"""
Convert an Open Chat Studio transcript export into Zeya's conversations_export.csv.

The output has the columns and value formats of
backend/app/services/analytics_service.py export_conversations_csv(), so the
planned analysis can read Zeya-era and OCS-era data the same way.

    python -m ocs.export_adapter \\
        --ocs-export ocs_sessions.csv \\
        --study-id-registry /secure/path/study_ids.json \\
        --zeya-users zeya_users.csv \\
        --out conversations_export_ocs.csv

``--zeya-users`` links OCS participants to existing Zeya users by WhatsApp id (the
OCS participant identifier) and keeps Zeya's STUDY_#### numbering. Participants
imported with seed_participants keep their phone number as identifier. New WhatsApp
users are keyed by Meta's business-scoped user ID (e.g. KE.1123493676705328, OCS
ADR-0043); they are never linked and get new study ids. Produce it from the Zeya database with:

    \\copy (SELECT DISTINCT u.id AS user_id, u.whatsapp_id FROM users u
            JOIN conversations c ON c.user_id = u.id) TO 'zeya_users.csv' CSV HEADER

Rules, matching what Zeya logged:
- Participants whose latest participant data does not have consent_given are left out.
- So are public users: ZEYA is open to anyone in Kenya, and only participants imported
  from the trial's enrolment list (seed_participants.py) have study_participant.
- Turns tagged "registration:first_contact" are left out (Zeya did not log the first
  message). On other "registration" turns only the user's message is kept (Zeya
  logged registration answers but not its replies).
- danger_sign and danger_keywords are set on the outgoing row only, from the gate's
  message tags, with keywords in Zeya's category order. Whitespace inside a keyword
  is collapsed to single spaces.
- gestational_age is the participant's gestational age when the message was sent.
- response_time_ms is the outgoing message time minus the incoming message time.
- Each reply is paired with the user message just before it in the same session. The
  export's Trace ID cannot be used: OCS leaves it blank unless an external tracing
  provider is configured.
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

ZEYA_COLUMNS = [
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

# DANGER_SIGN_PATTERNS order in backend/app/services/danger_signs.py.
CATEGORY_ORDER = [
    "bleeding",
    "headache_vision",
    "fever",
    "fetal_movement",
    "abdominal_pain",
    "water_breaking",
    "convulsions",
    "swelling",
]

DIRECTIONS = {"human": "incoming", "ai": "outgoing"}


def _digits(phone: str) -> str:
    return "".join(c for c in phone or "" if c.isdigit())


# Same pattern as looks_like_bsuid() in OCS apps/channels/datamodels.py.
_BSUID = re.compile(r"^[A-Z]{2}(?:\.ENT)?\.[A-Za-z0-9]{1,128}$")


def _phone(identifier: str) -> str | None:
    """The participant's phone digits, or None when OCS keys them by a WhatsApp BSUID."""
    return None if _BSUID.match(identifier or "") else _digits(identifier)


def _participant_data(row: dict) -> dict | None:
    try:
        data = json.loads(row.get("Participant Data") or "")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _tags(row: dict) -> list[str]:
    return [t for t in (row.get("Message Tags") or "").split(", ") if t]


def _timestamp(row: dict) -> datetime:
    return datetime.fromisoformat(row["Message Date"])


def _gestational_age(data: dict | None, at: datetime) -> int | str:
    """Mirror of User.current_gestational_age() evaluated at the message time."""
    if not data or data.get("gestational_age_at_enrollment") is None or not data.get("enrolled_at"):
        return ""
    enrolled_at = datetime.fromisoformat(data["enrolled_at"])
    return data["gestational_age_at_enrollment"] + (at - enrolled_at).days // 7


def _danger_keywords(tags: list[str]) -> str:
    keywords = []
    for tag in tags:
        if tag.startswith("danger_keyword:"):
            category, _, keyword = tag.removeprefix("danger_keyword:").partition(":")
            order = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)
            keywords.append((order, keyword))
    return ", ".join(keyword for _, keyword in sorted(keywords, key=lambda item: item[0]))


def _consented_participants(rows: list[dict]) -> set[str]:
    latest: dict[str, tuple[datetime, dict]] = {}
    for row in rows:
        data = _participant_data(row)
        if data is None:
            continue
        key = row["Participant Public ID"]
        at = _timestamp(row)
        if key not in latest or at >= latest[key][0]:
            latest[key] = (at, data)
    return {
        key
        for key, (_, data) in latest.items()
        if data.get("consent_given") is True and data.get("study_participant") is True
    }


