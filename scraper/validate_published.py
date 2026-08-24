#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
EXPIRED_FILE = DATA_DIR / "expired.json"

MAX_DATASET_AGE = timedelta(hours=2)
RECENTLY_EXPIRED_DAYS = 7
REQUIRED_FIELDS = (
    "id",
    "title",
    "country",
    "town",
    "start_date",
    "end_date",
    "deadline",
    "activity_type",
    "eligible_countries",
    "url",
)


def parse_datetime(value, label):
    if not value:
        raise RuntimeError(f"ERROR: {label} is missing.")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"ERROR: {label} is not a valid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date(value, label):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError as exc:
        raise RuntimeError(f"ERROR: invalid date in {label}: {value}") from exc


def validate_required_fields(records, dataset_name):
    for index, opportunity in enumerate(records, start=1):
        if not isinstance(opportunity, dict):
            raise RuntimeError(f"ERROR: {dataset_name} record {index} is not an object.")
        missing = [field for field in REQUIRED_FIELDS if field not in opportunity]
        if missing:
            raise RuntimeError(
                f"ERROR: {dataset_name} record {index} ({opportunity.get('id', '?')}) is missing: {', '.join(missing)}"
            )
        if not str(opportunity.get("id", "")).strip():
            raise RuntimeError(f"ERROR: {dataset_name} contains a record with an empty id.")
        if not isinstance(opportunity.get("eligible_countries"), list):
            raise RuntimeError(
                f"ERROR: {dataset_name} record {opportunity.get('id')} has invalid eligible_countries."
            )


def expiry_date_for(opportunity):
    deadline = parse_date(opportunity.get("deadline"), f"deadline for {opportunity.get('id')}")
    end_date = parse_date(opportunity.get("end_date"), f"end_date for {opportunity.get('id')}")
    return deadline if deadline is not None else end_date


def validate_active(records, today):
    seen = set()
    for opportunity in records:
        opid = str(opportunity["id"])
        if opid in seen:
            raise RuntimeError(f"ERROR: duplicate active opportunity id: {opid}")
        seen.add(opid)

        deadline = parse_date(opportunity.get("deadline"), f"deadline for active opportunity {opid}")
        end_date = parse_date(opportunity.get("end_date"), f"end_date for active opportunity {opid}")

        if deadline is not None and deadline < today:
            raise RuntimeError(f"ERROR: expired deadline remains active: {opid} ({deadline})")

        if deadline is None and end_date is not None and end_date < today:
            raise RuntimeError(f"ERROR: finished no-deadline activity remains active: {opid} ({end_date})")

    return seen


def validate_expired(records, today):
    seen = set()
    cutoff = today - timedelta(days=RECENTLY_EXPIRED_DAYS)
    for opportunity in records:
        opid = str(opportunity["id"])
        if opid in seen:
            raise RuntimeError(f"ERROR: duplicate recently expired opportunity id: {opid}")
        seen.add(opid)

        expiry = expiry_date_for(opportunity)
        if expiry is None:
            raise RuntimeError(f"ERROR: recently expired opportunity has no deadline/end date: {opid}")
        if expiry > today:
            raise RuntimeError(f"ERROR: future-dated record appears in recently expired: {opid} ({expiry})")
        if expiry < cutoff:
            raise RuntimeError(
                f"ERROR: expired opportunity older than {RECENTLY_EXPIRED_DAYS} days remains published: {opid} ({expiry})"
            )

    return seen


def load_object(path, label):
    if not path.exists():
        raise RuntimeError(f"ERROR: {label} is missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ERROR: {label} is invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"ERROR: {label} must contain a JSON object.")
    return data


def validate():
    active_payload = load_object(OPPORTUNITIES_FILE, "data/opportunities.json")
    expired_payload = load_object(EXPIRED_FILE, "data/expired.json")

    active = active_payload.get("opportunities")
    expired = expired_payload.get("opportunities")

    if not isinstance(active, list) or not active:
        raise RuntimeError("ERROR: active opportunity dataset is empty or invalid.")
    if not isinstance(expired, list):
        raise RuntimeError("ERROR: recently expired dataset is invalid.")

    if active_payload.get("count") != len(active):
        raise RuntimeError("ERROR: active count metadata does not match records.")
    if expired_payload.get("count") != len(expired):
        raise RuntimeError("ERROR: expired count metadata does not match records.")

    generated_at = parse_datetime(active_payload.get("generated_at"), "data/opportunities.json generated_at")
    now = datetime.now(timezone.utc)
    age = now - generated_at
    if age < timedelta(seconds=0):
        raise RuntimeError("ERROR: dataset generated_at is in the future.")
    if age > MAX_DATASET_AGE:
        raise RuntimeError(f"ERROR: published dataset is stale ({age}).")

    validate_required_fields(active, "active")
    validate_required_fields(expired, "expired")

    today = datetime.now().date()
    active_ids = validate_active(active, today)
    expired_ids = validate_expired(expired, today)

    overlap = sorted(active_ids & expired_ids)
    if overlap:
        raise RuntimeError(
            "ERROR: active and recently expired datasets overlap: "
            + ", ".join(overlap)
        )

    new_ids = active_payload.get("new_opportunity_ids", [])
    if not isinstance(new_ids, list):
        raise RuntimeError("ERROR: new_opportunity_ids must be a list.")

    normalized_new_ids = [str(value) for value in new_ids]
    if len(normalized_new_ids) != len(set(normalized_new_ids)):
        raise RuntimeError("ERROR: new_opportunity_ids contains duplicates.")

    missing_new_ids = [opid for opid in normalized_new_ids if opid not in active_ids]
    if missing_new_ids:
        raise RuntimeError(
            "ERROR: new_opportunity_ids contains IDs that are not in the active dataset: "
            + ", ".join(missing_new_ids)
        )

    if not isinstance(active_payload.get("scan_complete"), bool):
        raise RuntimeError("ERROR: scan_complete must be boolean.")

    print(f"PASS: active opportunities: {len(active)}")
    print(f"PASS: recently expired opportunities: {len(expired)}")
    print(f"PASS: dataset age: {age}")
    print(f"PASS: scan_complete: {active_payload['scan_complete']}")
    print(f"PASS: NEW badge IDs: {len(normalized_new_ids)}")
    print("PASS: active/expired date classification is valid.")
    print("PASS: active and recently expired datasets are disjoint.")
    print("PASS: published dataset passed production validation.")


if __name__ == "__main__":
    try:
        validate()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
