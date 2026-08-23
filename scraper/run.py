#!/usr/bin/env python3

import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_DIR = Path(__file__).resolve().parent

# When executing scraper/run.py directly, Python puts the scraper directory
# first on sys.path. That makes `import scraper.scraper` resolve scraper.py as
# a top-level module named `scraper`, which is not a package. Remove that
# script-directory entry so the repository-root namespace package is resolved
# correctly.
sys.path[:] = [
    entry
    for entry in sys.path
    if Path(entry or ".").resolve() != SCRAPER_DIR
]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scraper.scraper as scraper

_ORIGINAL_ENTRY_IS_STALE = scraper.entry_is_stale
_ORIGINAL_BUILD_WORK_QUEUE = scraper.build_work_queue


def _parse_cached_deadline(value):
    if not value:
        return None
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raw = f"{raw}T23:59:59"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_cached_activity_end(value):
    if not value:
        return None
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raw = f"{raw}T23:59:59"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_past(value):
    if value is None:
        return False
    try:
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        return value < now
    except TypeError:
        return False


def entry_is_stale(entry):
    """Preserve the normal 24h policy, but urgently recheck stale expiry data."""
    if isinstance(entry, dict) and entry.get("status") == "scanned":
        result = entry.get("result")
        if isinstance(result, dict):
            deadline = _parse_cached_deadline(result.get("deadline"))
            if deadline is not None and _is_past(deadline):
                return True

            if not result.get("deadline"):
                activity_end = _parse_cached_activity_end(result.get("end_date"))
                if activity_end is not None and _is_past(activity_end):
                    return True

    return _ORIGINAL_ENTRY_IS_STALE(entry)


def build_work_queue(current_opportunities, checkpoint):
    """Prioritize records whose cached expiry state may be stale."""
    queue = _ORIGINAL_BUILD_WORK_QUEUE(
        current_opportunities,
        checkpoint,
    )

    processed = checkpoint.get("processed", {})
    urgent = []
    normal = []

    for opid in queue:
        entry = processed.get(str(opid), {})
        result = entry.get("result") if isinstance(entry, dict) else None

        is_urgent = False
        if isinstance(result, dict):
            deadline = _parse_cached_deadline(result.get("deadline"))
            if deadline is not None and _is_past(deadline):
                is_urgent = True
            elif not result.get("deadline"):
                activity_end = _parse_cached_activity_end(result.get("end_date"))
                if activity_end is not None and _is_past(activity_end):
                    is_urgent = True

        if is_urgent:
            urgent.append(opid)
        else:
            normal.append(opid)

    return urgent + normal


scraper.entry_is_stale = entry_is_stale
scraper.build_work_queue = build_work_queue

print("URGENT RECHECK MODE: stale expired deadlines/activity endings are prioritized.")
print("Normal detail recheck interval, batch size, and request delays are unchanged.")

raise SystemExit(scraper.main())
