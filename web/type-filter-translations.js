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

  function translate() {
    const select = document.getElementById("type-filter");
    if (!select) return;

    const language = getLanguage();

    Array.from(select.options).forEach((option) => {
      if (!option.value) return;
      const key = option.dataset.typeKey || option.value;
      const label = translations[key]?.[language];
      if (!label) return;

      option.dataset.typeKey = key;
      if (option.textContent !== label) {
        option.textContent = label;
      }
    });
  }

  function start() {
    translate();
    window.translateTypeFilter = translate;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
