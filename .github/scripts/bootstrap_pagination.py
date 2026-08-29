from pathlib import Path
import re


SCRAPER_PATH = Path("scraper/scraper.py")

MARKER = "# API_PAGINATION_DEDUP_V6"
FUNCTION_START = "def fetch_current_opportunities():"
FUNCTION_END = "# ============================================================================\n# DETAIL PAGE PARSING"

NEW_FUNCTION_LINES = [
    "def fetch_current_opportunities():",
    "    # API_PAGINATION_DEDUP_V6",
    "    print(\"=\" * 70)",
    "    print(\"FETCHING CURRENT ESC OPPORTUNITIES\")",
    "    print(\"=\" * 70)",
    "",
    "    session = requests.Session()",
    "    opportunities_by_id = {}",
    "    offset = 0",
    "    total = None",
    "",
    "    try:",
    "        while True:",
    "            data = fetch_api_page(session, offset)",
    "            if data is None:",
    "                raise RuntimeError(\"Could not retrieve the current opportunity list.\")",
    "",
    "            hits = data.get(\"hits\", {})",
    "            total_info = hits.get(\"total\", {})",
    "            if total is None:",
    "                if isinstance(total_info, dict):",
    "                    total = int(total_info.get(\"value\", 0) or 0)",
    "                else:",
    "                    total = int(total_info or 0)",
    "                print(f\"API reports {total} opportunities.\", flush=True)",
    "",
    "            page_hits = hits.get(\"hits\", [])",
    "            if not page_hits:",
    "                break",
    "",
    "            for hit in page_hits:",
    "                source = hit.get(\"_source\", {})",
    "                opid = source.get(\"opid\") or hit.get(\"_id\")",
    "                if opid is None:",
    "                    continue",
    "                try:",
    "                    source[\"opid\"] = int(opid)",
    "                except (TypeError, ValueError):
                    continue",
    "                opportunities_by_id.setdefault(str(source[\"opid\"]), source)",
    "",
    "            offset += API_PAGE_SIZE",
    "            unique_count = len(opportunities_by_id)",
    "            print(f\"Retrieved {unique_count}/{total} unique opportunities (raw page hits: {len(page_hits)})\", flush=True)",
    "            if total is not None and unique_count >= total:",
    "                break",
    "    finally:",
    "        session.close()",
    "",
    "    opportunities = list(opportunities_by_id.values())",
    "    if total is not None and len(opportunities) != total:",
    "        raise RuntimeError(f\"Incomplete API retrieval: {len(opportunities)}/{total} unique opportunities\")",
    "    return opportunities",
    "",
    "",
]


