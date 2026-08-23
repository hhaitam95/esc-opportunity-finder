(() => {
  const LABELS = {
    en: {
      today: "Today",
      tomorrow: "Tomorrow",
      expiredToday: "Expired today",
      yesterday: "Yesterday",
    },
    fr: {
      today: "Aujourd’hui",
      tomorrow: "Demain",
      expiredToday: "Expirée aujourd’hui",
      yesterday: "Hier",
    },
    ar: {
      today: "اليوم",
      tomorrow: "غدًا",
      expiredToday: "انتهت اليوم",
      yesterday: "أمس",
    },
  };

  function language() {
    const value = (document.documentElement.lang || "en").toLowerCase();
    return value.startsWith("fr") ? "fr" : value.startsWith("ar") ? "ar" : "en";
  }

  function localDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function dayDifference(from, to) {
    return Math.round((localDay(to) - localDay(from)) / 86400000);
  }

  function updateDeadlineLabels(root = document) {
    const labels = LABELS[language()];
    const now = new Date();

    root.querySelectorAll?.(".live-deadline").forEach((element) => {
      const timestamp = Number(element.dataset.deadlineTimestamp);
      const label = element.querySelector(".deadline-date");
      if (!Number.isFinite(timestamp) || !label) return;

      const deadline = new Date(timestamp);
      const days = dayDifference(now, deadline);
      const archived = Boolean(element.closest(".expired-table"));

      if (archived) {
        if (days === 0) label.textContent = labels.expiredToday;
        else if (days === -1) label.textContent = labels.yesterday;
      } else {
        if (days === 0) label.textContent = labels.today;
        else if (days === 1) label.textContent = labels.tomorrow;
      }
    });
  }

  function start() {
    updateDeadlineLabels();
    const observer = new MutationObserver(() => updateDeadlineLabels());
    observer.observe(document.body, { childList: true, subtree: true });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    setInterval(updateDeadlineLabels, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
