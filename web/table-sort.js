(() => {
  const sortableColumns = new Set([0, 1, 2, 3, 4]);
  const state = new WeakMap();

  function installStyles() {
    if (document.getElementById("table-sort-styles")) return;
    const style = document.createElement("style");
    style.id = "table-sort-styles";
    style.textContent = `
      .opportunity-table th.sortable-header {
        cursor: pointer;
        user-select: none;
        transition: background 0.15s ease, color 0.15s ease;
      }
      .opportunity-table th.sortable-header:hover,
      .opportunity-table th.sortable-header:focus-visible {
        background: var(--surface-soft, rgba(0,0,0,0.04));
        color: var(--text, inherit);
        outline: none;
      }
      .table-sort-indicator {
        display: inline-block;
        margin-inline-start: 6px;
        font-size: 0.7em;
        opacity: 0.45;
        vertical-align: middle;
      }
      .opportunity-table th[aria-sort="ascending"] .table-sort-indicator,
      .opportunity-table th[aria-sort="descending"] .table-sort-indicator {
        opacity: 1;
        font-weight: 800;
      }
    `;
    document.head.appendChild(style);
  }

  function valueForCell(cell, index) {
    if (!cell) return "";

    if (index === 0) {
      const title = cell.querySelector(".title-main > span:last-child");
      return (title?.textContent || cell.textContent || "").trim().toLocaleLowerCase();
    }

    if (index === 1) {
      const city = cell.querySelector(".location-main");
      return (city?.textContent || cell.textContent || "").trim().toLocaleLowerCase();
    }

    if (index === 2) {
      const timestamp = Number(cell.dataset.sortTimestamp);
      if (Number.isFinite(timestamp)) return timestamp;
      return (cell.textContent || "").trim().toLocaleLowerCase();
    }

    if (index === 3) {
      const live = cell.querySelector("[data-deadline-timestamp]");
      if (live) {
        const timestamp = Number(live.dataset.deadlineTimestamp);
        if (Number.isFinite(timestamp)) return timestamp;
      }
      return (cell.textContent || "").trim().toLocaleLowerCase();
    }

    return (cell.textContent || "").trim().toLocaleLowerCase();
  }

  function compareValues(a, b, direction) {
    const aNumber = typeof a === "number";
    const bNumber = typeof b === "number";
    let result;

    if (aNumber && bNumber) {
      result = a - b;
    } else {
      const language = document.documentElement.lang || "en";
      result = String(a).localeCompare(String(b), language, {
        numeric: true,
        sensitivity: "base",
      });
    }

    if (result === 0) return 0;
    return direction === "asc" ? result : -result;
  }

  function updateIndicators(table, activeIndex, direction) {
    table.querySelectorAll("thead th").forEach((header, index) => {
      if (!sortableColumns.has(index)) {
        header.removeAttribute("aria-sort");
        return;
      }

      header.setAttribute(
        "aria-sort",
        index === activeIndex
          ? direction === "asc" ? "ascending" : "descending"
          : "none",
      );

      let indicator = header.querySelector(".table-sort-indicator");
      if (!indicator) {
        indicator = document.createElement("span");
        indicator.className = "table-sort-indicator";
        indicator.setAttribute("aria-hidden", "true");
        header.appendChild(indicator);
      }

      indicator.textContent =
        index === activeIndex
          ? direction === "asc" ? "▲" : "▼"
          : "↕";
    });
  }

  function sortTable(table, index) {
    const current = state.get(table) || { index: null, direction: "asc" };
    const direction =
      current.index === index && current.direction === "asc"
        ? "desc"
        : "asc";
    const body = table.tBodies[0];
    if (!body) return;

    const rows = Array.from(body.rows);
    rows.sort((rowA, rowB) => {
      const a = valueForCell(rowA.cells[index], index);
      const b = valueForCell(rowB.cells[index], index);
      if (a === "" && b === "") return 0;
      if (a === "") return 1;
      if (b === "") return -1;
      return compareValues(a, b, direction);
    });

    const fragment = document.createDocumentFragment();
    rows.forEach((row) => fragment.appendChild(row));
    body.appendChild(fragment);

    state.set(table, { index, direction });
    updateIndicators(table, index, direction);
  }

  function decorateTable(table) {
    if (!table) return;

    const alreadyBound = table.dataset.tableSortBound === "true";
    table.dataset.tableSortBound = "true";

    table.querySelectorAll("thead th").forEach((header, index) => {
      if (!sortableColumns.has(index) || header.classList.contains("apply-column")) return;

      header.classList.add("sortable-header");
      header.tabIndex = 0;
      header.setAttribute("role", "button");

      if (!header.querySelector(".table-sort-indicator")) {
        const indicator = document.createElement("span");
        indicator.className = "table-sort-indicator";
        indicator.setAttribute("aria-hidden", "true");
        indicator.textContent = "↕";
        header.appendChild(indicator);
      }

      if (!alreadyBound) {
        header.addEventListener("click", () => sortTable(table, index));
        header.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            sortTable(table, index);
          }
        });
      }
    });

    const current = state.get(table);
    updateIndicators(
      table,
      current?.index ?? null,
      current?.direction ?? "asc",
    );
  }

  function scan(root = document) {
    root.querySelectorAll?.("table.opportunity-table").forEach(decorateTable);
  }

  function install() {
    installStyles();
    scan();
    const observer = new MutationObserver(() => scan());
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
