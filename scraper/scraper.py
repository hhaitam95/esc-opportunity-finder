#!/usr/bin/env python3

import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pycountry
import requests
from bs4 import BeautifulSoup


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://youth.europa.eu"
API_URL = f"{BASE_URL}/api/rest/eyp/v1/search_en"

# Phase 1 public country.
DEFAULT_PARTICIPANT_COUNTRY = "MA"

# Data schemas.
CHECKPOINT_SCHEMA_VERSION = 4
OUTPUT_SCHEMA_VERSION = 4

# Active detail pages are rechecked at most once per day.
DETAIL_RECHECK_INTERVAL = 24 * 60 * 60

# API.
API_PAGE_SIZE = 1000
# Detail scanning.
BATCH_SIZE = 40
DETAIL_REQUEST_DELAY = 5.0
DETAIL_SCAN_COOLDOWN = 10.0

# HTTP.
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3
MAX_RATE_LIMIT_WAIT = 120

# Archive.
MAX_ARCHIVED_OPPORTUNITIES = 30

# NEW opportunities remain highlighted for 24 hours after first discovery.
NEW_OPPORTUNITY_DISPLAY_WINDOW = 24 * 60 * 60


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
EXPIRED_FILE = DATA_DIR / "expired.json"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# DATES
# ============================================================================

TODAY = datetime.now().replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

TODAY_API = TODAY.strftime(
    "%Y-%m-%dT00:00:00"
)


# ============================================================================
# HTTP
# ============================================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================================
# COUNTRY NORMALIZATION
# ============================================================================

COUNTRY_NAME_ALIASES = {
    "el": "GR",
    "greece": "GR",
    "uk": "GB",
    "united kingdom": "GB",
    "turkey": "TR",
    "türkiye": "TR",
    "czech republic": "CZ",
    "czechia": "CZ",
    "north macedonia": "MK",
    "the former yugoslav republic of macedonia": "MK",
    "macedonia": "MK",
    "republic of moldova": "MD",
    "moldova": "MD",
    "kosovo": "XK",
    "kosovo * un resolution": "XK",
    "bonaire, sint eustatius and saba": "BQ",
    "caribbean netherlands": "BQ",
    "curacao": "CW",
    "curaçao": "CW",
    "sint maarten": "SX",
    "sint maarten (dutch part)": "SX",
    "bolivia": "BO",
    "bolivia, plurinational state of": "BO",
    "brunei": "BN",
    "brunei darussalam": "BN",
    "iran": "IR",
    "iran, islamic republic of": "IR",
    "laos": "LA",
    "lao people's democratic republic": "LA",
    "russia": "RU",
    "russian federation": "RU",
    "syria": "SY",
    "syrian arab republic": "SY",
    "vietnam": "VN",
    "viet nam": "VN",
    "venezuela": "VE",
    "venezuela, bolivarian republic of": "VE",
    "palestine": "PS",
    "palestine, state of": "PS",
}


COUNTRY_DISPLAY_OVERRIDES = {
    "TR": "Türkiye",
    "CZ": "Czechia",
    "MK": "North Macedonia",
    "BA": "Bosnia and Herzegovina",
    "CW": "Curaçao",
    "SX": "Sint Maarten",
    "BQ": "Bonaire, Sint Eustatius and Saba",
    "XK": "Kosovo",
}


def normalize_country_text(value):
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    ).casefold()


def country_code_from_name(value):
    if not value:
        return None

    raw = re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )

    normalized = normalize_country_text(raw)

    if normalized in COUNTRY_NAME_ALIASES:
        return COUNTRY_NAME_ALIASES[normalized]

    if len(raw) == 2 and raw.isalpha():
        code = raw.upper()

        if code == "EL":
            return "GR"

        if code == "UK":
            return "GB"

        if code == "XK":
            return "XK"

        try:
            record = pycountry.countries.get(
                alpha_2=code
            )

            if record:
                return code
        except LookupError:
            pass

    cleaned = re.sub(
        r"\s*\*.*$",
        "",
        raw,
    ).strip()

    cleaned_normalized = normalize_country_text(
        cleaned
    )

    if cleaned_normalized in COUNTRY_NAME_ALIASES:
        return COUNTRY_NAME_ALIASES[
            cleaned_normalized
        ]

    for field in (
        "name",
        "official_name",
        "common_name",
    ):
        try:
            record = pycountry.countries.get(
                **{field: cleaned}
            )

            if record:
                return record.alpha_2
        except LookupError:
            pass

    try:
        matches = pycountry.countries.search_fuzzy(
            cleaned
        )

        if matches:
            return matches[0].alpha_2
    except LookupError:
        pass

    return None


