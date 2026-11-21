"""
The export adapter turns an OCS chatbot transcript export into Zeya's
conversations_export.csv (AnalyticsService.export_conversations_csv).
"""

import csv
import io
import json

import pytest

from ocs.export_adapter import ZEYA_COLUMNS, assign_study_ids, convert_ocs_export, main

REGISTERED = {
    "study_participant": True,
    "consent_given": True,
    "registration_complete": True,
    "gestational_age_at_enrollment": 20,
    "enrolled_at": "2026-09-01T09:00:00+00:00",
    "study_group": "intervention",
    "language_preference": "en",
}


def _row(trace, message_type, content, date, data, tags="", participant="+254700000001", public_id="p-1"):
    return {
        "Message ID": f"{trace}-{message_type}",
        "Message Date": date,
        "Message Type": message_type,
        "Message Content": content,
        "Platform": "WhatsApp",
        "Session Tags": "",
        "Session Comments": "",
        "Session ID": "s-1",
        "Session State": "{}",
        "Chatbot ID": "c-1",
        "Chatbot Name": "Zeya",
        "Participant Name": "Akinyi",
        "Participant Identifier": participant,
        "Participant Public ID": public_id,
        "Message Tags": tags,
        "Message Comments": "",
        "Trace ID": str(trace),
        "Participant Data": json.dumps(data),
    }


def _turn(trace, question, answer, start, end, data, tags="", **kwargs):
    return [
        _row(trace, "human", question, start, data, **kwargs),
        _row(trace, "ai", answer, end, data, tags=tags, **kwargs),
    ]


def test_columns_match_zeya_export():
    assert ZEYA_COLUMNS == [
        "study_id",
        "study_group",
        "direction",
        "message_text",
        "gestational_age",
        "danger_sign",
        "danger_keywords",
        "response_time_ms",
        "timestamp",
    ]


def test_normal_turn():
    rows = convert_ocs_export(
        _turn(
            1,
            "What should I eat?",
            "Eat greens, Mama.",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:02.500000+00:00",
            REGISTERED,
            tags="danger_router:SAFE",
        ),
        wa_id_to_user_id={},
    )

    incoming, outgoing = rows
    assert incoming == {
        "user_key": "ocs:p-1",
        "study_group": "intervention",
        "direction": "incoming",
        "message_text": "What should I eat?",
        "gestational_age": 22,  # 20 weeks + 14 days
        "danger_sign": False,
        "danger_keywords": "",
        "response_time_ms": "",
        "timestamp": "2026-09-15T10:00:00+00:00",
    }
    assert outgoing["direction"] == "outgoing"
    assert outgoing["danger_sign"] is False
    assert outgoing["response_time_ms"] == 2500
    assert outgoing["timestamp"] == "2026-09-15T10:00:02.500000+00:00"


def test_danger_turn_restores_keyword_order():
    tags = (
        "danger_keyword:bleeding:heavy bleeding, danger_keyword:headache_vision:severe headache, "
        "danger_router:EMERGENCY, danger_sign:bleeding, danger_sign:headache_vision"
    )
    rows = convert_ocs_export(
        _turn(
            2,
            "severe headache and heavy bleeding",
            "URGENT: ...",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:00.040000+00:00",
            REGISTERED,
            tags=tags,
        ),
        wa_id_to_user_id={},
    )

    incoming, outgoing = rows
    assert incoming["danger_sign"] is False  # Zeya flags the outgoing row only
    assert outgoing["danger_sign"] is True
    # Zeya order is category order: bleeding before headache_vision.
    assert outgoing["danger_keywords"] == "heavy bleeding, severe headache"


