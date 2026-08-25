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

      const fallbackName = normalized === "GR" ? "Greece" : "United Kingdom";
      let translatedName = fallbackName;

      try {
        const displayNames = new Intl.DisplayNames([locale], { type: "region" });
        translatedName = displayNames.of(normalized) || fallbackName;
      } catch {
        // Keep fallback.
      }

      if (nameNode.textContent !== translatedName) {
        nameNode.textContent = translatedName;
      }

      if (/^[A-Z]{2}$/.test(normalized)) {
        const flag = String.fromCodePoint(
          ...normalized.split("").map((letter) => 127397 + letter.charCodeAt(0)),
        );
        if (flagNode.textContent !== flag) {
          flagNode.textContent = flag;
        }
      }
    });
  }

  function start() {
    normalizeCountryDisplay();
    window.normalizeCountryDisplay = normalizeCountryDisplay;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
