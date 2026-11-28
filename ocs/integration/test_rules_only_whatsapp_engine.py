"""
Rules-only mode (#26) through OCS's real WhatsApp handler, not only the pipeline.

Run with ``make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio``.

test_rules_only_engine.py starts inside the Zeya graph. Here Meta Cloud API webhook
payloads go through handle_meta_cloud_api_message, so the channel stages around the
pipeline run too. The operator switch is made the way docs/ocs-migration.md describes:
both builds are published versions, and only which one is the published (default)
version changes. Delivery to Meta is intercepted, and every model call, including OCS's
own EventBot, is recorded by a fake LLM.

The last test pins a known limitation, not a goal: OCS answers a voice note it cannot
transcribe with EventBot, a model call outside the pipeline whose prompt carries her
recent messages and saved participant data. Rules-only mode cannot prevent it. If OCS
changes this, the test fails, and "Rules-only mode" in docs/ocs-migration.md must be
updated.
"""

import datetime
import itertools
from io import BytesIO
from unittest import mock

import pytest
from apps.channels.models import ChannelPlatform
from apps.channels.tasks import handle_meta_cloud_api_message
from apps.channels.tests.message_examples import meta_cloud_api_messages
from apps.chat.models import ChatMessage
from apps.experiments.models import Experiment, ExperimentSession, Participant, ParticipantData
from apps.pipelines.flow import FullFlow, split_flow_data
from apps.service_providers.models import MessagingProviderType
from apps.utils.factories.channels import ExperimentChannelFactory
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import (
    LlmProviderFactory,
    LlmProviderModelFactory,
    MessagingProviderFactory,
)
from apps.utils.tests.langchain import build_fake_llm_service
from django.conf import settings
from django.core.cache import cache as default_cache
from django.core.cache import caches
from field_audit.models import AuditAction

from ocs.build_pipeline import build_pipeline
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

LLM_REPLY = "Kula mlo kamili, Mama."
SW_RULES_ONLY = (
    "Samahani, ZEYA imeshindwa kujibu swali lako kwa sasa. Tafadhali jaribu tena baadaye. "
    "Kwa maswali kuhusu ujauzito, wasiliana na mtoa huduma wako wa afya."
)
UNCOVERED_SW = "Hali ya hewa leo ni nini?"
BLEEDING_SW = BILINGUAL_EXAMPLES["bleeding"]["sw"]
ONBOARDING_SW = ["Habari", "2", "NDIYO", "Akinyi", "20"]

_message_ids = itertools.count(1)


@pytest.fixture(autouse=True)
def _empty_rate_limit_window():
    # As in apps/channels/tests/conftest.py: the counters outlive a single test.
    caches[settings.RATE_LIMIT_CACHE_ALIAS].clear()
    default_cache.clear()
    yield
    caches[settings.RATE_LIMIT_CACHE_ALIAS].clear()
    default_cache.clear()


@pytest.fixture()
def fake_llm():
    service = build_fake_llm_service(responses=[LLM_REPLY] * 10)
    service.llm.calls = []
    with mock.patch("apps.service_providers.models.LlmProvider.get_llm_service", return_value=service):
        yield service.llm


@pytest.fixture()
def sent():
    """Every reply OCS hands to Meta, text or voice, in order."""
    replies = []
    with (
        mock.patch(
            "apps.service_providers.messaging_service.MetaCloudAPIService.send_text_message",
            side_effect=lambda message, *args, **kwargs: replies.append(message),
        ),
        mock.patch(
            "apps.service_providers.messaging_service.MetaCloudAPIService.send_voice_message",
            side_effect=lambda *args, **kwargs: replies.append("<voice>"),
        ),
        mock.patch(
            "apps.service_providers.messaging_service.MetaCloudAPIService.get_message_audio",
            return_value=BytesIO(b"OggS"),
        ),
    ):
        yield replies


def _import(team, provider, provider_model, rules_only):
    pipeline = PipelineFactory.create(team=team)
    flow = FullFlow(**build_pipeline(provider.id, provider_model.id, rules_only=rules_only)["data"])
    layout, node_data = split_flow_data(flow)
    pipeline.data = layout.model_dump()
    pipeline.save()
    pipeline.update_nodes_from_data(node_data)
    return pipeline


@pytest.fixture()
def bot(db):
    """A WhatsApp chatbot with a published normal version and an unpublished rules-only one."""
    messaging = MessagingProviderFactory.create(
        name="meta_cloud_api",
        type=MessagingProviderType.meta_cloud_api,
        config={"access_token": "t", "business_id": "b", "app_secret": "s", "verify_token": "v"},
    )
    channel = ExperimentChannelFactory.create(
        platform=ChannelPlatform.WHATSAPP,
        messaging_provider=messaging,
        experiment__team=messaging.team,
        extra_data={"number": "+15551234567", "phone_number_id": "12345"},
    )
    chatbot = channel.experiment
    team = chatbot.team
    # EventBot uses the team's first LLM provider, not the pipeline's (apps/chat/bots.py).
    provider = LlmProviderFactory.create(team=team)
    provider_model = LlmProviderModelFactory.create(team=team)

    normal_pipeline = _import(team, provider, provider_model, rules_only=False)
    chatbot.pipeline = normal_pipeline
    chatbot.save()
    normal = chatbot.create_new_version(version_description="normal", make_default=True)

    chatbot.pipeline = _import(team, provider, provider_model, rules_only=True)
    chatbot.save()
    rules_only = chatbot.create_new_version(version_description="RULES-ONLY", make_default=False)

    # docs/ocs-migration.md, "Prepare it": the working version ends on the normal build.
    chatbot.pipeline = normal_pipeline
    chatbot.save()
    return {"channel": channel, "chatbot": chatbot, "normal": normal, "rules_only": rules_only}


