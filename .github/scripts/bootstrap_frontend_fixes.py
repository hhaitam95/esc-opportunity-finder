from pathlib import Path


APP_PATH = Path("web/app.js")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: expected exactly one {label} target, found {count}."
        )
    return text.replace(old, new, 1)


def main():
    if not APP_PATH.exists():
        raise SystemExit("ERROR: web/app.js does not exist.")

    text = APP_PATH.read_text(encoding="utf-8")

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

    text = replace_once(
        text,
        old,
        new,
        "handleSearchInput",
    )

    APP_PATH.write_text(text, encoding="utf-8")
    print("PASS: search input now updates state.filters.search.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