def country_display_name(code):
    normalized = str(code).upper()

    if normalized in COUNTRY_DISPLAY_OVERRIDES:
        return COUNTRY_DISPLAY_OVERRIDES[
            normalized
        ]

    try:
        record = pycountry.countries.get(
            alpha_2=normalized
        )

        if record:
            return (
                getattr(
                    record,
                    "common_name",
                    None,
                )
                or record.name
            )
    except LookupError:
        pass

    return normalized


def normalize_eligible_country_codes(values):
    codes = set()
    unmapped = set()

    for raw in values or []:
        code = country_code_from_name(raw)

        if code:
            codes.add(code.upper())
        else:
            text = str(raw).strip()

            if text:
                unmapped.add(text)

    return (
        sorted(codes),
        sorted(unmapped),
    )


def normalize_result_country_schema(result):
    raw_values = result.get(
        "eligible_countries",
        [],
    )

    if isinstance(raw_values, list):
        codes, unmapped = (
            normalize_eligible_country_codes(
                raw_values
            )
        )
    else:
        codes = []
        unmapped = []

    result["eligible_countries"] = codes

    if unmapped:
        result[
            "eligible_countries_unmapped"
        ] = unmapped
    else:
        result.pop(
            "eligible_countries_unmapped",
            None,
        )

    # An empty list is valid only when the source explicitly gave
    # us an empty participant-country list.
    result["eligibility_known"] = bool(
        codes or raw_values == []
    )

    return result


# ============================================================================
# API PARAMETERS
# ============================================================================


def build_api_params(offset):
    return {
        "type": "Opportunity",
        "size": API_PAGE_SIZE,
        "from": offset,

        "filters[status]": "open",

        "filters[date_end][operator]": ">=",
        "filters[date_end][value]": TODAY_API,
        "filters[date_end][type]": "must",

        "filters[funding_programme][id][0]": 5,
        "filters[funding_programme][id][1]": 4,
        "filters[funding_programme][id][2]": 3,
        "filters[funding_programme][id][3]": 2,
        "filters[funding_programme][id][4]": 1,
        "filters[funding_programme][id][5]": 8,
        "filters[funding_programme][id][6]": 6,
        "filters[funding_programme][id][7]": 7,

        "filters[date_application_end][operator]": ">=",
        "filters[date_application_end][value]": TODAY_API,
        "filters[date_application_end][type]": "must",
        "filters[date_application_end][group]": "deadline",

        "filters[has_no_deadline][value]": "true",
        "filters[has_no_deadline][type]": "must",
        "filters[has_no_deadline][group]": "deadline",

        "fields[0]": "opid",
        "fields[1]": "title",
        "fields[2]": "town",
        "fields[3]": "country",
        "fields[4]": "date_start",
        "fields[5]": "date_end",
        "fields[6]": "date_application_end",
        "fields[7]": "has_no_deadline",
        "fields[8]": "duration",
        "fields[9]": "created",
        "fields[10]": "is_esc_related",

        "sort[created]": "desc",
    }


# ============================================================================
# GENERIC HELPERS
# ============================================================================


def now_iso():
    return datetime.now().isoformat()


def atomic_write_json(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def parse_iso_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return None


def parse_date_values(text):
    if not text:
        return []

    values = re.findall(
        r"\d{2}/\d{2}/\d{4}",
        text,
    )

    dates = []

    for value in values:
        try:
            dates.append(
                datetime.strptime(
                    value,
                    "%d/%m/%Y",
                )
            )
        except ValueError:
            pass

    return dates


# ============================================================================
# CHECKPOINT
# ============================================================================


def default_checkpoint():
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "processed": {},
        "history": {},
        "last_scan_at": None,
        "updated_at": None,
        "new_opportunity_first_seen_at": {},
    }


def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return default_checkpoint()

    try:
        data = json.loads(
            CHECKPOINT_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Checkpoint must be a JSON object."
            )

        data.setdefault(
            "processed",
            {},
        )

        data.setdefault(
            "history",
            {},
        )

        data.setdefault(
            "last_scan_at",
            None,
        )

        data.setdefault(
            "updated_at",
            None,
        )

        data.setdefault(
            "new_opportunity_first_seen_at",
            {},
        )

        for entry in data["processed"].values():
            if not isinstance(entry, dict):
                continue

            result = entry.get("result")

            if isinstance(result, dict):
                entry["result"] = (
                    normalize_result_country_schema(
                        result
                    )
                )

        data[
            "schema_version"
        ] = CHECKPOINT_SCHEMA_VERSION

        return data

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:

        print(
            f"Checkpoint could not be read safely: {exc}",
            flush=True,
        )

        print(
            "Starting with an empty checkpoint.",
            flush=True,
        )

        return default_checkpoint()


