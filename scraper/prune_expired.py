#!/usr/bin/env python3

import json
from datetime import datetime, timedelta
from pathlib import Path

RECENTLY_EXPIRED_DAYS = 7
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPIRED_FILE = PROJECT_ROOT / "data" / "expired.json"


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def main():
    if not EXPIRED_FILE.exists():
        print("PASS: no expired.json exists; nothing to prune.")
        return 0

    data = json.loads(EXPIRED_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("ERROR: data/expired.json must contain an object.")

    opportunities = data.get("opportunities")
    if not isinstance(opportunities, list):
        raise SystemExit("ERROR: data/expired.json has no opportunities list.")

    today = datetime.now().date()
    cutoff = today - timedelta(days=RECENTLY_EXPIRED_DAYS)
    kept = []
    removed = 0

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue

        deadline = parse_date(opportunity.get("deadline"))
        end_date = parse_date(opportunity.get("end_date"))

        # A deadline is the expiry date when one exists. For opportunities
        # without a deadline, the activity itself must have ended before the
        # opportunity can be considered recently expired.
        expiry_date = deadline if deadline is not None else end_date

        if expiry_date is None:
            removed += 1
            continue

        age_days = (today - expiry_date).days

        # Never publish future-dated records in the recently expired table.
        if 0 <= age_days <= RECENTLY_EXPIRED_DAYS:
            kept.append(opportunity)
        else:
            removed += 1

    kept.sort(
        key=lambda item: (
            item.get("deadline") or item.get("end_date") or "",
            item.get("last_seen") or "",
        ),
        reverse=True,
    )

    output = {
        "generated_at": datetime.now().isoformat(),
        "recently_expired_days": RECENTLY_EXPIRED_DAYS,
        "count": len(kept),
        "opportunities": kept,
    }

    temporary = EXPIRED_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(EXPIRED_FILE)

    print(f"PASS: retained {len(kept)} recently expired opportunities.")
    print(f"PASS: removed {removed} invalid or older-than-{RECENTLY_EXPIRED_DAYS}-day opportunities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
