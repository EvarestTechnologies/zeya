"""
Build an Open Chat Studio participant import CSV from Zeya's users table.

Imported participants carry their consent, name, gestational age, language and
study group, so enrolled women go straight to the chatbot without registering again.

    \\copy (SELECT id, whatsapp_id, name, consent_given, consent_given_at,
            gestational_age_at_enrollment, expected_delivery_date, enrolled_at,
            registration_complete, language_preference, study_group, is_active
            FROM users) TO 'zeya_users_full.csv' CSV HEADER

    python -m ocs.seed_participants --zeya-users zeya_users_full.csv --out ocs_participants.csv

Then import ocs_participants.csv on the chatbot's Participants page in OCS.

Users that an admin deactivated after they consented are left out and listed on
stderr: Zeya ignored their messages, and they must not start getting replies
without a decision from the study team.
"""

import argparse
import csv
import json
import sys
from datetime import datetime

OCS_COLUMNS = [
    "identifier",
    "channel",
    "name",
    "data.welcome_sent",
    "data.consent_given",
    "data.consent_declined",
    "data.consent_given_at",
    "data.name_collected",
    "data.gestational_age_at_enrollment",
    "data.expected_delivery_date",
    "data.enrolled_at",
    "data.registration_complete",
    "data.language_preference",
    "data.study_group",
    "data.zeya_user_id",
    "data.study_participant",
]


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"t", "true", "1", "yes"}


def _iso_datetime(value: str) -> str | None:
    """Parse an ISO datetime string, raising a safe ValueError without echoing the value."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("participant data contains an invalid date value") from None


def _gestational_age_weeks(value: str) -> int:
    """Parse gestational age weeks, raising a safe error without echoing the value."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError("participant data contains an invalid gestational age") from None


def zeya_user_to_participant(user: dict) -> dict:
    """Map one row of the Zeya users table to one OCS import row."""
    consent_given = _bool(user["consent_given"])
    name = (user.get("name") or "").strip()
    weeks = user.get("gestational_age_at_enrollment")
    data = {
        "welcome_sent": True,
        "consent_given": consent_given,
        "consent_declined": True if not consent_given and not _bool(user["is_active"]) else None,
        "consent_given_at": _iso_datetime(user.get("consent_given_at")),
        "name_collected": True if name else None,
        "gestational_age_at_enrollment": _gestational_age_weeks(weeks) if weeks else None,
        "expected_delivery_date": user.get("expected_delivery_date") or None,
        "enrolled_at": _iso_datetime(user.get("enrolled_at")),
        "registration_complete": _bool(user["registration_complete"]),
        "language_preference": user.get("language_preference") or "en",
        "study_group": user.get("study_group") or "intervention",
        "zeya_user_id": user["id"],
        # Marks trial participants; the export keeps only these (ZEYA is open to anyone).
        "study_participant": True,
    }
    # OCS matches an imported participant against the wa_id in Meta's webhook exactly,
    # so the identifier must be digits only (OCS ADR-0043).
    identifier = "".join(c for c in user["whatsapp_id"] if c.isdigit())
    row = {"identifier": identifier, "channel": "whatsapp", "name": name}
    for key, value in data.items():
        # OCS parses each data.* cell as JSON and skips empty cells.
        row[f"data.{key}"] = "" if value is None else json.dumps(value)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zeya-users", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    try:
        with open(args.zeya_users, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            users = list(reader)
            fieldnames: list[str] = list(reader.fieldnames or [])
    except UnicodeDecodeError:
        print("error: seed source is not valid UTF-8", file=sys.stderr)
        return 1
    except (FileNotFoundError, OSError, csv.Error):
        print("error: could not read seed source", file=sys.stderr)
        return 1

    # Validate CSV headers: no blank, no duplicates, required columns present.
    _REQUIRED_HEADERS = frozenset({"id", "whatsapp_id", "consent_given", "is_active", "registration_complete"})
    if any(not (f or "").strip() for f in fieldnames):
        print("error: seed CSV has blank column header(s)", file=sys.stderr)
        return 1
    if len(fieldnames) != len(set(fieldnames)):
        print("error: seed CSV has duplicate column header(s)", file=sys.stderr)
        return 1
    if not _REQUIRED_HEADERS.issubset(set(fieldnames)):
        print("error: seed CSV is missing required column(s)", file=sys.stderr)
        return 1

    # Validate required columns: fail before processing if any mandatory field
    # is absent from the headers or missing (None) in a row.
    rows, skipped = [], []
    for user in users:
        # None restkey: extra unnamed cells
        if None in user:
            print("error: seed CSV row has unexpected extra cell(s)", file=sys.stderr)
            return 1
        # None values: missing declared cell (row shorter than headers)
        if any(v is None for v in user.values()):
            print("error: seed CSV row is missing a declared cell", file=sys.stderr)
            return 1

        if _bool(user["consent_given"]) and not _bool(user["is_active"]):
            skipped.append(user["whatsapp_id"])
            continue
        try:
            rows.append(zeya_user_to_participant(user))
        except (ValueError, KeyError, TypeError):
            # Date parsing, missing field, or unexpected type: fail cleanly.
            print("error: invalid participant data (not echoing content)", file=sys.stderr)
            return 1

    try:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OCS_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    except OSError:
        print("error: could not write output", file=sys.stderr)
        return 1

    print(f"Wrote {len(rows)} participant(s).", file=sys.stderr)
    if skipped:
        print(f"Skipped {len(skipped)} deactivated consented user(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