def save_checkpoint(checkpoint):
    checkpoint["schema_version"] = (
        CHECKPOINT_SCHEMA_VERSION
    )

    checkpoint["last_scan_at"] = now_iso()
    checkpoint["updated_at"] = now_iso()

    atomic_write_json(
        CHECKPOINT_FILE,
        checkpoint,
    )


# ============================================================================
# API FETCHING
# ============================================================================


def get_retry_after_seconds(response):
    value = response.headers.get(
        "Retry-After"
    )

    if value:
        try:
            seconds = int(float(value))

            return max(
                1,
                min(
                    seconds,
                    MAX_RATE_LIMIT_WAIT,
                ),
            )
        except ValueError:
            pass

    return 30


def fetch_api_page(session, offset):
    params = build_api_params(offset)

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            print(
                f"API request: from={offset}, "
                f"size={API_PAGE_SIZE}",
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
                wait = get_retry_after_seconds(
                    response
                )

                print(
                    f"API HTTP 429. "
                    f"Waiting {wait}s "
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
                        f"API HTTP "
                        f"{response.status_code}. "
                        f"Retrying in {wait}s...",
                        flush=True,
                    )

                    time.sleep(wait)
                    continue

                return None

            print(
                f"API error: HTTP "
                f"{response.status_code}",
                flush=True,
            )

            return None

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                wait = 2**attempt

                print(
                    f"API timeout. "
                    f"Retrying in {wait}s...",
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


def fetch_current_opportunities():
    # API_PAGINATION_DEDUP_V3
    print("=" * 70)
    print("FETCHING CURRENT ESC OPPORTUNITIES")
    print("=" * 70)

    session = requests.Session()
    opportunities_by_id = {}
    offset = 0
    total = None

    try:
        while True:
            data = fetch_api_page(session, offset)

            if data is None:
                raise RuntimeError(
                    "Could not retrieve the current opportunity list."
                )

            hits = data.get("hits", {})
            total_info = hits.get("total", {})

            if total is None:
                if isinstance(total_info, dict):
                    total = int(total_info.get("value", 0) or 0)
                else:
                    total = int(total_info or 0)

                print(
                    f"API reports {total} opportunities.",
                    flush=True,
                )

            page_hits = hits.get("hits", [])

            if not page_hits:
                break

            for hit in page_hits:
                source = hit.get("_source", {})
                opid = source.get("opid")

                if opid is None:
                    opid = hit.get("_id")

                if opid is None:
                    continue

                try:
                    source["opid"] = int(opid)
                except (TypeError, ValueError):
                    continue

                opportunities_by_id.setdefault(
                    str(source["opid"]),
                    source,
                )

            offset += API_PAGE_SIZE
            unique_count = len(opportunities_by_id)

            print(
                f"Retrieved {unique_count}/{total} unique opportunities "
                f"(raw page hits: {len(page_hits)})",
                flush=True,
            )

            if total is not None and unique_count >= total:
                break

    finally:
        session.close()

    opportunities = list(opportunities_by_id.values())

    if total is not None and len(opportunities) != total:
        raise RuntimeError(
            "Incomplete API retrieval: "
            f"{len(opportunities)}/{total} unique opportunities"
        )

    return opportunities

# ============================================================================
# DETAIL PAGE PARSING
# ============================================================================


def find_detail_card(soup):
    for card in soup.find_all(
        "div",
        class_="card-content",
    ):
        headings = [
            heading.get_text(
                " ",
                strip=True,
            ).lower()
            for heading in card.find_all(
                "h6"
            )
        ]

        if "activity dates" in headings:
            return card

    return None


def get_section(card, heading_name):
    if card is None:
        return None

    for heading in card.find_all(
        "h6"
    ):
        current = heading.get_text(
            " ",
            strip=True,
        )

        if (
            current.lower()
            != heading_name.lower()
        ):
            continue

        for sibling in heading.next_siblings:
            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "p"
            ):
                return sibling.get_text(
                    " ",
                    strip=True,
                )

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "h6"
            ):
                break

    return None


def get_topics(card):
    if card is None:
        return []

    for heading in card.find_all(
        "h6"
    ):
        if (
            heading.get_text(
                " ",
                strip=True,
            ).lower()
            != "activity topics"
        ):
            continue

        topics = []

        for sibling in heading.next_siblings:
            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "h6"
            ):
                break

            if (
                getattr(
                    sibling,
                    "name",
                    None,
                )
                == "p"
            ):
                text = sibling.get_text(
                    " ",
                    strip=True,
                )

                if text:
                    topics.append(text)

        return topics

    return []