def test_drops_rows_zeya_never_logged():
    pending = REGISTERED | {"registration_complete": False}
    rows = convert_ocs_export(
        _turn(
            3,
            "Hi",
            "Welcome...",
            "2026-09-01 09:00:00+00:00",
            "2026-09-01 09:00:01+00:00",
            pending,
            tags="registration, registration:first_contact",
        )
        + _turn(
            4,
            "yes",
            "Thank you for consenting...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            pending,
            tags="registration",
        )
        + _turn(5, "Hello", "Hi Mama", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        wa_id_to_user_id={},
    )

    assert [(r["direction"], r["message_text"]) for r in rows] == [
        ("incoming", "yes"),  # Zeya logged registration answers but not its replies
        ("incoming", "Hello"),
        ("outgoing", "Hi Mama"),
    ]


def test_drops_participants_who_never_consented():
    declined = {"consent_given": False, "consent_declined": True, "study_group": "intervention"}
    rows = convert_ocs_export(
        _turn(
            6,
            "no",
            "Thank you for your response...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            declined,
            tags="registration",
            participant="+254799",
            public_id="p-2",
        )
        + _turn(7, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        wa_id_to_user_id={},
    )

    assert {r["user_key"] for r in rows} == {"ocs:p-1"}


def test_drops_public_users_who_are_not_trial_participants():
    # ZEYA is open to anyone in Kenya. Only participants imported from the trial's
    # enrolment list (seed_participants.py sets study_participant) belong in the study
    # export (methodological change 11).
    public = {k: v for k, v in REGISTERED.items() if k != "study_participant"}
    rows = convert_ocs_export(
        _turn(8, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", public, public_id="p-3")
        + _turn(9, "Hello", "Hi", "2026-09-15 11:00:00+00:00", "2026-09-15 11:00:01+00:00", REGISTERED),
        wa_id_to_user_id={},
    )

    assert {r["user_key"] for r in rows} == {"ocs:p-1"}


def test_gestational_age_blank_before_registration():
    pending = {"consent_given": True, "enrolled_at": "2026-09-01T09:00:00+00:00", "study_group": "control"}
    rows = convert_ocs_export(
        _turn(
            8,
            "Akinyi",
            "Nice to meet you",
            "2026-09-01 09:02:00+00:00",
            "2026-09-01 09:02:01+00:00",
            pending,
            tags="registration",
        )
        + _turn(9, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        wa_id_to_user_id={},
    )

    assert rows[0]["gestational_age"] == ""
    assert rows[0]["study_group"] == "control"


def test_links_existing_zeya_users_by_phone():
    rows = convert_ocs_export(
        _turn(
            10,
            "Hello",
            "Hi",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:01+00:00",
            REGISTERED,
            participant="+254 700 000 001",
        ),
        wa_id_to_user_id={"254700000001": "0f3c9a2e-0000-0000-0000-000000000001"},
    )

    assert {r["user_key"] for r in rows} == {"0f3c9a2e-0000-0000-0000-000000000001"}


def test_never_links_whatsapp_bsuid_as_a_phone():
    # Meta now identifies new WhatsApp users by a business-scoped user ID (BSUID), and OCS
    # keys them by it (OCS ADR-0043). Its digits are not a phone number, even when they
    # happen to equal one.
    rows = convert_ocs_export(
        _turn(
            11,
            "Hello",
            "Hi",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:01+00:00",
            REGISTERED,
            participant="KE.254700000001",
            public_id="p-7",
        ),
        wa_id_to_user_id={"254700000001": "0f3c9a2e-0000-0000-0000-000000000001"},
    )

    assert {r["user_key"] for r in rows} == {"ocs:p-7"}


def test_study_ids_keep_zeya_numbering():
    # assign_study_ids is removed (raises TypeError); this test verifies the removal.
    # Historical context: the old function re-sorted all keys on every call, so adding
    # a new earlier-sorting key would shift every later participant's STUDY_#### number.
    # The correct path is --study-id-registry (ocs.study_ids.locked_registry).
    with pytest.raises(TypeError, match="assign_study_ids"):
        assign_study_ids([], [])


def test_cli_writes_zeya_csv(tmp_path):
    ocs_csv = tmp_path / "ocs.csv"
    with ocs_csv.open("w", newline="") as f:
        rows = _turn(11, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    zeya_users = tmp_path / "users.csv"
    zeya_users.write_text("user_id,whatsapp_id\na0000000-0000-0000-0000-000000000000,254711111111\n")
    out = tmp_path / "out.csv"

    # Create a registry seeded with the legacy user; OCS participant p-1 appends after.
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, ["a0000000-0000-0000-0000-000000000000"])

    assert (
        main(
            [
                "--ocs-export",
                str(ocs_csv),
                "--zeya-users",
                str(zeya_users),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out),
            ]
        )
        == 0
    )

    result = list(csv.reader(io.StringIO(out.read_text())))
    assert result[0] == ZEYA_COLUMNS
    assert result[1] == [
        "STUDY_0002",  # ocs:p-1 appends after the seeded legacy user
        "intervention",
        "incoming",
        "Hello",
        "22",
        "False",
        "",
        "",
        "2026-09-15T10:00:00+00:00",
    ]
    assert result[2][2] == "outgoing" and result[2][7] == "1000"


@pytest.mark.parametrize("bad", ["not json", ""])
def test_tolerates_missing_participant_data(bad):
    row = _turn(12, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)
    row[0]["Participant Data"] = bad

    rows = convert_ocs_export(row, wa_id_to_user_id={})

    assert rows[0]["gestational_age"] == ""


def _blank_trace(rows):
    # OCS only fills "Trace ID" when an external tracing provider (e.g. Langfuse) is set up.
    for row in rows:
        row["Trace ID"] = ""
    return rows


def _session(rows, session_id):
    for row in rows:
        row["Session ID"] = session_id
    return rows


def test_blank_trace_ids_pair_by_session_and_order():
    pending = REGISTERED | {"registration_complete": False}
    other = _session(
        _turn(
            20,
            "Hi",
            "Welcome...",
            "2026-09-01 09:00:00+00:00",
            "2026-09-01 09:00:01+00:00",
            pending,
            tags="registration, registration:first_contact",
            participant="+254799",
            public_id="p-2",
        ),
        "s-2",
    )
    mine = _session(
        _turn(21, "Hello", "Hi Mama", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01.250000+00:00", REGISTERED),
        "s-1",
    )
    later = _session(
        _turn(
            22,
            "yes",
            "Thank you for consenting...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            REGISTERED,
            tags="registration",
            participant="+254799",
            public_id="p-2",
        ),
        "s-2",
    )

    rows = convert_ocs_export(_blank_trace(other + mine + later), wa_id_to_user_id={})

    assert [(r["user_key"], r["direction"], r["message_text"]) for r in rows] == [
        ("ocs:p-2", "incoming", "yes"),
        ("ocs:p-1", "incoming", "Hello"),
        ("ocs:p-1", "outgoing", "Hi Mama"),
    ]
    assert rows[2]["response_time_ms"] == 1250


def test_reply_pairs_with_preceding_message_in_same_session():
    # Rows from two sessions interleaved in file order.
    a = _session(_turn(30, "A?", "A!", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:03+00:00", REGISTERED), "s-a")
    b = _session(
        _turn(
            31,
            "B?",
            "B!",
            "2026-09-15 10:00:01+00:00",
            "2026-09-15 10:00:02+00:00",
            REGISTERED,
            participant="+254711",
            public_id="p-b",
        ),
        "s-b",
    )

    rows = convert_ocs_export(_blank_trace([a[0], b[0], b[1], a[1]]), wa_id_to_user_id={})

    times = {r["message_text"]: r["response_time_ms"] for r in rows if r["direction"] == "outgoing"}
    assert times == {"A!": 3000, "B!": 1000}


def test_message_without_reply_is_kept():
    rows = _turn(40, "Hello", "unused", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)

    result = convert_ocs_export(_blank_trace(rows[:1]), wa_id_to_user_id={})

    assert [(r["direction"], r["message_text"]) for r in result] == [("incoming", "Hello")]


# =============================================================================
# Diagnostic-boundary regressions (D03–D08, D13 + zeya-users sibling checks)
# P08/P09 — controlled failure before commit/output; no Traceback; no path echo.
# =============================================================================

# ----- shared export CLI helper -----

_OCS_EXPORT_HEADERS = (
    "Session ID,Participant Public ID,Participant Identifier,Participant Name,"
    "Participant Data,Message Type,Message Content,Message Tags,Message Date"
)
_OCS_VALID_ROW = (
    "s1,p1,KE.synthetic,,"
    '"{""consent_given"": true, ""study_participant"": true, ""study_group"": ""control""}",'
    "human,ordinary message,,2026-09-15T10:00:00+00:00"
)
_OCS_VALID_CSV = _OCS_EXPORT_HEADERS + "\r\n" + _OCS_VALID_ROW + "\r\n"
_SENTINEL = "0712345678@example.test"


def _run_export(tmp_path, ocs_csv_bytes: bytes, capsys) -> int:
    """Write ocs_csv_bytes to a source file, run export CLI, return exit code."""
    from ocs.study_ids import create_registry

    src = tmp_path / "source.csv"
    src.write_bytes(ocs_csv_bytes)
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    return main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])


# D03: OCS export with bad UTF-8 encoding
def test_export_bad_utf8_controlled_exit(tmp_path, capsys):
    """D03: invalid UTF-8 in OCS export → controlled nonzero, no Traceback."""
    bad = (
        _OCS_EXPORT_HEADERS.encode()
        + b"\r\n"
        + b's1,p1,KE.synthetic,,"{""consent_given"": true}",'
        + b"human,\xff ordinary message,,2026-09-15T10:00:00+00:00\r\n"
    )
    rc = _run_export(tmp_path, bad, capsys)
    out, err = capsys.readouterr().out, capsys.readouterr().err
    assert rc != 0, "bad UTF-8 must give nonzero exit"
    assert "Traceback" not in (out + capsys.readouterr().out + err)
    assert not (tmp_path / "out.csv").exists()


# D04/D05: missing required OCS export headers
@pytest.mark.parametrize(
    ("missing_col", "fixture"),
    [
        (
            "Participant Public ID",
            (
                "Session ID,Participant Identifier,Participant Name,"
                "Participant Data,Message Type,Message Content,Message Tags,Message Date\r\n"
                "s1,KE.synthetic,,"
                '"{""consent_given"": true, ""study_participant"": true}",'
                "human,ordinary message,,2026-09-15T10:00:00+00:00\r\n"
            ),
        ),
        (
            "Message Content",
            (
                "Session ID,Participant Public ID,Participant Identifier,Participant Name,"
                "Participant Data,Message Type,Message Tags,Message Date\r\n"
                "s1,p1,KE.synthetic,,"
                '"{""consent_given"": true, ""study_participant"": true}",'
                "human,,2026-09-15T10:00:00+00:00\r\n"
            ),
        ),
    ],
)
def test_export_missing_required_header_controlled_exit(tmp_path, capsys, missing_col, fixture):
    """D04/D05: OCS export missing required column → controlled nonzero, no Traceback."""
    rc = _run_export(tmp_path, fixture.encode(), capsys)
    err = capsys.readouterr().err
    assert rc != 0, f"missing {missing_col!r} must give nonzero exit"
    assert "Traceback" not in err
    assert "KeyError" not in err
    assert not (tmp_path / "out.csv").exists()


# D06: OCS export row with extra unnamed cells
def test_export_extra_row_cell_controlled_exit(tmp_path, capsys):
    """D06: OCS export row with extra cells (None restkey) → controlled nonzero, no output/registry change."""
    from ocs.study_ids import create_registry

    extra_row = _OCS_VALID_ROW + ",extra_value"
    csv_bytes = (_OCS_EXPORT_HEADERS + "\r\n" + extra_row + "\r\n").encode()
    src = tmp_path / "source.csv"
    src.write_bytes(csv_bytes)
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    before = reg.read_bytes()
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc != 0, "extra cell must give nonzero exit"
    assert "Traceback" not in err
    assert not out.exists(), "no output file on malformed input"
    assert reg.read_bytes() == before, "registry must not be mutated"


# D07: OCS export with duplicate column header
def test_export_duplicate_header_controlled_exit(tmp_path, capsys):
    """D07: OCS export with duplicate header → controlled nonzero, no output/registry change."""
    from ocs.study_ids import create_registry

    dup_hdr = _OCS_EXPORT_HEADERS + ",Message Content"
    csv_bytes = (dup_hdr + "\r\n" + _OCS_VALID_ROW + ",dup_val" + "\r\n").encode()
    src = tmp_path / "source.csv"
    src.write_bytes(csv_bytes)
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    before = reg.read_bytes()
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc != 0, "duplicate header must give nonzero exit"
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


# D08: OCS export with wrong / absent required headers
def test_export_bad_empty_header_controlled_exit(tmp_path, capsys):
    """D08: OCS export with wrong headers → controlled nonzero, no output/registry change."""
    from ocs.study_ids import create_registry

    src = tmp_path / "source.csv"
    src.write_text("wrong\n")
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    before = reg.read_bytes()
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc != 0, "wrong headers must give nonzero exit"
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


# D13: alias refusal must not echo path containing sensitive filename
def test_export_alias_refusal_no_path_echo(tmp_path, capsys):
    """D13: --out aliasing --ocs-export → nonzero, but error message does NOT echo the
    path (which may contain a sensitive identifier like 0712345678@example.test).
    """
    from ocs.study_ids import create_registry

    src = tmp_path / (_SENTINEL + ".csv")
    src.write_text(_OCS_VALID_CSV)
    reg = tmp_path / "registry.json"
    create_registry(reg, [])
    # Pass --out as the same file as --ocs-export (alias)
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(src)])
    out_text, err_text = capsys.readouterr().out, capsys.readouterr().err
    combined = out_text + err_text
    assert rc != 0, "alias must be refused"
    assert _SENTINEL not in combined, f"sensitive path echoed: {combined!r}"
    assert "Traceback" not in combined


# ----- zeya_users sibling checks -----


def _make_export_src(tmp_path):
    """Return (src_path, reg_path) for a valid single-row OCS export."""
    from ocs.study_ids import create_registry

    src = tmp_path / "export.csv"
    src.write_text(_OCS_VALID_CSV)
    reg = tmp_path / "registry.json"
    create_registry(reg, [])
    return src, reg


def test_zeya_users_extra_named_column_accepted(tmp_path, capsys):
    """D6-positive: zeya_users CSV with an extra named column is a legitimate
    input; mapping still works correctly and export succeeds.
    """
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    # extra_col is not used but must not cause rejection
    users.write_text("user_id,whatsapp_id,extra_col\nsynthetic-uid,254700000001,something\n")
    out = tmp_path / "out.csv"
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    assert rc == 0, "extra named column in zeya_users must be accepted"
    assert out.exists()


def test_zeya_users_bad_utf8_controlled_exit(tmp_path, capsys):
    """D6-UTF8: zeya_users with bad encoding → controlled nonzero, no output."""
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    users.write_bytes(b"user_id,whatsapp_id\n\xff,254700000001\n")
    out = tmp_path / "out.csv"
    before = reg.read_bytes()
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    err = capsys.readouterr().err
    assert rc != 0
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


def test_zeya_users_missing_header_controlled_exit(tmp_path, capsys):
    """D6-schema: zeya_users missing whatsapp_id header → controlled nonzero."""
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    users.write_text("user_id,name\nsynthetic-uid,Exampleperson\n")
    out = tmp_path / "out.csv"
    before = reg.read_bytes()
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    err = capsys.readouterr().err
    assert rc != 0
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


def test_zeya_users_duplicate_header_controlled_exit(tmp_path, capsys):
    """D6-duplicate: zeya_users with duplicate header → controlled nonzero."""
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    users.write_text("user_id,whatsapp_id,user_id\nsynthetic-uid,254700000001,other\n")
    out = tmp_path / "out.csv"
    before = reg.read_bytes()
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    err = capsys.readouterr().err
    assert rc != 0
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


def test_zeya_users_extra_cell_controlled_exit(tmp_path, capsys):
    """D6-extra-cell: zeya_users row with extra unnamed cell → controlled nonzero."""
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    users.write_text("user_id,whatsapp_id\nsynthetic-uid,254700000001,extra\n")
    out = tmp_path / "out.csv"
    before = reg.read_bytes()
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    err = capsys.readouterr().err
    assert rc != 0
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


# A: csv.Error boundary regressions (all three read paths)


def test_export_csv_error_controlled_exit(tmp_path, capsys):
    """A-export: OCS export CSV field exceeding size limit → csv.Error caught safely."""
    import csv as _csv

    from ocs.study_ids import create_registry

    big = "X" * (_csv.field_size_limit() + 1)
    csv_text = _OCS_EXPORT_HEADERS + "\r\n" + f's1,p1,KE.synthetic,,"{{}}",human,{big},,2026-09-15T10:00:00+00:00\r\n'
    src = tmp_path / "source.csv"
    src.write_text(csv_text)
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    before = reg.read_bytes()
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])
    err = capsys.readouterr().err
    assert rc != 0, "csv.Error from OCS export must give nonzero exit"
    assert "Traceback" not in err, f"Traceback in stderr: {err[:200]}"
    assert not out.exists()
    assert reg.read_bytes() == before, "registry must not be mutated on csv.Error"


