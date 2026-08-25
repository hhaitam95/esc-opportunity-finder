(() => {
  const LABELS = {
    en: { today: "Today", tomorrow: "Tomorrow", expiredToday: "Expired today", yesterday: "Yesterday" },
    fr: { today: "Aujourd’hui", tomorrow: "Demain", expiredToday: "Expirée aujourd’hui", yesterday: "Hier" },
    ar: { today: "اليوم", tomorrow: "غدًا", expiredToday: "انتهت اليوم", yesterday: "أمس" },
  };

  const RELATIVE_LABELS = new Set(Object.values(LABELS).flatMap((group) => Object.values(group)));

  function language() {
    const value = String(document.documentElement.lang || "en").toLowerCase();
    return value.startsWith("fr") ? "fr" : value.startsWith("ar") ? "ar" : "en";
  }

  function localDay(value) {
    const date = new Date(value);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  }

  function dayDifference(from, to) {
    return Math.round((localDay(to) - localDay(from)) / 86400000);
  }

  function updateLabels() {
    const labels = LABELS[language()];
    const now = new Date();

    document.querySelectorAll(".live-deadline").forEach((element) => {
      const timestamp = Number(element.dataset.deadlineTimestamp);
      const label = element.querySelector(".deadline-date");
      if (!Number.isFinite(timestamp) || !label) return;

      if (!element.dataset.deadlineOriginalLabel && !RELATIVE_LABELS.has(label.textContent.trim())) {
        element.dataset.deadlineOriginalLabel = label.textContent;
      }

      const days = dayDifference(now, timestamp);
      const expiredTable = Boolean(element.closest(".expired-table"));
      let replacement = null;

      if (expiredTable) {
        if (days === 0) replacement = labels.expiredToday;
        else if (days === -1) replacement = labels.yesterday;
      } else {
        if (days === 0) replacement = labels.today;
        else if (days === 1) replacement = labels.tomorrow;
      }

      const nextText = replacement || element.dataset.deadlineOriginalLabel;
      if (nextText && label.textContent !== nextText) {
        label.textContent = nextText;
      }
    });
  }

  function start() {
    updateLabels();
    window.updateRelativeDeadlineLabels = updateLabels;
    window.setInterval(updateLabels, 60000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
