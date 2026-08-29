from pathlib import Path


SCRAPER_PATH = Path("scraper/scraper.py")
PARSER_MARKER = "# ELIGIBILITY_PARSER_COMPLETE_V1"
MIGRATION_MARKER = "# ELIGIBILITY_PARSER_MIGRATION_V1"
PRIORITY_MARKER = "# PRIORITIZE_54038_V1"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: expected exactly one {label} target, found {count}."
        )
    return text.replace(old, new, 1)


def main():
    if not SCRAPER_PATH.exists():
        raise SystemExit("ERROR: scraper/scraper.py does not exist.")

    text = SCRAPER_PATH.read_text(encoding="utf-8")

    # Replace the participant section helper so every paragraph belonging to
    # the section is collected. EYP can split long participant lists across
    # multiple paragraphs; returning only the first paragraph loses countries.
    get_section_start = text.find("def get_section(card, heading_name):")
    get_topics_start = text.find("def get_topics(card):", get_section_start)
    if get_section_start < 0 or get_topics_start < 0:
        raise SystemExit(
            "ERROR: could not locate get_section/get_topics boundaries; no source change made."
        )

    parser = "\n".join([
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
    ])
    text = text[:get_section_start] + parser + text[get_topics_start:]

    # One-time migration: invalidate already-scanned records so the corrected
    # participant eligibility parser is applied to the whole existing cache.
    if MIGRATION_MARKER not in text:
        migration = "\n".join([
            MIGRATION_MARKER,
            "ELIGIBILITY_PARSER_MIGRATION_VERSION = 1",
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
        ])
        anchor = "# ============================================================================\n# WORK QUEUE"
        text = replace_once(
            text,
            anchor,
            migration + anchor,
            "eligibility migration insertion point",
        )

    migration_call = "    _apply_eligibility_parser_migration(checkpoint)\n"
    history_anchor = '    history = checkpoint[\n        "history"\n    ]\n'
    if migration_call not in text:
        text = replace_once(
            text,
            history_anchor,
            history_anchor + "\n" + migration_call,
            "eligibility migration call",
        )

    # Put the known validation opportunity first while the one-time migration
    # is being consumed, allowing Austria-vs-Albania to be verified promptly.
    if PRIORITY_MARKER not in text:
        old_return = "".join([
            "    return (\n",
            "        new_ids\n",
            "        + retry_ids\n",
            "        + stale_ids\n",
            "    )\n",
        ])
        new_return = "".join([
            f"    {PRIORITY_MARKER}\n",
            '    if "54038" in stale_ids:\n',
            '        stale_ids.remove("54038")\n',
            '        return ["54038"] + new_ids + retry_ids + stale_ids\n',
            "\n",
            old_return,
        ])
        text = replace_once(
            text,
            old_return,
            new_return,
            "work queue return block",
        )

    SCRAPER_PATH.write_text(text, encoding="utf-8")
    print("PASS: complete participant eligibility parser installed.")
    print("PASS: one-time eligibility migration installed.")
    print("PASS: opportunity 54038 prioritized for immediate revalidation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