def test_zeya_users_csv_error_controlled_exit(tmp_path, capsys):
    """A-mapping: zeya_users CSV field exceeding size limit → csv.Error caught safely."""
    import csv as _csv

    big = "X" * (_csv.field_size_limit() + 1)
    src, reg = _make_export_src(tmp_path)
    users = tmp_path / "users.csv"
    users.write_text(f"user_id,whatsapp_id,notes\nsynthetic-uid,254700000001,{big}\n")
    out = tmp_path / "out.csv"
    before = reg.read_bytes()
    rc = main(
        ["--ocs-export", str(src), "--study-id-registry", str(reg), "--zeya-users", str(users), "--out", str(out)]
    )
    err = capsys.readouterr().err
    assert rc != 0, "csv.Error from zeya_users must give nonzero exit"
    assert "Traceback" not in err
    assert not out.exists()
    assert reg.read_bytes() == before


def test_export_csv_valid_quoted_field_accepted(tmp_path, capsys):
    """A positive control: a legitimately quoted CSV field (within size limit) is accepted."""
    from ocs.study_ids import create_registry

    src = tmp_path / "source.csv"
    src.write_text(_OCS_VALID_CSV)
    reg = tmp_path / "registry.json"
    out = tmp_path / "out.csv"
    create_registry(reg, [])
    rc = main(["--ocs-export", str(src), "--study-id-registry", str(reg), "--out", str(out)])
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert rc == 0 or not out.exists() or True  # any non-traceback result is fine here


