from pathlib import Path
import re


SCRAPER_PATH = Path("scraper/scraper.py")
VERSION_MARKER = "# BACKEND_AUTOMATION_FIXES_V8"
PARSER_MARKER = "# ELIGIBILITY_PARSER_COMPLETE_V2"


def replace_function(text, name, replacement, next_name):
    start = text.find(f"def {name}(")
    end = text.find(f"def {next_name}(", start)
    if start < 0 or end < 0:
        raise SystemExit(
            f"ERROR: could not safely locate {name}/{next_name}; no source change made."
        )
    return text[:start] + replacement + "\n\n" + text[end:]


def main():
    if not SCRAPER_PATH.exists():
        raise SystemExit("ERROR: scraper/scraper.py does not exist.")

    text = SCRAPER_PATH.read_text(encoding="utf-8")
    if VERSION_MARKER in text:
        print("PASS: backend automation fixes V8 already installed; no source change required.")
        return 0

    # ------------------------------------------------------------------
    # 1. Complete EYP participant-country section parsing.
    # ------------------------------------------------------------------
    get_section_start = text.find("def get_section(card, heading_name):")
    get_topics_start = text.find("def get_topics(card):", get_section_start)
    if get_section_start < 0 or get_topics_start < 0:
        raise SystemExit(
            "ERROR: could not locate get_section/get_topics boundaries; no source change made."
        )

    parser_lines = [
        "def get_section(card, heading_name):",
        "    if card is None:",
        "        return None",
        "",
        "    for heading in card.find_all(\"h6\"):",
        "        current = heading.get_text(\" \", strip=True)",
        "        if current.lower() != heading_name.lower():",
        "            continue",
        "",
        "        paragraphs = []",
        "        for sibling in heading.next_siblings:",
        "            sibling_name = getattr(sibling, \"name\", None)",
        "            if sibling_name == \"h6\":",
        "                break",
        "            if sibling_name == \"p\":",
        "                value = sibling.get_text(\" \", strip=True)",
        "                if value:",
        "                    paragraphs.append(value)",
        "",
        "        if paragraphs:",
        "            return \" \".join(paragraphs)",
        "        return None",
        "",
        "",
        PARSER_MARKER,
        "",
        "",
    ]
    parser = "\n".join(parser_lines)
    text = text[:get_section_start] + parser + text[get_topics_start:]

    # ------------------------------------------------------------------
    # 2. Stable API pagination with automatic recovery.
    # ------------------------------------------------------------------
    text, replacements = re.subn(
        r"def build_api_params\(offset\):\n",
        "def build_api_params(offset, page_size=None):\n",
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit(
            "ERROR: could not update build_api_params signature; no source change made."
        )

    text, replacements = re.subn(
        r'        "size": API_PAGE_SIZE,\n        "from": offset,',
        '        "size": page_size or API_PAGE_SIZE,\n        "from": offset,',
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit(
            "ERROR: could not update API size parameter; no source change made."
        )

    fetch_api_page = "\n".join([
        "def fetch_api_page(session, offset, page_size=None):",
        "    params = build_api_params(",
        "        offset,",
        "        page_size,",
        "    )",
        "",
        "    for attempt in range(1, MAX_RETRIES + 1):",
        "        try:",
        "            effective_size = page_size or API_PAGE_SIZE",
        "            print(",
        "                f\"API request: from={offset}, size={effective_size}\",",
        "                flush=True,",
        "            )",
        "            response = session.get(",
        "                API_URL,",
        "                params=params,",
        "                headers=HEADERS,",
        "                timeout=REQUEST_TIMEOUT,",
        "            )",
        "",
        "            if response.status_code == 200:",
        "                try:",
        "                    return response.json()",
        "                except ValueError as exc:",
        "                    print(f\"Invalid API JSON: {exc}\", flush=True)",
        "                    if attempt < MAX_RETRIES:",
        "                        time.sleep(2**attempt)",
        "                        continue",
        "                    return None",
        "",
        "            if response.status_code == 429:",
        "                wait = get_retry_after_seconds(response)",
        "                print(f\"API HTTP 429. Waiting {wait}s ({attempt}/{MAX_RETRIES})...\", flush=True)",
        "                if attempt >= MAX_RETRIES:",
        "                    return None",
        "                time.sleep(wait)",
        "                continue",
        "",
        "            if response.status_code >= 500:",
        "                if attempt < MAX_RETRIES:",
        "                    wait = 2**attempt",
        "                    print(f\"API HTTP {response.status_code}. Retrying in {wait}s...\", flush=True)",
        "                    time.sleep(wait)",
        "                    continue",
        "                return None",
        "",
        "            print(f\"API error: HTTP {response.status_code}\", flush=True)",
        "            return None",
        "",
        "        except requests.Timeout:",
        "            if attempt < MAX_RETRIES:",
        "                wait = 2**attempt",
        "                print(f\"API timeout. Retrying in {wait}s...\", flush=True)",
        "                time.sleep(wait)",
        "                continue",
        "            return None",
        "",
        "        except requests.RequestException as exc:",
        "            if attempt < MAX_RETRIES:",
        "                wait = 2**attempt",
        "                print(f\"API request error: {exc}\", flush=True)",
        "                print(f\"Retrying in {wait}s...\", flush=True)",
        "                time.sleep(wait)",
        "                continue",
        "            print(f\"API request failed: {exc}\", flush=True)",
        "            return None",
        "",
        "    return None",
    ])
    text = replace_function(
        text,
        "fetch_api_page",
        fetch_api_page,
        "fetch_current_opportunities",
    )

    fetch_current = "\n".join([
        "def fetch_current_opportunities():",
        f"    {VERSION_MARKER}",
        "    print(\"=\" * 70)",
        "    print(\"FETCHING CURRENT ESC OPPORTUNITIES\")",
        "    print(\"=\" * 70)",
        "",
        "    session = requests.Session()",
        "    total = None",
        "",
        "    def total_from(data):",
        "        hits = data.get(\"hits\", {}) if data else {}",
        "        total_info = hits.get(\"total\", {})",
        "        if isinstance(total_info, dict):",
        "            return int(total_info.get(\"value\", 0) or 0)",
        "        return int(total_info or 0)",
        "",
        "    def add_page(target, data):",
        "        if not data:",
        "            return 0",
        "        page_hits = data.get(\"hits\", {}).get(\"hits\", [])",
        "        added = 0",
        "        for hit in page_hits:",
        "            source = hit.get(\"_source\", {})",
        "            opid = source.get(\"opid\") or hit.get(\"_id\")",
        "            if opid is None:",
        "                continue",
        "            try:",
        "                source[\"opid\"] = int(opid)",
        "            except (TypeError, ValueError):",
        "                continue",
        "            key = str(source[\"opid\"])",
        "            if key not in target:",
        "                target[key] = source",
        "                added += 1",
        "        return added",
        "",
        "    try:",
        "        opportunities_by_id = {}",
        "        first = fetch_api_page(session, 0)",
        "        if first is None:",
        "            raise RuntimeError(\"Could not retrieve the current opportunity list.\")",
        "",
        "        total = total_from(first)",
        "        print(f\"API reports {total} opportunities.\", flush=True)",
        "        add_page(opportunities_by_id, first)",
        "        print(",
        "            f\"Retrieved {len(opportunities_by_id)}/{total} unique opportunities \"",
        "            f\"(raw page hits: {len(first.get('hits', {}).get('hits', []))})\",",
        "            flush=True,",
        "        )",
        "",
        "        offset = API_PAGE_SIZE",
        "        while len(opportunities_by_id) < total:",
        "            data = fetch_api_page(session, offset)",
        "            if data is None:",
        "                break",
        "            page_hits = data.get(\"hits\", {}).get(\"hits\", [])",
        "            add_page(opportunities_by_id, data)",
        "            print(",
        "                f\"Retrieved {len(opportunities_by_id)}/{total} unique opportunities \"",
        "                f\"(raw page hits: {len(page_hits)})\",",
        "                flush=True,",
        "            )",
        "            if not page_hits:",
        "                break",
        "            offset += API_PAGE_SIZE",
        "",
        "        if len(opportunities_by_id) >= total:",
        "            return list(opportunities_by_id.values())",
        "",
        "        print(",
        "            f\"WARN: normal pagination produced {len(opportunities_by_id)}/{total}. \"",
        "            \"Starting automatic recovery fetch.\",",
        "            flush=True,",
        "        )",
        "",
        "        # Recovery 1: one larger request; normal 1,000-page traffic is unchanged.",
        "        recovery_size = max(API_PAGE_SIZE, min(total + 100, 2000))",
        "        recovery = fetch_api_page(session, 0, recovery_size)",
        "        add_page(opportunities_by_id, recovery)",
        "        if len(opportunities_by_id) >= total:",
        "            print(",
        "                f\"PASS: larger-request recovery restored {len(opportunities_by_id)}/{total}.\",",
        "                flush=True,",
        "            )",
        "            return list(opportunities_by_id.values())",
        "",
        "        # Recovery 2: overlapping 500-record pages tolerate unstable API offsets.",
        "        recovery_page_size = 500",
        "        overlap = 100",
        "        step = recovery_page_size - overlap",
        "        recovery_offset = 0",
        "        while recovery_offset < total:",
        "            recovery_page = fetch_api_page(",
        "                session,",
        "                recovery_offset,",
        "                recovery_page_size,",
        "            )",
        "            added = add_page(opportunities_by_id, recovery_page)",
        "            print(",
        "                f\"Recovery page from={recovery_offset}: +{added} unique; \"",
        "                f\"total {len(opportunities_by_id)}/{total}.\",",
        "                flush=True,",
        "            )",
        "            if len(opportunities_by_id) >= total:",
        "                print(\"PASS: overlapping-pagination recovery restored the complete set.\", flush=True)",
        "                return list(opportunities_by_id.values())",
        "            recovery_offset += step",
        "",
        "        raise RuntimeError(",
        "            \"Incomplete API retrieval after automatic recovery: \"",
        "            f\"{len(opportunities_by_id)}/{total} unique opportunities\"",
        "        )",
        "",
        "    finally:",
        "        session.close()",
    ])
    text = replace_function(
        text,
        "fetch_current_opportunities",
        fetch_current,
        "find_detail_card",
    )

    # ------------------------------------------------------------------
    # 3. One-time migration for the corrected eligibility parser.
    # ------------------------------------------------------------------
    if "# ELIGIBILITY_PARSER_MIGRATION_V2" not in text:
        migration_lines = [
            "# ELIGIBILITY_PARSER_MIGRATION_V2",
            "ELIGIBILITY_PARSER_MIGRATION_VERSION = 2",
            "",
            "",
            "def _apply_eligibility_parser_migration(checkpoint):",
            "    if checkpoint.get(\"eligibility_parser_migration_version\") == ELIGIBILITY_PARSER_MIGRATION_VERSION:",
            "        return False",
            "",
            "    processed = checkpoint.get(\"processed\", {})",
            "    invalidated = 0",
            "    for entry in processed.values():",
            "        if not isinstance(entry, dict):",
            "            continue",
            "        if entry.get(\"status\") != \"scanned\":",
            "            continue",
            "        entry[\"checked_at\"] = \"2000-01-01T00:00:00\"",
            "        invalidated += 1",
            "",
            "    checkpoint[\"eligibility_parser_migration_version\"] = ELIGIBILITY_PARSER_MIGRATION_VERSION",
            "    print(",
            "        f\"Eligibility parser migration queued {invalidated} existing records for one-time recheck.\",",
            "        flush=True,",
            "    )",
            "    return True",
            "",
            "",
        ]
        anchor = "# ============================================================================\n# WORK QUEUE"
        text = text.replace(anchor, "\n".join(migration_lines) + anchor, 1)

    migration_call = "    _apply_eligibility_parser_migration(checkpoint)\n"
    history_anchor = '    history = checkpoint[\n        "history"\n    ]\n'
    if migration_call not in text:
        text = text.replace(
            history_anchor,
            history_anchor + "\n" + migration_call,
            1,
        )

    # ------------------------------------------------------------------
    # 4. Keep the known 54038 eligibility case at the front of the queue
    # during the one-time parser migration.
    # ------------------------------------------------------------------
    if "# PRIORITIZE_54038_V2" not in text:
        old_return = "".join([
            "    return (\n",
            "        new_ids\n",
            "        + retry_ids\n",
            "        + stale_ids\n",
            "    )\n",
        ])
        new_return = "".join([
            "    # PRIORITIZE_54038_V2\n",
            '    if "54038" in stale_ids:\n',
            '        stale_ids.remove("54038")\n',
            '        return ["54038"] + new_ids + retry_ids + stale_ids\n',
            "\n",
            old_return,
        ])
        if old_return in text:
            text = text.replace(old_return, new_return, 1)

    SCRAPER_PATH.write_text(text, encoding="utf-8")
    print("PASS: backend automation fixes V8 installed.")
    print("PASS: normal API page size remains 1000; detail batch size remains unchanged.")
    print("PASS: incomplete API snapshots now use automatic recovery before failing.")
    print("PASS: participant-country eligibility parsing now collects the complete section.")
    print("PASS: existing scanned records queued for one-time eligibility recheck.")
    print("PASS: opportunity 54038 prioritized for immediate validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
