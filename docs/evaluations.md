# Zeya OCS completed-observation evaluations

## Scope and observed verification

The evaluator package checks completed, trusted-runner observations; it does not generate a new answer in order to prove an earlier turn used no model. Clinical and fluent-language approval remain separate human-led work.

The final local candidate passed 1263 unit/sandbox tests and 121 real-engine integration tests against OCS commit `9f5c25476555ff74a167c6a14832ce798832847a`. The latter include 12 completed-evaluation tests using persisted OCSTracer records, actual OCS CSV creation/import and evaluation tasks, plus grounded-graph, privacy and onboarding tests. These are observed results for the candidate, not expected future suite totals, clinical accuracy, held-out recall or hosted/WhatsApp acceptance. Synthetic model responses use FakeLlm, not a provider API.

## Completed-observation flow

1. The trusted runner freezes and fingerprints the exact pipeline artifact used for a turn, captures the verified metric-source profile, and executes the pipeline.
2. Persisted Trace, ExperimentSession, Experiment and exact input/output ChatMessage records are read back separately. Capture output tags from the completed execution; do not invent metric values or fill absent evidence with defaults.
3. `CompletedObservationRow.from_trace_dict()` validates these snapshots and their foreign-key, chat and team relationships. It also requires an independently configured expected bot/pipeline identity.
4. `write_completed_observations_csv()` exports validated rows with their original input/output text, observation envelope and expected source.
5. Import the CSV into an OCS evaluation dataset with `COMPLETED_OBS_COLUMN_MAPPING`.
6. Run the generated Python evaluators in completed-observation mode: `generation_experiment=None`, with “Run generation step before evaluation” disabled. The actual OCS task supplies `generated_response=""`; the evaluators reject non-empty fresh generation.
7. Shared generated validation checks transport labels, source/profile/identity/text binding and evidence before route, no-model and card-selection scoring.

Never rebuild today's pipeline to infer an earlier execution's fingerprint. Version numbers alone are not source identity. Expected labels are authored test expectations, not provenance.

## Trusted adapter inputs

Use the exact snapshot contract documented on `CompletedObservationRow.from_trace_dict()` in `ocs/evaluations/completed_adapter.py`:

| Snapshot | Required fields |
|---|---|
| `trace` | `trace_id`, `input_message_id`, `output_message_id`, `session_id`, `experiment_id`, `team_id`, `status`, `error`, `n_turns`, `metric_profile`, `captured_output_tags`, `pipeline_sha256`, `experiment_version_number` |
| `session` | `id`, `external_id`, `experiment_id`, `chat_id`, `team_id` |
| `experiment` | `id`, `public_id`, `team_id` |
| each message | `id`, `chat_id`, `message_type`, `content` |
| `expected_source_config` | independently configured `chatbot_public_id`, `pipeline_sha256` |

The adapter requires plain positive integer record IDs (not bools or coerced strings), exact Trace message FKs, matching session/experiment/team records, distinct input/output IDs and the correct human/AI roles. Matching text in a different record is insufficient. The current envelope requires lowercase hyphenated UUID-format trace/session identifiers; this is the adapter's supported contract, not a claim that every OCS external session ID is universally UUID-constrained.

`trace.status` must be `"success"` and `trace.error` must be an actual empty string. Do not replace a recorded error with `error or ""`. All evidence keys must be present. The captured pipeline SHA256 is mandatory; `experiment_version_number` is explicitly present and may be `None` or a non-negative integer, never a boolean. Neither its absence nor a version by itself establishes source identity.

The following API example assumes the trusted runner has already collected and checked the named snapshots and independently selected `expected_source_config`. It is not a collector or a fabricated execution example:

```python
from ocs.evaluations.completed_adapter import (
    COMPLETED_OBS_COLUMN_MAPPING,
    CompletedObservationRow,
    RelationshipError,
    write_completed_observations_csv,
)

try:
    row = CompletedObservationRow.from_trace_dict(
        trace=trace_snapshot,
        session=session_snapshot,
        experiment=experiment_snapshot,
        input_message=input_snapshot,
        output_message=output_snapshot,
        expected_source_config=expected_source_config,
        expected_route="EMERGENCY",
        expected_category="bleeding",
        expected_card_id="",
    )
except RelationshipError:
    raise  # Reject the row; do not print record contents or exception payloads.

# `destination` is a trusted, access-controlled writable text stream.
write_completed_observations_csv([row], destination)
# Supply COMPLETED_OBS_COLUMN_MAPPING to OCS dataset import.
```

