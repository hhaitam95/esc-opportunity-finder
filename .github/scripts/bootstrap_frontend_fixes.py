from pathlib import Path


APP_PATH = Path("web/app.js")


SEARCH_FIXED = '  state.filters.search = dom.searchInput?.value || "";\n'


def main():
    if not APP_PATH.exists():
        raise SystemExit("ERROR: web/app.js does not exist.")

    text = APP_PATH.read_text(encoding="utf-8")

    if SEARCH_FIXED in text:
        print("PASS: search input state fix already present.")
        return 0

    old = '''function handleSearchInput() {
  if (searchRenderTimer) window.clearTimeout(searchRenderTimer);
  searchRenderTimer = window.setTimeout(renderAll, 120);
}
'''

    new = '''function handleSearchInput() {
  state.filters.search = dom.searchInput?.value || "";
  if (searchRenderTimer) window.clearTimeout(searchRenderTimer);
  searchRenderTimer = window.setTimeout(renderAll, 120);
}
'''

    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: expected exactly one handleSearchInput target, found {count}."
        )

    text = text.replace(old, new, 1)
    APP_PATH.write_text(text, encoding="utf-8")
    print("PASS: search input now updates state.filters.search.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
