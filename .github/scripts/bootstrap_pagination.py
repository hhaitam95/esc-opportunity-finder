from pathlib import Path
import re


SCRAPER_PATH = Path("scraper/scraper.py")

MARKER = "# API_PAGINATION_DEDUP_V4"
FUNCTION_START = "def fetch_current_opportunities():"
FUNCTION_END = "# ============================================================================\n# DETAIL PAGE PARSING"

NEW_FUNCTION_LINES = [
    "def fetch_current_opportunities():",
    "    # API_PAGINATION_DEDUP_V4",
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
    "                raise RuntimeError(\"Could not retrieve the current opportunity list.\")",
    "",
    "            hits = data.get(\"hits\", {})",
    "            total_info = hits.get(\"total\", {})",
    "",
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
    "                except (TypeError, ValueError):",
    "                    continue",
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

    if MARKER not in text:
        raise SystemExit(
            "ERROR: pagination marker was not written; no source change made."
        )

    SCRAPER_PATH.write_text(text, encoding="utf-8")
    print("PASS: stable API pagination/deduplication fix applied.")
    print("PASS: API page size remains 1000; detail batch size unchanged.")
    print("PASS: API ordering now uses stable opid ordering to prevent page shifts during updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
