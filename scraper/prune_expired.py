#!/usr/bin/env python3

import json
from datetime import datetime, timedelta
from pathlib import Path

RECENTLY_EXPIRED_DAYS = 7
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
EXPIRED_FILE = DATA_DIR / "expired.json"


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def expiry_date_for(opportunity):
    deadline = parse_date(opportunity.get("deadline"))
    if deadline is not None:
        return deadline
    return parse_date(opportunity.get("end_date"))


def load_object(path, label):
    if not path.exists():
        return {
            "generated_at": datetime.now().isoformat(),
            "count": 0,
            "opportunities": [],
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: {label} is invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} must contain an object.")

    opportunities = data.get("opportunities")
    if not isinstance(opportunities, list):
        raise SystemExit(f"ERROR: {label} has no opportunities list.")

    return data


def main():
    active_data = load_object(OPPORTUNITIES_FILE, "data/opportunities.json")
    expired_data = load_object(EXPIRED_FILE, "data/expired.json")

    active = active_data["opportunities"]
    existing_expired = expired_data["opportunities"]

    today = datetime.now().date()
    cutoff = today - timedelta(days=RECENTLY_EXPIRED_DAYS)

    kept_active = []
    newly_expired = []

    for opportunity in active:
        if not isinstance(opportunity, dict):
            continue

        expiry = expiry_date_for(opportunity)

        if expiry is not None and expiry < today:
            newly_expired.append(opportunity)
        else:
            kept_active.append(opportunity)

    existing_by_id = {}
    for opportunity in existing_expired:
        if not isinstance(opportunity, dict):
            continue
        opid = str(opportunity.get("id", "")).strip()
        if opid:
            existing_by_id[opid] = opportunity

    moved = 0
    for opportunity in newly_expired:
        opid = str(opportunity.get("id", "")).strip()
        if not opid:
            continue
        existing_by_id[opid] = {
            **opportunity,
            "last_seen": opportunity.get("last_seen") or datetime.now().isoformat(),
            "reason": (
                "Application deadline has expired."
                if parse_date(opportunity.get("deadline")) is not None
                else "Activity has finished."
            ),
        }
        moved += 1

    active_ids = {
        str(item.get("id", "")).strip()
        for item in kept_active
        if isinstance(item, dict)
    }

    kept_expired = []
    for opportunity in existing_by_id.values():
        if not isinstance(opportunity, dict):
            continue

        opid = str(opportunity.get("id", "")).strip()
        if not opid or opid in active_ids:
            continue

        expiry = expiry_date_for(opportunity)
        if expiry is None:
            continue

        age_days = (today - expiry).days
        if 0 <= age_days <= RECENTLY_EXPIRED_DAYS:
            kept_expired.append(opportunity)

    kept_expired.sort(
        key=lambda item: (
            expiry_date_for(item) or datetime.min.date(),
            item.get("last_seen") or "",
        ),
        reverse=True,
    )

    active_data["count"] = len(kept_active)
    active_data["opportunities"] = kept_active

    new_ids = active_data.get("new_opportunity_ids", [])
    if isinstance(new_ids, list):
        active_data["new_opportunity_ids"] = [
            str(opid)
            for opid in new_ids
            if str(opid) in active_ids
        ]

    active_data["expired_pruned_at"] = datetime.now().isoformat()

    expired_output = {
        "generated_at": datetime.now().isoformat(),
        "recently_expired_days": RECENTLY_EXPIRED_DAYS,
        "count": len(kept_expired),
        "opportunities": kept_expired,
    }

    active_tmp = OPPORTUNITIES_FILE.with_suffix(".json.tmp")
    active_tmp.write_text(
        json.dumps(active_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    active_tmp.replace(OPPORTUNITIES_FILE)

    expired_tmp = EXPIRED_FILE.with_suffix(".json.tmp")
    expired_tmp.write_text(
        json.dumps(expired_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    expired_tmp.replace(EXPIRED_FILE)

    print(f"PASS: active opportunities retained: {len(kept_active)}")
    print(f"PASS: moved newly expired active opportunities: {moved}")
    print(f"PASS: recently expired opportunities retained: {len(kept_expired)}")
    print(f"PASS: recently expired cutoff: {cutoff}")
    print("PASS: active and recently expired datasets are disjoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
