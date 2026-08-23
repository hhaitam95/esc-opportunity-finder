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
      let replacement = null;

      if (archived) {
        if (days === 0) replacement = labels.expiredToday;
        else if (days === -1) replacement = labels.yesterday;
      } else {
        if (days === 0) replacement = labels.today;
        else if (days === 1) replacement = labels.tomorrow;
      }

      if (replacement && label.textContent !== replacement) {
        label.textContent = replacement;
      }
    });
  }

  function start() {
    updateDeadlineLabels();

    let scheduled = false;
    const scheduleUpdate = () => {
      if (scheduled) return;
      scheduled = true;
      queueMicrotask(() => {
        scheduled = false;
        updateDeadlineLabels();
      });
    };

    const observer = new MutationObserver(scheduleUpdate);
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
