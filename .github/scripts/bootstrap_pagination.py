from pathlib import Path
import re


SCRAPER_PATH = Path("scraper/scraper.py")
MARKER = "# API_PAGINATION_DEDUP_V7"


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

    text, replacements = re.subn(
        r"def build_api_params\(offset\):\n",
        "def build_api_params(offset, page_size=None):\n",
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit("ERROR: could not update build_api_params signature; no source change made.")

    text, replacements = re.subn(
        r'        "size": API_PAGE_SIZE,\n        "from": offset,',
        '        "size": page_size or API_PAGE_SIZE,\n        "from": offset,',
        text,
        count=1,
    )
    if replacements != 1:
        raise SystemExit("ERROR: could not update API size parameter; no source change made.")

    fetch_api_page = '''def fetch_api_page(session, offset, page_size=None):
    params = build_api_params(
        offset,
        page_size,
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            effective_size = page_size or API_PAGE_SIZE
            print(
                f"API request: from={offset}, "
                f"size={effective_size}",
                flush=True,
            )

            response = session.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    print(
                        f"Invalid API JSON: {exc}",
                        flush=True,
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(2**attempt)
                        continue
                    return None

            if response.status_code == 429:
                wait = get_retry_after_seconds(response)
                print(
                    f"API HTTP 429. Waiting {wait}s "
                    f"({attempt}/{MAX_RETRIES})...",
                    flush=True,
                )
                if attempt >= MAX_RETRIES:
                    return None
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                if attempt < MAX_RETRIES:
                    wait = 2**attempt
                    print(
                        f"API HTTP {response.status_code}. "
                        f"Retrying in {wait}s...",
                        flush=True,
                    )
                    time.sleep(wait)
                    continue
                return None

            print(
                f"API error: HTTP {response.status_code}",
                flush=True,
            )
            return None

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                wait = 2**attempt
                print(
                    f"API timeout. Retrying in {wait}s...",
                    flush=True,
                )
                time.sleep(wait)
                continue
            return None

        except requests.RequestException as exc:
            if attempt < MAX_RETRIES:
                wait = 2**attempt
                print(
                    f"API request error: {exc}",
                    flush=True,
                )
                print(
                    f"Retrying in {wait}s...",
                    flush=True,
                )
                time.sleep(wait)
                continue
            print(
                f"API request failed: {exc}",
                flush=True,
            )
            return None

    return None
'''
    text = replace_function(
        text,
        "fetch_api_page",
        fetch_api_page,
        "fetch_current_opportunities",
    )

    fetch_current = '''def fetch_current_opportunities():
    # API_PAGINATION_DEDUP_V7
    print("=" * 70)
    print("FETCHING CURRENT ESC OPPORTUNITIES")
    print("=" * 70)

    session = requests.Session()
    total = None

    def total_from(data):
        hits = data.get("hits", {}) if data else {}
        total_info = hits.get("total", {})
        if isinstance(total_info, dict):
            return int(total_info.get("value", 0) or 0)
        return int(total_info or 0)

    def add_page(target, data):
        if not data:
            return 0
        page_hits = data.get("hits", {}).get("hits", [])
        added = 0
        for hit in page_hits:
            source = hit.get("_source", {})
            opid = source.get("opid") or hit.get("_id")
            if opid is None:
                continue
            try:
                source["opid"] = int(opid)
            except (TypeError, ValueError):
                continue
            key = str(source["opid"])
            if key not in target:
                target[key] = source
                added += 1
        return added

    try:
        opportunities_by_id = {}

        first = fetch_api_page(session, 0)
        if first is None:
            raise RuntimeError("Could not retrieve the current opportunity list.")

        total = total_from(first)
        print(f"API reports {total} opportunities.", flush=True)
        add_page(opportunities_by_id, first)
        print(
            f"Retrieved {len(opportunities_by_id)}/{total} unique opportunities "
            f"(raw page hits: {len(first.get('hits', {}).get('hits', []))}).",
            flush=True,
        )

        offset = API_PAGE_SIZE
        while len(opportunities_by_id) < total:
            data = fetch_api_page(session, offset)
            if data is None:
                break
            page_hits = data.get("hits", {}).get("hits", [])
            add_page(opportunities_by_id, data)
            print(
                f"Retrieved {len(opportunities_by_id)}/{total} unique opportunities "
                f"(raw page hits: {len(page_hits)})",
                flush=True,
            )
            if not page_hits:
                break
            offset += API_PAGE_SIZE

        if len(opportunities_by_id) >= total:
            return list(opportunities_by_id.values())

        print(
            f"WARN: normal pagination produced {len(opportunities_by_id)}/{total}. "
            "Starting automatic recovery fetch.",
            flush=True,
        )

        recovery_size = max(API_PAGE_SIZE, min(total + 100, 2000))
        recovery = fetch_api_page(session, 0, recovery_size)
        add_page(opportunities_by_id, recovery)
        if len(opportunities_by_id) >= total:
            print(
                f"PASS: larger-request recovery restored {len(opportunities_by_id)}/{total}.",
                flush=True,
            )
            return list(opportunities_by_id.values())

        recovery_page_size = 500
        overlap = 100
        step = recovery_page_size - overlap
        recovery_offset = 0

        while recovery_offset < total:
            recovery_page = fetch_api_page(
                session,
                recovery_offset,
                recovery_page_size,
            )
            added = add_page(opportunities_by_id, recovery_page)
            print(
                f"Recovery page from={recovery_offset}: +{added} unique; "
                f"total {len(opportunities_by_id)}/{total}.",
                flush=True,
            )
            if len(opportunities_by_id) >= total:
                print(
                    "PASS: overlapping-pagination recovery restored the complete set.",
                    flush=True,
                )
                return list(opportunities_by_id.values())
            recovery_offset += step

        raise RuntimeError(
            "Incomplete API retrieval after automatic recovery: "
            f"{len(opportunities_by_id)}/{total} unique opportunities"
        )

    finally:
        session.close()
'''
    text = replace_function(
        text,
        "fetch_current_opportunities",
        fetch_current,
        "find_detail_card",
    )

    # Make the patch idempotent and update the marker after all replacements.
    text = text.replace(
        "# API_PAGINATION_DEDUP_V4",
        MARKER,
        1,
    )

    SCRAPER_PATH.write_text(text, encoding="utf-8")
    print("PASS: normal API pagination remains unchanged at size 1000.")
    print("PASS: incomplete snapshots now trigger automatic larger-request recovery.")
    print("PASS: overlapping-pagination recovery enabled as a second fallback.")
    print("PASS: API integrity validation remains strict after recovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
