(() => {
  const translations = {
    "Individual volunteering": {
      en: "Individual volunteering",
      fr: "Volontariat individuel",
      ar: "التطوع الفردي",
    },
    "Volunteering teams": {
      en: "Volunteering teams",
      fr: "Équipes de volontariat",
      ar: "فرق التطوع",
    },
  };

  const getLanguage = () => {
    const value = document.documentElement.lang || "en";
    if (value.startsWith("fr")) return "fr";
    if (value.startsWith("ar")) return "ar";
    return "en";
  };

  const translate = () => {
    const select = document.getElementById("type-filter");
    if (!select) return;

    const language = getLanguage();

    Array.from(select.options).forEach((option) => {
      if (!option.value) return;
      const key = option.dataset.typeKey || option.value;
      const label = translations[key]?.[language];
      if (!label) return;
      option.dataset.typeKey = key;
      option.textContent = label;
    });
  };

  const start = () => {
    const select = document.getElementById("type-filter");
    if (!select) return;

    translate();

    const observer = new MutationObserver(translate);
    observer.observe(select, { childList: true });

    const languageObserver = new MutationObserver(translate);
    languageObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["lang"],
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
