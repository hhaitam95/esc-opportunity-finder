(() => {
  const DIGIT_MAP = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
  };

  function normalizeDigits(value) {
    return String(value || "").replace(/[٠-٩]/g, (digit) => DIGIT_MAP[digit] || digit);
  }

  function formatArabicLastUpdated() {
    const element = document.getElementById("last-updated");
    if (!element || !document.documentElement.lang.startsWith("ar")) return;

    const data = element.textContent.trim();
    if (!data || data === "—") return;

    const normalized = normalizeDigits(data).replace(/[\u200e\u200f\u202a-\u202e]/g, "");
    const match = normalized.match(/(\d{1,2})\D+(\d{1,2})\D+(\d{4})\D+(\d{1,2}):(\d{2})/);
    if (!match) return;

    const day = Number(match[1]);
    const month = Number(match[2]);
    const year = Number(match[3]);
    const hour = match[4].padStart(2, "0");
    const minute = match[5];
    if (!day || !month || !year) return;

    const date = new Date(Date.UTC(year, month - 1, day));
    if (Number.isNaN(date.getTime())) return;

    const monthName = new Intl.DateTimeFormat("ar-MA", {
      month: "long",
      timeZone: "UTC",
    }).format(date);

    const formatted = `${day} ${monthName} ${year}، الساعة ${hour}:${minute}`;
    if (element.textContent.trim() === formatted) return;

    element.textContent = formatted;
  }

  let scheduled = false;

  function scheduleFormat() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      formatArabicLastUpdated();
    });
  }

  const observer = new MutationObserver(scheduleFormat);

  function start() {
    scheduleFormat();
    const target = document.getElementById("last-updated");
    if (target) {
      observer.observe(target, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["lang"],
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
