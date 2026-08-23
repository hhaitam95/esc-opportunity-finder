(() => {
  const COUNTRY_CODE_ALIASES = {
    EL: "GR",
    UK: "GB",
  };

  function normalizeCountryDisplay(root = document) {
    const locale = document.documentElement.lang || "en";
    const displays = root.querySelectorAll?.(".country-display") || [];

    displays.forEach((display) => {
      const nameNode = display.querySelector(".country-flag + span");
      const flagNode = display.querySelector(".country-flag");
      if (!nameNode || !flagNode) return;

      const raw = String(nameNode.textContent || "").trim().toUpperCase();
      const normalized = COUNTRY_CODE_ALIASES[raw];
      if (!normalized) return;

      try {
        const displayNames = new Intl.DisplayNames([locale], { type: "region" });
        nameNode.textContent = displayNames.of(normalized) || "Greece";
      } catch {
        nameNode.textContent = normalized === "GR" ? "Greece" : "United Kingdom";
      }

      if (/^[A-Z]{2}$/.test(normalized)) {
        flagNode.textContent = String.fromCodePoint(
          ...normalized.split("").map((letter) => 127397 + letter.charCodeAt(0)),
        );
      }
    });
  }

  const observer = new MutationObserver(() => normalizeCountryDisplay());

  function start() {
    normalizeCountryDisplay();
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start, { once: true });
})();