def get_image_url(soup):
    logo = soup.find(
        "img",
        class_=lambda classes: (
            classes
            and "org-logo" in classes
        ),
    )

    if logo is None:
        return None

    src = logo.get("src")

    if not src:
        return None

    if src.startswith("/"):
        return f"{BASE_URL}{src}"

    return src


def parse_detail_page(
    opportunity,
    html,
):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    card = find_detail_card(
        soup
    )

    if card is None:
        return {
            "status": "parse_error",
            "result": None,
        }

    participant_text = get_section(
        card,
        "Looking for participants from",
    )

    if participant_text is None:
        return {
            "status": "parse_error",
            "result": None,
        }

    raw_countries = [
        item.strip()
        for item in participant_text.split(",")
        if item.strip()
    ]

    eligible_codes, unmapped = (
        normalize_eligible_country_codes(
            raw_countries
        )
    )

    activity_text = get_section(
        card,
        "Activity dates",
    )

    location = get_section(
        card,
        "Activity location",
    )

    activity_type = get_section(
        card,
        "Activity type",
    )

    deadline_text = get_section(
        card,
        "Deadline for applications",
    )

    project_code = get_section(
        card,
        "Project code",
    )

    activity_dates = parse_date_values(
        activity_text
    )

    start_date = (
        activity_dates[0]
        if len(activity_dates) >= 1
        else None
    )

    end_date = (
        activity_dates[1]
        if len(activity_dates) >= 2
        else None
    )

    deadline_dates = parse_date_values(
        deadline_text
    )

    deadline = (
        deadline_dates[0]
        if deadline_dates
        else None
    )

    if (
        deadline is not None
        and deadline < TODAY
    ):
        return {
            "status": "expired_deadline",
            "result": None,
        }

    if (
        end_date is not None
        and end_date < TODAY
    ):
        return {
            "status": "activity_finished",
            "result": None,
        }

    opid = int(
        opportunity["opid"]
    )

    result = {
        "id": opid,
        "opid": opid,
        "title": opportunity.get(
            "title",
            "",
        ),
        "location": (
            location
            or (
                f"{opportunity.get('town', '')}, "
                f"{opportunity.get('country', '')}"
            ).strip(", ")
        ),
        "country": opportunity.get(
            "country",
            "",
        ),
        "town": opportunity.get(
            "town",
            "",
        ),
        "activity_type": (
            activity_type or ""
        ),
        "start_date": (
            start_date.strftime(
                "%Y-%m-%d"
            )
            if start_date
            else None
        ),
        "end_date": (
            end_date.strftime(
                "%Y-%m-%d"
            )
            if end_date
            else None
        ),
        "deadline": (
            deadline.strftime(
                "%Y-%m-%d"
            )
            if deadline
            else None
        ),
        "eligible_countries": eligible_codes,
        "eligibility_known": True,
        "topics": get_topics(
            card
        ),
        "project_code": (
            project_code or ""
        ),
        "created": opportunity.get(
            "created",
            "",
        ),
        "image_url": get_image_url(
            soup
        ),
        "url": (
            f"{BASE_URL}/solidarity/"
            f"opportunity/{opid}_en"
        ),
    }

    if unmapped:
        result[
            "eligible_countries_unmapped"
        ] = unmapped

    return {
        "status": "scanned",
        "result": result,
    }


# ============================================================================
# DETAIL REQUEST
# ============================================================================


