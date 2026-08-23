(() => {
  function formatArabicLastUpdated() {
    const element = document.getElementById("last-updated");
    if (!element || !document.documentElement.lang.startsWith("ar")) return;

    const data = element.textContent.trim();
    if (!data || data === "—") return;

    const existing = element.dataset.arabicLastUpdated;
    if (existing === data) return;

    const match = data.match(/(\d{1,2})[\u200e\u200f\u202a-\u202e\/]+(\d{1,2})[\u200e\u200f\u202a-\u202e\/]+(\d{4})[،,]?\s*(\d{1,2}):(\d{2})/);
    if (!match) return;

    const month = Number(match[2]);
    const day = Number(match[1]);
    const year = Number(match[3]);
    const hour = match[4].padStart(2, "0");
    const minute = match[5];
    if (!month || !day || !year) return;

    const date = new Date(Date.UTC(year, month - 1, day));
    const monthName = new Intl.DateTimeFormat("ar-MA", {
      month: "long",
      timeZone: "UTC",
    }).format(date);

    element.textContent = `آخر تحديث ${day} ${monthName} ${year}، الساعة ${hour}:${minute}`;
    element.dataset.arabicLastUpdated = data;
  }

  const observer = new MutationObserver(formatArabicLastUpdated);

  function start() {
    formatArabicLastUpdated();
    const target = document.getElementById("last-updated");
    if (target) observer.observe(target, { childList: true, characterData: true, subtree: true });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
