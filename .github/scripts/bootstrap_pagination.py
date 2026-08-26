from pathlib import Path


SCRAPER_PATH = Path("scraper/scraper.py")

MARKER = "# API_PAGINATION_DEDUP_V3"
FUNCTION_START = "def fetch_current_opportunities():"
FUNCTION_END = "# ============================================================================\n# DETAIL PAGE PARSING"

NEW_FUNCTION_LINES = [
    "def fetch_current_opportunities():",
    "    # API_PAGINATION_DEDUP_V3",
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
    "",
    "            if data is None:",
    "                raise RuntimeError(",
    "                    \"Could not retrieve the current opportunity list.\"",
    "                )",
    "",
    "            hits = data.get(\"hits\", {})",
    "            total_info = hits.get(\"total\", {})",
    "",
    "            if total is None:",
    "                if isinstance(total_info, dict):",
    "                    total = int(total_info.get(\"value\", 0) or 0)",
    "                else:",
    "                    total = int(total_info or 0)",
    "",
    "                print(",
    "                    f\"API reports {total} opportunities.\",",
    "                    flush=True,",
    "                )",
    "",
    "            page_hits = hits.get(\"hits\", [])",
    "",
    "            if not page_hits:",
    "                break",
    "",
    "            for hit in page_hits:",
    "                source = hit.get(\"_source\", {})",
    "                opid = source.get(\"opid\")",
    "",
    "                if opid is None:",
    "                    opid = hit.get(\"_id\")",
    "",
    "                if opid is None:",
    "                    continue",
    "",
    "                try:",
    "                    source[\"opid\"] = int(opid)",
    "                except (TypeError, ValueError):",
    "                    continue",
    "",
    "                opportunities_by_id.setdefault(",
    "                    str(source[\"opid\"]),",
    "                    source,",
    "                )",
    "",
    "            offset += API_PAGE_SIZE",
    "            unique_count = len(opportunities_by_id)",
    "",
    "            print(",
    "                f\"Retrieved {unique_count}/{total} unique opportunities \"",
    "                f\"(raw page hits: {len(page_hits)})\",",
    "                flush=True,",
    "            )",
    "",
    "            if total is not None and unique_count >= total:",
    "                break",
    "",
    "    finally:",
    "        session.close()",
    "",
    "    opportunities = list(opportunities_by_id.values())",
    "",
    "    if total is not None and len(opportunities) != total:",
    "        raise RuntimeError(",
    "            \"Incomplete API retrieval: \"",
    "            f\"{len(opportunities)}/{total} unique opportunities\"",
    "        )",
    "",
    "    return opportunities",
    "",
    "",
]


def main():
    if not SCRAPER_PATH.exists():
        raise SystemExit("ERROR: scraper/scraper.py does not exist.")

    text = SCRAPER_PATH.read_text(encoding="utf-8")

    if MARKER not in text:
        start = text.find(FUNCTION_START)
        end = text.find(FUNCTION_END, start)

        if start < 0 or end < 0:
            raise SystemExit(
                "ERROR: could not locate fetch_current_opportunities boundaries; no source change made."
            )

        new_function = "\n".join(NEW_FUNCTION_LINES)
        text = text[:start] + new_function + text[end:]

    old_page_size = "API_PAGE_SIZE = 100"
    new_page_size = "API_PAGE_SIZE = 1000"

    if old_page_size in text:
        text = text.replace(
            old_page_size,
            new_page_size,
            1,
        )

    if MARKER not in text:
        raise SystemExit(
            "ERROR: pagination marker was not written; no source change made."
        )

    SCRAPER_PATH.write_text(
        text,
        encoding="utf-8",
    )

    print("PASS: permanent API pagination/deduplication fix applied.")
    print("PASS: API page size set to 1000; detail batch size unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
