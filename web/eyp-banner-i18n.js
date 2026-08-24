(() => {
  const translations = {
    en: "EU funded volunteering opportunities",
    fr: "Opportunités de volontariat financées par l’UE",
    ar: "فرص التطوع الممولة من الاتحاد الأوروبي",
  };

  const update = () => {
    const banner = document.querySelector("[data-i18n='eypBannerTitle']");
    if (!banner) return;

    const language = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
    banner.textContent = translations[language] || translations.en;
  };

  update();

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "attributes" && mutation.attributeName === "lang") {
        update();
        break;
      }
    }
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"],
  });
})();