def _pair_turns(rows: list[dict]) -> dict[int, list[dict]]:
    """Group each AI reply with the user message just before it in the same session.

    OCS writes each exchange as its human row followed by its AI row. The "Trace ID"
    column cannot be used for this: OCS only fills it when an external tracing
    provider is configured, and leaves it blank otherwise. Returns, for each row
    (by ``id``), the rows of its exchange.
    """
    turns: dict[int, list[dict]] = {}
    pending: dict[str, dict] = {}  # session id -> human row still waiting for its reply
    for row in rows:
        session = row["Session ID"]
        if row["Message Type"] == "human":
            turns[id(row)] = [row]
            pending[session] = row
        elif session in pending:
            human = pending.pop(session)
            turns[id(human)].append(row)
            turns[id(row)] = turns[id(human)]
        else:
            turns[id(row)] = [row]
    return turns


def convert_ocs_export(rows: Iterable[dict], wa_id_to_user_id: dict[str, str]) -> list[dict]:
    """Convert OCS export rows to Zeya rows keyed by ``user_key`` instead of ``study_id``.

    ``user_key`` is the linked Zeya user id, or ``ocs:<participant public id>``.
    """
    rows = [r for r in rows if r.get("Message Type") in DIRECTIONS]
    consented = _consented_participants(rows)
    turns = _pair_turns(rows)

    output = []
    for row in sorted(rows, key=_timestamp):
        if row["Participant Public ID"] not in consented:
            continue
        turn = turns[id(row)]
        if any("registration:first_contact" in _tags(r) for r in turn):
            continue
        direction = DIRECTIONS[row["Message Type"]]
        tags = _tags(row)
        if direction == "outgoing" and "registration" in tags:
            continue

        data = _participant_data(row)
        at = _timestamp(row)
        is_danger = direction == "outgoing" and any(t.startswith("danger_sign:") for t in tags)
        response_time_ms: int | str = ""
        if direction == "outgoing":
            incoming = [r for r in turn if r["Message Type"] == "human"]
            if incoming:
                response_time_ms = int((at - _timestamp(incoming[0])).total_seconds() * 1000) or ""

        user_id = wa_id_to_user_id.get(_phone(row["Participant Identifier"]))
        output.append(
            {
                "user_key": user_id or f"ocs:{row['Participant Public ID']}",
                "study_group": (data or {}).get("study_group") or "",
                "direction": direction,
                "message_text": row["Message Content"],
                "gestational_age": _gestational_age(data, at),
                "danger_sign": is_danger,
                "danger_keywords": _danger_keywords(tags) if is_danger else "",
                "response_time_ms": response_time_ms,
                "timestamp": at.isoformat(),
            }
        )
    return output


def assign_study_ids(rows: list[dict], zeya_user_ids: Iterable[str]) -> list[dict]:
    """Removed: assign_study_ids re-sorted all keys on every call, making IDs unstable.

    Calling this function now raises ``TypeError`` with migration guidance.  Use
    ``ocs.study_ids.locked_registry`` with ``--study-id-registry`` on the CLI.
    See docs/study-export-operations.md for the migration guide.
    """
    raise TypeError(
        "assign_study_ids is no longer supported: it re-sorts all keys on every call "
        "and produces unstable IDs when new earlier-sorting participants are added.  "
        "Use --study-id-registry (python -m ocs.study_ids create ...) for stable IDs.  "
        "See docs/study-export-operations.md."
    )


def _resolve_no_follow(p: str) -> int:
    """Return inode number of *p* without following a final symlink."""
    return os.lstat(p).st_ino