def _publish(bot, which):
    """What set_default_experiment does (apps/experiments/views/experiment.py)."""
    version = bot[which]
    Experiment.objects.filter(working_version=bot["chatbot"]).exclude(id=version.id).update(
        is_default_version=False, audit_action=AuditAction.AUDIT
    )
    version.is_default_version = True
    version.save()


def _deliver(bot, value):
    value["messages"][0]["id"] = f"wamid.zeya{next(_message_ids)}"
    value["messages"][0]["timestamp"] = str(int(datetime.datetime.now(datetime.UTC).timestamp()))
    channel = bot["channel"]
    handle_meta_cloud_api_message(channel_id=channel.id, team_slug=channel.team.slug, message_data=value)


def _text(bot, sent, text):
    value = meta_cloud_api_messages.text_message_value()
    value["messages"][0]["text"] = {"body": text}
    before = len(sent)
    _deliver(bot, value)
    assert len(sent) == before + 1, f"expected exactly one reply to {text!r}, got {sent[before:]}"
    return sent[-1]


def _participant_data(bot):
    return ParticipantData.objects.get(experiment=bot["chatbot"]).data


def _onboard(bot, sent):
    for message in ONBOARDING_SW:
        _text(bot, sent, message)
    data = _participant_data(bot)
    assert data["registration_complete"] is True
    assert data["language_preference"] == "sw"


def test_switching_versions_in_an_existing_conversation(bot, sent, fake_llm):
    _publish(bot, "normal")
    _onboard(bot, sent)
    assert fake_llm.calls == []

    assert _text(bot, sent, UNCOVERED_SW) == LLM_REPLY, "control: the normal version calls the model"
    assert len(fake_llm.calls) == 1

    _publish(bot, "rules_only")
    assert _text(bot, sent, UNCOVERED_SW) == SW_RULES_ONLY
    assert _text(bot, sent, BLEEDING_SW).startswith("DHARURA:")
    assert len(fake_llm.calls) == 1, "rules-only text turns make no model call"

    _publish(bot, "normal")
    assert _text(bot, sent, UNCOVERED_SW) == LLM_REPLY
    assert len(fake_llm.calls) == 2

    data = _participant_data(bot)
    assert data["registration_complete"] is True
    assert data["language_preference"] == "sw"
    assert data["name"] == "Akinyi"


def test_known_limitation_voice_note_reaches_eventbot_in_rules_only_mode(bot, sent, fake_llm):
    """Not a goal: pins OCS behaviour that docs/ocs-migration.md warns about.

    The chatbot has no voice provider, so OCS cannot transcribe the note and answers
    it with EventBot (apps/channels/stages/core.py QueryExtractionStage, then
    apps/channels/pipeline.py _generate_error_message). EventBot's system prompt holds
    the recent conversation and her participant data (apps/chat/bots.py EventBot).
    """
    _publish(bot, "rules_only")
    _onboard(bot, sent)
    assert _text(bot, sent, BLEEDING_SW).startswith("DHARURA:")
    assert fake_llm.calls == []

    before = len(sent)
    _deliver(bot, meta_cloud_api_messages.audio_message_value())

    assert len(sent) == before + 1, "the voice note still gets a reply"
    assert len(fake_llm.calls) == 1, "that reply came from a model call outside the pipeline"
    prompt = "\n".join(str(m.content) for m in fake_llm.calls[0].args[0])
    assert "Akinyi" in prompt, "EventBot's prompt carries her saved name"
    assert BLEEDING_SW in prompt, "and her earlier health message"


def test_disabled_channel_still_stores_a_first_time_sender(bot, sent, fake_llm):
    """The channel switch is not a "record nothing" switch (docs/ocs-migration.md).

    ParticipantResolverStage runs before ChannelDisabledStage
    (apps/channels/channel_base.py), so a first-time sender gets a participant record
    with her WhatsApp identifier and phone number. No session, message or reply follows,
    and no danger gate runs.
    """
    _publish(bot, "normal")
    channel = bot["channel"]
    channel.enabled = False
    channel.save()

    value = meta_cloud_api_messages.text_message_value()
    value["messages"][0]["text"] = {"body": BLEEDING_SW}
    _deliver(bot, value)

    assert sent == [], "no reply, not even the emergency message"
    assert fake_llm.calls == []
    participant = Participant.objects.get(team=bot["chatbot"].team)
    assert participant.identifier == meta_cloud_api_messages.BSUID
    assert participant.remote_id == "27456897512"
    assert not ExperimentSession.objects.filter(participant=participant).exists()
    assert not ChatMessage.objects.filter(content=BLEEDING_SW).exists()