See `ocs/integration/test_completed_evaluations_engine.py` for executed, isolated examples of actual tracer snapshots, CSV import and evaluation tasks. Raw messages and adapter exceptions can contain sensitive content: do not put them in operational logs or public reports.

## Metric profile and no-model evidence

The verified profile in `ocs/evaluations/observation.py` binds:

- OCS commit: `9f5c25476555ff74a167c6a14832ce798832847a`
- MetricsCollector SHA256: `c296ebb6b41517d85f9614ce6ee06eb4cb0906517a33c8052302f9c9fa7db9e7`
- OCSTracer SHA256: `e9b64b52681957a1bd79ff5480840af3e20f7afa6f387908a6c72e14c2e0076e`

The runner must verify the actual source before capturing this profile; copying these constants into an arbitrary record does not authenticate it. Under this verified profile, `MetricsCollector.get_metrics()` returns `turns or None`:

| Recorded `n_turns` | Interpretation |
|---|---|
| Explicit `None` | No LLM start recorded; accepted as no-model evidence only after all other validation |
| Positive integer | LLM was started; fails the no-model requirement for EMERGENCY |
| Literal `0` | Inconsistent with this profile; rejected |
| Missing, boolean, negative or wrong type | Invalid/unknown evidence; rejected |

An unfamiliar engine/profile must be verified separately; do not silently treat its null or zero counter as equivalent.

## CSV transport and mapping

Use the exported `COMPLETED_OBS_COLUMN_MAPPING`, rather than reproducing an older mapping. It includes input/output and these context keys:

- `expected_route`
- `expected_category`
- `expected_card_id`
- `observation`
- `expected_source`

The exporter JSON-encodes the three scalar label strings, including the empty no-card label. This keeps their CSV cells non-empty through OCS's update importer, whose falsey-value guard would drop a raw empty cell. The pinned parser JSON-decodes objects/arrays only: quoted scalar labels remain quoted strings after import. Shared generated evaluator validation explicitly decodes these labels once; caller preprocessing is not required. Legacy unquoted strings remain supported, missing stays missing, and malformed quoted labels fail validation. Primitive-looking card IDs such as `false`, `null` and `123` remain logical strings. Object-valued observation/source columns are parsed as JSON objects, preserving the explicit `n_turns: null` key.

Both adapter export and the generated evaluator boundary validate evidence. The latter also enforces exact input/output text binding, expected-source binding and the verified metric profile. Refer to `_SHARED_VALIDATION_BODY` in `ocs/evaluations/observation.py` for the authoritative error keys.

## State and scoring boundaries

- `set_temp_state_key()` is ephemeral node state, not automatically available from `message.session_state` in an evaluator.
- `set_session_state_key()` is a different, persistent mechanism. Do not pretend it contains node temp state.
- Persistent output tags and Trace metrics are captured by the trusted runner into the observation envelope.
- CARD selection is not necessarily delivery: a selected card can subsequently be blocked by `output_guard`. Inspect selection and guard tags separately.
- Route/card checks over authored fixtures are regression evidence, not clinician approval or a held-out accuracy claim.
- `ocs/evaluations/llm_judge_template.py` is a template for separate quality evaluation. No Groq/provider judge run is claimed by this change; any such run needs a separate approved dataset and provider/privacy setup.

The adapter and evaluator establish internal consistency for trusted-runner observations, not cryptographic authentication of arbitrary JSON uploads. A forged entire snapshot can still lie. Retain independent source configuration, protect runner access and handle exported original text as sensitive data.

## Reproducing local checks

From the repository root, after installing `ocs/requirements-dev.txt` in an isolated environment:

```bash
make lint-ocs PYTHON=/path/to/venv/bin/python
OCS_SOURCE=/path/to/pinned/open-chat-studio \
    make test-ocs PYTHON=/path/to/venv/bin/python
```

The real-engine gate additionally needs the pinned OCS checkout's prepared virtualenv, supported test settings and an isolated disposable test database:

```bash
make test-ocs-engine OCS_SOURCE=/path/to/pinned/open-chat-studio
```

Never run these database tests against production. The final replay used isolated synthetic storage and a loopback-only disposable database; its owned container and volume were removed and absence was checked. These commands alone do not provision or approve a hosted release.

## Remaining release work

The five English starter KB/card topics and five Kiswahili (sw) counterparts have approved runtime eligibility; the original approximately 60-card ambition is not completed. Expanded authored/held-out evaluation, content/contact verification, any provider-backed judge, hosted deployment/source-drift verification, Meta templates and handset delivery tests are separate checks. Merging source does not publish WhatsApp or establish clinical safety.