def fetch_detail_page(
    session,
    opportunity,
):
    opid = int(
        opportunity["opid"]
    )

    url = (
        f"{BASE_URL}/solidarity/"
        f"opportunity/{opid}_en"
    )

    print(
        f"  → Requesting {opid}",
        flush=True,
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            response = session.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:
                print(
                    f"  ← {opid}: HTTP 200",
                    flush=True,
                )

                return (
                    "200",
                    response.text,
                )

            if response.status_code == 404:
                print(
                    f"  ← {opid}: HTTP 404",
                    flush=True,
                )

                return (
                    "404",
                    None,
                )

            if response.status_code == 429:
                wait = get_retry_after_seconds(
                    response
                )

                print(
                    f"  ← {opid}: HTTP 429",
                    flush=True,
                )

                if attempt >= MAX_RETRIES:
                    return (
                        "429",
                        None,
                    )

                print(
                    f"  Waiting {wait}s...",
                    flush=True,
                )

                time.sleep(wait)
                continue

            if response.status_code >= 500:
                print(
                    f"  ← {opid}: "
                    f"HTTP {response.status_code}",
                    flush=True,
                )

                if attempt < MAX_RETRIES:
                    wait = 2**attempt
                    time.sleep(wait)
                    continue

                return (
                    f"HTTP_{response.status_code}",
                    None,
                )

            print(
                f"  ← {opid}: "
                f"HTTP {response.status_code}",
                flush=True,
            )

            return (
                f"HTTP_{response.status_code}",
                None,
            )

        except requests.Timeout:
            print(
                f"  ← {opid}: TIMEOUT",
                flush=True,
            )

            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue

            return (
                "TIMEOUT",
                None,
            )

        except requests.RequestException as exc:
            print(
                f"  ← {opid}: REQUEST ERROR: {exc}",
                flush=True,
            )

            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue

            return (
                "ERROR",
                None,
            )

    return (
        "FAILED",
        None,
    )


# ============================================================================
# ARCHIVING
# ============================================================================


def archive_match(
    history,
    opid,
    result,
    reason,
):
    existing = history.get(
        opid,
        {},
    )

    history[opid] = {
        "first_seen": (
            existing.get(
                "first_seen"
            )
            or result.get(
                "created"
            )
        ),
        "last_seen": now_iso(),
        "result": result,
        "reason": reason,
    }


def archive_disappeared_matches(
    processed,
    history,
    current_ids,
):
    count = 0

    for opid, entry in processed.items():
        if not isinstance(
            entry,
            dict,
        ):
            continue

        if entry.get(
            "status"
        ) != "scanned":
            continue

        result = entry.get(
            "result"
        )

        if not isinstance(
            result,
            dict,
        ):
            continue

        if opid in current_ids:
            continue

        archive_match(
            history,
            opid,
            result,
            (
                "No longer present in "
                "the active opportunity list."
            ),
        )

        count += 1

    return count


def archive_previous_result(
    history,
    opid,
    previous_entry,
    reason,
):
    if not previous_entry:
        return False

    if previous_entry.get(
        "status"
    ) != "scanned":
        return False

    result = previous_entry.get(
        "result"
    )

    if not result:
        return False

    archive_match(
        history,
        opid,
        result,
        reason,
    )

    return True


# ============================================================================
# WORK QUEUE
# ============================================================================


def entry_is_stale(entry):
    if not entry:
        return True

    checked_at = parse_iso_datetime(
        entry.get(
            "checked_at"
        )
    )

    if checked_at is None:
        return True

    try:
        if checked_at.tzinfo:
            current = datetime.now(
                checked_at.tzinfo
            )
        else:
            current = datetime.now()

        return (
            current - checked_at
        ).total_seconds() >= (
            DETAIL_RECHECK_INTERVAL
        )
    except TypeError:
        return True


def build_work_queue(
    current_opportunities,
    checkpoint,
):
    processed = checkpoint.get(
        "processed",
        {},
    )

    new_ids = []
    retry_ids = []
    stale_ids = []

    ordered_ids = [
        str(
            opportunity["opid"]
        )
        for opportunity in current_opportunities
    ]

    for opid in ordered_ids:
        entry = processed.get(
            opid
        )

        if entry is None:
            new_ids.append(opid)
            continue

        status = entry.get(
            "status"
        )

        if status in {
            "error",
            "parse_error",
            "timeout",
        }:
            retry_ids.append(opid)
            continue

        if status == "not_found":
            retry_ids.append(opid)
            continue

        if status in {
            "scanned",
            "expired_deadline",
            "activity_finished",
        }:
            if entry_is_stale(entry):
                stale_ids.append(opid)

            continue

        retry_ids.append(opid)

    return (
        new_ids
        + retry_ids
        + stale_ids
    )


# ============================================================================
# CURRENT CACHE
# ============================================================================


def get_active_new_opportunity_ids(checkpoint, current_ids):
    """Return newly discovered IDs that are still within the 24-hour window."""
    first_seen = checkpoint.get("new_opportunity_first_seen_at", {})
    now = datetime.now()
    active = []
    stale = []

    for raw_id, raw_timestamp in first_seen.items():
        opid = str(raw_id)
        if opid not in current_ids:
            stale.append(opid)
            continue

        seen_at = parse_iso_datetime(raw_timestamp)
        if seen_at is None:
            stale.append(opid)
            continue

        if (now - seen_at.replace(tzinfo=None)).total_seconds() <= NEW_OPPORTUNITY_DISPLAY_WINDOW:
            active.append(opid)
        else:
            stale.append(opid)

    for opid in stale:
        first_seen.pop(opid, None)

    return sorted(set(active))


def get_current_results(
    checkpoint,
    current_ids,
):
    processed = checkpoint.get(
        "processed",
        {},
    )

    results = []

    for opid in current_ids:
        entry = processed.get(
            opid
        )

        if not isinstance(
            entry,
            dict,
        ):
            continue

        if entry.get(
            "status"
        ) != "scanned":
            continue

        result = entry.get(
            "result"
        )

        if not isinstance(
            result,
            dict,
        ):
            continue

        results.append(
            normalize_result_country_schema(
                dict(result)
            )
        )

    results.sort(
        key=lambda item: (
            item.get(
                "deadline"
            )
            or "9999-12-31",
            item.get(
                "title",
                "",
            ).casefold(),
        )
    )

    return results


def build_participant_country_registry(
    opportunities,
):
    codes = set()

    for opportunity in opportunities:
        for code in opportunity.get(
            "eligible_countries",
            [],
        ):
            if (
                isinstance(code, str)
                and len(code) == 2
            ):
                codes.add(
                    code.upper()
                )

    return [
        {
            "code": code,
            "name": country_display_name(
                code
            ),
        }
        for code in sorted(codes)
    ]


# ============================================================================
# PUBLIC OUTPUT
# ============================================================================


def save_public_output(
    opportunities,
    checkpoint,
    current_ids,
    generated_at=None,
    new_opportunity_ids=None,
):
    registry = build_participant_country_registry(
        opportunities
    )

    scan_complete = bool(
        current_ids
    ) and all(
        (
            checkpoint.get(
                "processed",
                {},
            )
            .get(opid, {})
            .get("status")
            == "scanned"
        )
        for opid in current_ids
    )

    # Phase 1 intentionally exposes the full scanned cache.
    # The frontend can filter by eligible_countries.
    #
    # This means the same backend can later support:
    #
    #   MA
    #   FR
    #   DE
    #   etc.
    #
    # without another scraper architecture rewrite.

    output = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        # PHASE3_UPDATE_CYCLE_METADATA
        "generated_at": generated_at or now_iso(),
        "new_opportunity_ids": sorted(
            {
                str(opid)
                for opid in (new_opportunity_ids or [])
            }
        ),
        "source_date": TODAY.strftime(
            "%Y-%m-%d"
        ),
        "default_participant_country": (
            DEFAULT_PARTICIPANT_COUNTRY
        ),
        "scan_complete": scan_complete,
        "participant_countries": registry,
        "count": len(opportunities),
        "opportunities": opportunities,
    }

    atomic_write_json(
        OPPORTUNITIES_FILE,
        output,
    )


    return output