def main():
    if not SCRAPER_PATH.exists():
        raise SystemExit("ERROR: scraper/scraper.py does not exist.")

    text = SCRAPER_PATH.read_text(encoding="utf-8")

    start = text.find(FUNCTION_START)
    end = text.find(FUNCTION_END, start)
    if start < 0 or end < 0:
        raise SystemExit(
            "ERROR: could not locate fetch_current_opportunities boundaries; no source change made."
        )

    replacement = "\n".join(NEW_FUNCTION_LINES)
    text = text[:start] + replacement + "\n" + text[end:]

    text, replacements = re.subn(
        r"(?m)^API_PAGE_SIZE\s*=\s*\d+\s*$",
        "API_PAGE_SIZE = 1000",
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit(
            "ERROR: could not safely set API_PAGE_SIZE to 1000; no source change made."
        )

    text, replacements = re.subn(
        r'(?m)^\s*"sort\[created\]": "desc",\s*$',
        '        "sort[opid]": "asc",',
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit(
            "ERROR: could not safely switch API ordering to stable opid ordering; no source change made."
        )

    first_seen_marker = '    history = checkpoint[\n        "history"\n    ]\n'
    first_seen_block = first_seen_marker + '''\n    new_first_seen = checkpoint.setdefault(\n        "new_opportunity_first_seen_at",\n        {},\n    )\n\n    discovered_at = now_iso()\n    newly_discovered = 0\n\n    for current_opportunity in current_opportunities:\n        current_id = str(current_opportunity["opid"])\n        if current_id not in processed and current_id not in new_first_seen:\n            new_first_seen[current_id] = discovered_at\n            newly_discovered += 1\n\n    if newly_discovered:\n        print(\n            f"New opportunities discovered in API snapshot: {newly_discovered}",\n            flush=True,\n        )\n\n    save_checkpoint(checkpoint)\n'''
    if first_seen_marker in text and 'new_first_seen = checkpoint.setdefault' not in text:
        text = text.replace(first_seen_marker, first_seen_block, 1)

    get_section_start = text.find("def get_section(card, heading_name):")
    get_topics_start = text.find("def get_topics(card):", get_section_start)
    if get_section_start < 0 or get_topics_start < 0:
        raise SystemExit(
            "ERROR: could not locate get_section/get_topics boundaries; no source change made."
        )

    new_get_section = '''def get_section(card, heading_name):\n    if card is None:\n        return None\n\n    for heading in card.find_all(\n        "h6"\n    ):\n        current = heading.get_text(\n            " ",\n            strip=True,\n        )\n\n        if (\n            current.lower()\n            != heading_name.lower()\n        ):\n            continue\n\n        paragraphs = []\n\n        for sibling in heading.next_siblings:\n            sibling_name = getattr(\n                sibling,\n                "name",\n                None,\n            )\n\n            if sibling_name == "h6":\n                break\n\n            if sibling_name == "p":\n                value = sibling.get_text(\n                    " ",\n                    strip=True,\n                )\n                if value:\n                    paragraphs.append(value)\n\n        if paragraphs:\n            return " ".join(paragraphs)\n\n        return None\n\n\n'''
    text = text[:get_section_start] + new_get_section + text[get_topics_start:]

    migration_marker = "# ELIGIBILITY_PARSER_MIGRATION_V1"
    if migration_marker not in text:
        migration_block = '''\n# ELIGIBILITY_PARSER_MIGRATION_V1\nELIGIBILITY_PARSER_MIGRATION_VERSION = 1\n\n\ndef _apply_eligibility_parser_migration(checkpoint):\n    if checkpoint.get("eligibility_parser_migration_version") == ELIGIBILITY_PARSER_MIGRATION_VERSION:\n        return False\n\n    processed = checkpoint.get("processed", {})\n    invalidated = 0\n\n    for entry in processed.values():\n        if not isinstance(entry, dict):\n            continue\n        if entry.get("status") != "scanned":\n            continue\n        entry["checked_at"] = "2000-01-01T00:00:00"\n        invalidated += 1\n\n    checkpoint["eligibility_parser_migration_version"] = ELIGIBILITY_PARSER_MIGRATION_VERSION\n    print(\n        f"Eligibility parser migration queued {invalidated} existing records for one-time recheck.",\n        flush=True,\n    )\n    return True\n\n\n'''
        insert_at = text.find("# ============================================================================\n# WORK QUEUE")
        if insert_at < 0:
            raise SystemExit("ERROR: could not locate WORK QUEUE insertion point; no source change made.")
        text = text[:insert_at] + migration_block + text[insert_at:]

    # Prioritize the known 54038 validation case once it is stale/new.
    priority_marker = "# PRIORITIZE_54038_V1"
    if priority_marker not in text:
        old_return = '''    return (\n        new_ids\n        + retry_ids\n        + stale_ids\n    )\n'''
        new_return = '''    # PRIORITIZE_54038_V1\n    if "54038" in stale_ids:\n        stale_ids.remove("54038")\n        return ["54038"] + new_ids + retry_ids + stale_ids\n\n    return (\n        new_ids\n        + retry_ids\n        + stale_ids\n    )\n'''
        if old_return not in text:
            raise SystemExit("ERROR: could not locate work-queue return block; no source change made.")
        text = text.replace(old_return, new_return, 1)

    # Run the one-time migration immediately after checkpoint load.
    migration_call = '    _apply_eligibility_parser_migration(checkpoint)\n'
    migration_anchor = '    history = checkpoint[\n        "history"\n    ]\n'
    if migration_call not in text:
        if migration_anchor not in text:
            raise SystemExit("ERROR: could not locate checkpoint history block for eligibility migration; no source change made.")
        text = text.replace(migration_anchor, migration_anchor + "\n" + migration_call, 1)

    if MARKER not in text:
        raise SystemExit("ERROR: stable pagination marker was not written; no source change made.")

    SCRAPER_PATH.write_text(text, encoding="utf-8")
    print("PASS: stable API pagination/deduplication fix applied.")
    print("PASS: API page size remains 1000; detail batch size unchanged.")
    print("PASS: API ordering now uses stable opid ordering to prevent page shifts during updates.")
    print("PASS: new API IDs are recorded immediately for the 24-hour NEW window.")
    print("PASS: participant-country parser now collects every paragraph in the eligibility section.")
    print("PASS: one-time eligibility parser migration queues existing records for recheck.")
    print("PASS: opportunity 54038 is prioritized for immediate eligibility revalidation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