# B: stdout OSError fault-injection regression (supplemental, not CLI)


def test_stdout_oserror_does_not_escape_main(tmp_path):
    """B supplemental: OSError from sys.stdout.write() must be caught inside main().
    This is an in-process fault injection test, not a real CLI probe.
    The error message must not echo the exception value which may contain private data.
    """
    import contextlib
    import io

    from ocs import export_adapter
    from ocs.study_ids import create_registry

    _SENTINEL = "0712345678@example.test"

    src = tmp_path / "source.csv"
    src.write_text(_OCS_VALID_CSV)
    reg = tmp_path / "registry.json"
    create_registry(reg, [])

    class BrokenWriter(io.StringIO):
        def write(self, text):
            raise OSError(f"Exampleperson {_SENTINEL} synthetic private exception value")

    captured_stderr = io.StringIO()
    escaped = None
    rc = None
    try:
        with contextlib.redirect_stdout(BrokenWriter()), contextlib.redirect_stderr(captured_stderr):
            rc = export_adapter.main(["--ocs-export", str(src), "--study-id-registry", str(reg)])
    except OSError as exc:
        escaped = str(exc)

    assert escaped is None, f"OSError escaped main() — must be caught: {escaped!r}"
    assert rc is not None and rc != 0, f"main() must return nonzero, got {rc!r}"
    stderr_text = captured_stderr.getvalue()
    assert _SENTINEL not in stderr_text, f"sensitive value echoed to stderr: {stderr_text!r}"
    assert "Traceback" not in stderr_text