def save_expired_output(history):
    archived = []

    for entry in history.values():
        if not isinstance(
            entry,
            dict,
        ):
            continue

        result = entry.get(
            "result"
        )

        if not isinstance(
            result,
            dict,
        ):
            continue

        archived.append(
            {
                **result,
                "last_seen": entry.get(
                    "last_seen"
                ),
                "reason": entry.get(
                    "reason"
                ),
            }
        )

    archived.sort(
        key=lambda item: (
            item.get(
                "last_seen",
                "",
            )
        ),
        reverse=True,
    )

    archived = archived[
        :MAX_ARCHIVED_OPPORTUNITIES
    ]

    output = {
        "generated_at": now_iso(),
        "count": len(archived),
        "opportunities": archived,
    }

    atomic_write_json(
        EXPIRED_FILE,
        output,
    )


# ============================================================================
# MAIN
# ============================================================================


def main():
    # PHASE3_UPDATE_CYCLE_METADATA
    cycle_generated_at = now_iso()
    newly_scanned_ids = set()
    print("=" * 70)
    print(
        "EUROPEAN SOLIDARITY CORPS — "
        "PHASE 1 BACKEND CACHE"
    )
    print("=" * 70)

    print(
        f"Date: {TODAY.strftime('%d/%m/%Y')}",
        flush=True,
    )

    print(
        f"Default participant country: "
        f"{DEFAULT_PARTICIPANT_COUNTRY}",
        flush=True,
    )

    print(
        f"Batch size: {BATCH_SIZE}",
        flush=True,
    )

    print(
        f"Detail request delay: "
        f"{DETAIL_REQUEST_DELAY}s",
        flush=True,
    )

    # ------------------------------------------------------------------
    # 1. Retrieve the authoritative active API snapshot.
    # ------------------------------------------------------------------

    current_opportunities = (
        fetch_current_opportunities()
    )

    if not current_opportunities:
        raise RuntimeError(
            "No current opportunities were retrieved."
        )

    current_ids = {
        str(
            opportunity["opid"]
        )
        for opportunity in current_opportunities
    }

    opportunities_by_id = {
        str(
            opportunity["opid"]
        ): opportunity
        for opportunity in current_opportunities
    }

    # ------------------------------------------------------------------
    # 2. Load persistent checkpoint.
    # ------------------------------------------------------------------

    checkpoint = load_checkpoint()

    processed = checkpoint[
        "processed"
    ]

    history = checkpoint[
        "history"
    ]

    # ------------------------------------------------------------------
    # 3. Archive opportunities that disappeared from the API.
    # ------------------------------------------------------------------

    disappeared = (
        archive_disappeared_matches(
            processed,
            history,
            current_ids,
        )
    )

    if disappeared:
        print(
            f"Archived {disappeared} disappeared "
            "opportunity/opportunities.",
            flush=True,
        )

        save_checkpoint(
            checkpoint
        )

    # ------------------------------------------------------------------
    # 4. Build incremental work queue.
    # ------------------------------------------------------------------

    queue = build_work_queue(
        current_opportunities,
        checkpoint,
    )

    batch = queue[
        :BATCH_SIZE
    ]

    already_processed = sum(
        1
        for opid in current_ids
        if opid in processed
    )

    print()
    print("=" * 70)
    print("SCAN PLAN")
    print("=" * 70)

    print(
        f"Current API opportunities: "
        f"{len(current_opportunities)}"
    )

    print(
        f"Already known: "
        f"{already_processed}"
    )

    print(
        f"Work remaining: "
        f"{len(queue)}"
    )

    print(
        f"This invocation: "
        f"{len(batch)}"
    )

    print("=" * 70)

    # ------------------------------------------------------------------
    # 5. No detail work required.
    # ------------------------------------------------------------------

    if not batch:
        opportunities = get_current_results(
            checkpoint,
            current_ids,
        )

        active_new_ids = get_active_new_opportunity_ids(
            checkpoint,
            current_ids,
        )

        save_public_output(
            opportunities,
            checkpoint,
            current_ids,
            generated_at=cycle_generated_at,
            new_opportunity_ids=active_new_ids,
        )

        save_expired_output(
            history
        )

        save_checkpoint(
            checkpoint
        )

        print()
        print(
            "NO DETAIL SCANNING REQUIRED",
            flush=True,
        )

        print(
            f"Published scanned opportunities: "
            f"{len(opportunities)}",
            flush=True,
        )

        return 0

    # ------------------------------------------------------------------
    # 6. Cooldown before detail scanning.
    # ------------------------------------------------------------------

    print(
        f"\nWaiting {DETAIL_SCAN_COOLDOWN}s "
        "before detail scanning...",
        flush=True,
    )

    time.sleep(
        DETAIL_SCAN_COOLDOWN
    )

    # ------------------------------------------------------------------
    # 7. Process one incremental batch.
    # ------------------------------------------------------------------

    session = requests.Session()

    processed_this_batch = 0
    scanned_this_batch = 0
    archived_this_batch = 0
    rate_limited = False

    try:
        for index, opid in enumerate(
            batch,
            start=1,
        ):
            opportunity = (
                opportunities_by_id[
                    opid
                ]
            )

            previous_entry = (
                processed.get(
                    opid
                )
            )

            print(
                "\n" + "=" * 60,
                flush=True,
            )

            print(
                f"[{index}/{len(batch)}] "
                f"Checking ID {opid}",
                flush=True,
            )

            status, html = (
                fetch_detail_page(
                    session,
                    opportunity,
                )
            )

            # ------------------------------------------------------
            # Rate limit: do not mark the opportunity as processed.
            # ------------------------------------------------------

            if status == "429":
                rate_limited = True

                print(
                    "\n" + "!" * 60,
                    flush=True,
                )

                print(
                    "RATE LIMIT DETECTED",
                    flush=True,
                )

                print(
                    "Stopping this invocation safely.",
                    flush=True,
                )

                break

            processed_this_batch += 1

            checked_at = now_iso()

            # ------------------------------------------------------
            # 404: keep the last known result but retry later.
            # ------------------------------------------------------

            if status == "404":
                processed[opid] = {
                    "status": "not_found",
                    "result": (
                        previous_entry.get(
                            "result"
                        )
                        if previous_entry
                        else None
                    ),
                    "checked_at": checked_at,
                }

            # ------------------------------------------------------
            # Other HTTP/network failures.
            # ------------------------------------------------------

            elif status != "200":
                processed[opid] = {
                    "status": "error",
                    "http_status": status,
                    "result": (
                        previous_entry.get(
                            "result"
                        )
                        if previous_entry
                        else None
                    ),
                    "checked_at": checked_at,
                }

            # ------------------------------------------------------
            # Successful detail-page retrieval.
            # ------------------------------------------------------

            else:
                parsed = parse_detail_page(
                    opportunity,
                    html,
                )

                new_status = parsed.get(
                    "status"
                )

                # Archive a previously active result if the
                # opportunity has genuinely expired.
                if (
                    previous_entry
                    and previous_entry.get(
                        "status"
                    )
                    == "scanned"
                    and previous_entry.get(
                        "result"
                    )
                    and new_status
                    in {
                        "expired_deadline",
                        "activity_finished",
                    }
                ):
                    reason = (
                        "Application deadline has expired."
                        if new_status
                        == "expired_deadline"
                        else
                        "Activity has finished."
                    )

                    if archive_previous_result(
                        history,
                        opid,
                        previous_entry,
                        reason,
                    ):
                        archived_this_batch += 1

                if new_status == "scanned":
                    # PHASE3_UPDATE_CYCLE_METADATA
                    if previous_entry is None:
                        new_id = str(opid)
                        newly_scanned_ids.add(new_id)
                        checkpoint.setdefault(
                            "new_opportunity_first_seen_at",
                            {},
                        )[new_id] = checked_at
                    history.pop(
                        opid,
                        None,
                    )

                    scanned_this_batch += 1

                    result = parsed.get(
                        "result"
                    )

                    if result:
                        print(
                            "\n✅ SCANNED",
                            flush=True,
                        )

                        print(
                            f"{result['id']} — "
                            f"{result['title']}",
                            flush=True,
                        )

                elif new_status == "parse_error":
                    # Never destroy a valid previous result merely
                    # because the website HTML changed temporarily.
                    if (
                        previous_entry
                        and previous_entry.get(
                            "result"
                        )
                    ):
                        parsed[
                            "result"
                        ] = previous_entry[
                            "result"
                        ]

                processed[opid] = {
                    **parsed,
                    "checked_at": checked_at,
                }

            checkpoint[
                "processed"
            ] = processed

            checkpoint[
                "history"
            ] = history

            save_checkpoint(
                checkpoint
            )

            print(
                f"Checkpoint saved after ID {opid}.",
                flush=True,
            )

            if index < len(batch):
                time.sleep(
                    DETAIL_REQUEST_DELAY
                )

    finally:
        session.close()

    # ------------------------------------------------------------------
    # 8. Publish current cache.
    # ------------------------------------------------------------------

    opportunities = get_current_results(
        checkpoint,
        current_ids,
    )

    active_new_ids = get_active_new_opportunity_ids(
        checkpoint,
        current_ids,
    )

    output = save_public_output(
        opportunities,
        checkpoint,
        current_ids,
        generated_at=cycle_generated_at,
        new_opportunity_ids=active_new_ids,
    )

    save_expired_output(
        history
    )

    save_checkpoint(
        checkpoint
    )

    # ------------------------------------------------------------------
    # 9. Determine remaining work.
    # ------------------------------------------------------------------

    remaining_queue = build_work_queue(
        current_opportunities,
        checkpoint,
    )

    print()
    print("=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    print(
        f"Processed this invocation: "
        f"{processed_this_batch}"
    )

    print(
        f"Successfully scanned: "
        f"{scanned_this_batch}"
    )

    print(
        f"Archived this invocation: "
        f"{archived_this_batch}"
    )

    print(
        f"Published scanned opportunities: "
        f"{len(opportunities)}"
    )

    print(
        f"Participant countries discovered: "
        f"{len(output['participant_countries'])}"
    )

    print(
        f"Remaining detail work: "
        f"{len(remaining_queue)}"
    )

    print("=" * 70)

    if rate_limited:
        print(
            "⚠️ Rate limited. "
            "Checkpoint and cache were saved.",
            flush=True,
        )

        return 2

    if remaining_queue:
        print(
            "More opportunities remain. "
            "The next hourly run will continue "
            "from the checkpoint.",
            flush=True,
        )
    else:
        print(
            "🎉 Current active opportunity set "
            "has been fully scanned.",
            flush=True,
        )

    return 0


# ============================================================================
# ENTRY POINT
# ============================================================================


if __name__ == "__main__":
    try:
        sys.exit(
            main()
        )

    except KeyboardInterrupt:
        print(
            "\nInterrupted by user.",
            flush=True,
        )

        print(
            "Existing checkpoint progress "
            "has been preserved.",
            flush=True,
        )

        sys.exit(2)

    except Exception as exc:
        print(
            f"\nFATAL ERROR: {exc}",
            file=sys.stderr,
            flush=True,
        )

        sys.exit(1)