def _same_inode(a: str, b: str) -> bool:
    """True when *a* and *b* resolve to the same underlying file (both follow symlinks).

    Uses ``os.stat`` for both sides so that symlinks pointing to the same real file
    are detected regardless of which name is used.  When either path does not exist
    (e.g. a lock file not yet created), falls back to lexical path comparison so
    deterministic paths like the registry ``.lock`` sibling are still protected.
    """
    try:
        sa = os.stat(a)
        sb = os.stat(b)
        return sa.st_ino == sb.st_ino and sa.st_dev == sb.st_dev
    except OSError:
        # At least one path does not exist; compare canonical lexical paths.
        try:
            return Path(a).resolve() == Path(b).resolve()
        except OSError:
            return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ocs-export", required=True, help="CSV exported from the OCS chatbot sessions page")
    parser.add_argument("--zeya-users", help="CSV with user_id,whatsapp_id from the Zeya database")
    parser.add_argument(
        "--study-id-registry",
        required=False,
        help=(
            "Path to the persistent study-ID registry JSON (ocs.study_ids). "
            "REQUIRED for stable IDs across multiple exports. "
            "Create with: python -m ocs.study_ids create --registry R.json [--seed zeya_users.csv]. "
            "Omitting this flag is an error; the deprecated assign_study_ids fallback is not invoked."
        ),
    )
    parser.add_argument("--out", help="output path (default: stdout)")
    args = parser.parse_args(argv)

    # S06: require --study-id-registry; refuse silent fallback.
    if not args.study_id_registry:
        print(
            "error: --study-id-registry is required for stable IDs across multiple exports.\n"
            "Create a registry first: python -m ocs.study_ids create --registry R.json\n"
            "See docs/study-export-operations.md for the full migration guide.",
            file=sys.stderr,
        )
        return 1

    # S09: reject --out that aliases any input or the registry lock file.
    # F5: always protect the lock path even when it does not yet exist —
    # the path is deterministic and must not be overwritten before locking.
    if args.out:
        reg_path_tentative = Path(args.study_id_registry)
        protected = [
            p
            for p in [
                args.ocs_export,
                args.study_id_registry,
                args.zeya_users,
                str(reg_path_tentative.with_suffix(".lock")),  # always, no exists() check
            ]
            if p is not None
        ]
        for input_path in protected:
            if _same_inode(args.out, input_path):
                print(
                    f"error: --out {args.out!r} resolves to the same file as an input "
                    f"({input_path!r}); refusing to overwrite.",
                    file=sys.stderr,
                )
                return 1

    with open(args.ocs_export, newline="", encoding="utf-8") as f:
        ocs_rows = list(csv.DictReader(f))

    wa_id_to_user_id: dict[str, str] = {}
    if args.zeya_users:
        with open(args.zeya_users, newline="", encoding="utf-8") as f:
            wa_id_to_user_id = {_digits(r["whatsapp_id"]): r["user_id"] for r in csv.DictReader(f)}

    converted = convert_ocs_export(ocs_rows, wa_id_to_user_id)

    from ocs.study_ids import RegistryError, locked_registry

    reg_path = Path(args.study_id_registry)
    csv_text: str | None = None
    try:
        with locked_registry(reg_path) as reg:
            # Build the ID map and rows entirely in memory.
            id_map = {r["user_key"]: reg.allocate(r["user_key"]) for r in converted}
            rows_out = [
                {"study_id": id_map[r["user_key"]], **{k: v for k, v in r.items() if k != "user_key"}}
                for r in converted
            ]

            # Render CSV to an in-memory spool BEFORE committing the registry.
            # If the render raises, reg.save() is never called; no registry change persists.
            spool = io.StringIO()
            writer = csv.writer(spool)
            writer.writerow(ZEYA_COLUMNS)
            for row in rows_out:
                writer.writerow([row[column] for column in ZEYA_COLUMNS])
            csv_text = spool.getvalue()

            # Commit registry to disk FIRST (while still under lock).
            # Only after this succeeds will we publish any output.
            # If reg.save() raises: locked_registry does NOT auto-save; csv_text discarded.
            reg.save()
            # locked_registry.__exit__ skips auto-save because reg._committed is True.

    except (RegistryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Registry committed; now publish output.
    # If this step fails: retained allocation is OK (IDs never recycled).
    if csv_text is None:
        return 1  # defensive guard; should not occur after successful context exit

    if args.out:
        out_path = Path(args.out)
        fd, tmp_str = tempfile.mkstemp(prefix=".export-tmp-", suffix=".csv", dir=out_path.parent)
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
                fd = -1
                fh.write(csv_text)
        except BaseException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp_str)
            except OSError:
                pass
            raise
        try:
            os.replace(tmp_str, args.out)
        except OSError as exc:
            try:
                os.unlink(tmp_str)
            except OSError:
                pass
            print(f"error: writing output failed: {exc}", file=sys.stderr)
            return 1
    else:
        # Stdout: write after registry commit.
        sys.stdout.write(csv_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
