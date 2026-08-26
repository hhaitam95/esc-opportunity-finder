const TOPIC_ICONS = {
  "Education and training": "📚",
  "Creativity and culture": "🎨",
  "Social challenges": "🤝",
  "Citizenship and democratic participation": "🗳️",
  "Environment and natural protection": "🌱",
  "Health and wellbeing": "❤️",
  "Employment and entrepreneurship": "💼",
  "Physical education and sport": "⚽",
  "Working against discrimination (including gender discrimination)": "🫱🏻‍🫲🏽",
  "Reception and integration of refugees and migrants": "🏠",
  "Support to local Small and Medium Enterprises": "🏢",
  "Nutrition and subsistence agriculture": "🌾",
  Shelter: "🏠",
  "Disaster prevention and recovery": "🛟",
  "Disaster Preparedness": "🚨",
  "Post Disaster relief": "🆘",
  "WASH (Water, sanitation and hygiene)": "🚿",
};

const TOPIC_TRANSLATIONS = {
  "Citizenship and democratic participation": {
    fr: "Citoyenneté et participation démocratique",
    ar: "المواطنة والمشاركة الديمقراطية",
  },
  "Environment and natural protection": {
    fr: "Environnement et protection de la nature",
    ar: "البيئة وحماية الطبيعة",
  },
  "Creativity and culture": {
    fr: "Créativité et culture",
    ar: "الإبداع والثقافة",
  },
};

const ACTIVITY_TYPE_ICONS = {
  "Individual volunteering": "👤",
  "Team volunteering": "👥",
  "Volunteering teams": "👥",
  "Volunteering": "🤝",
  "Traineeship": "🎓",
  "Job": "💼",
};

const ACTIVITY_TYPE_TRANSLATIONS = {
  "Individual volunteering": {
    en: "Individual volunteering",
    fr: "Volontariat individuel",
    ar: "التطوع الفردي",
  },
  "Team volunteering": {
    en: "Team volunteering",
    fr: "Volontariat en équipe",
    ar: "التطوع ضمن فريق",
  },
  "Volunteering teams": {
    en: "Volunteering teams",
    fr: "Équipes de volontariat",
    ar: "فرق التطوع",
  },
  "Volunteering": {
    en: "Volunteering",
    fr: "Volontariat",
    ar: "التطوع",
  },
  "Traineeship": {
    en: "Traineeship",
    fr: "Stage",
    ar: "تدريب",
  },
  "Job": {
    en: "Job",
    fr: "Emploi",
    ar: "وظيفة",
  },
};

const dateFormatterCache = new Map();
const displayNamesCache = new Map();

function getDateFormatter(locale) {
  const key = String(locale || "en-GB");
  let formatter = dateFormatterCache.get(key);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(key, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    dateFormatterCache.set(key, formatter);
  }
  return formatter;
}

function getRegionDisplayNames(locale) {
  const key = String(locale || "en-GB");
  let displayNames = displayNamesCache.get(key);
  if (!displayNames && typeof Intl !== "undefined" && typeof Intl.DisplayNames === "function") {
    try {
      displayNames = new Intl.DisplayNames([key], { type: "region" });
      displayNamesCache.set(key, displayNames);
    } catch {
      return null;
    }
  }
  return displayNames || null;
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseDate(value) {
  if (!value) return null;
  const raw = String(value).trim();
  const date = /^\d{4}-\d{2}-\d{2}$/.test(raw)
    ? new Date(`${raw}T00:00:00`)
    : new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value, locale, fallback = "—") {
  const date = parseDate(value);
  if (!date) return fallback;
  try {
    return getDateFormatter(locale).format(date);
  } catch {
    return fallback;
  }
}

export function filterRows(opportunities, filters) {
  const search = String(filters.search || "").trim().toLocaleLowerCase();
  const country = String(filters.country || "").trim().toUpperCase();
  const type = String(filters.type || "").trim();

  return opportunities.filter((opportunity) => {
    if (search) {
      const text = [
        opportunity.title,
        opportunity.town,
        opportunity.location,
        opportunity.country,
        opportunity.activity_type,
        Array.isArray(opportunity.topics) ? opportunity.topics.join(" ") : "",
      ].join(" ").toLocaleLowerCase();
      if (!text.includes(search)) return false;
    }

    if (country && String(opportunity.country || "").toUpperCase() !== country) return false;
    if (type && String(opportunity.activity_type || "") !== type) return false;
    return true;
  });
}

function dateValue(value) {
  const date = parseDate(value);
  return date ? date.getTime() : Number.POSITIVE_INFINITY;
}

export function sortRows(opportunities, sort) {
  const result = [...opportunities];
  if (sort === "created") {
    return result.sort((a, b) => String(b.created || "").localeCompare(String(a.created || "")));
  }
  if (sort === "start") {
    return result.sort((a, b) => dateValue(a.start_date) - dateValue(b.start_date));
  }
  return result.sort((a, b) => dateValue(a.deadline) - dateValue(b.deadline));
}

function safeUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value, "https://youth.europa.eu");
    if (url.protocol !== "http:" && url.protocol !== "https:") return "";
    return url.href;
  } catch {
    return "";
  }
}

function renderCountry(opportunity, locale) {
  const code = String(opportunity.country || "").trim().toUpperCase();
  if (!code) return "";

  let name = code;
  let flag = "🌍";
  try {
    const displayNames = getRegionDisplayNames(locale);
    if (displayNames) {
      name = displayNames.of(code) || code;
    }
    if (/^[A-Z]{2}$/.test(code)) {
      flag = String.fromCodePoint(...code.split("").map((letter) => 127397 + letter.charCodeAt(0)));
    }
  } catch {
    // Keep fallback values.
  }

  return `<span class="country-display"><span class="country-flag" aria-hidden="true">${flag}</span><span>${escapeHtml(name)}</span></span>`;
}

const CITY_NAME_CORRECTIONS = {
  "SK|BANSKA BYSTRICA": "Banská Bystrica",
  "SK|BRATISLAVA": "Bratislava",
  "SK|KOSICE": "Košice",
  "SK|NITRA": "Nitra",
  "SK|PRESOV": "Prešov",
  "SK|ZILINA": "Žilina",
  "PL|BIALYSTOK": "Białystok",
  "PL|JELENIA GORA": "Jelenia Góra",
  "PL|LODZ": "Łódź",
  "PL|POZNAN": "Poznań",
  "PL|WROCLAW": "Wrocław",
  "PL|KRAKOW": "Kraków",
  "PL|GDANSK": "Gdańsk",
  "PL|WARSAW": "Warsaw",
  "RO|TIMISOARA": "Timișoara",
  "RO|BUCHAREST": "Bucharest",
  "RO|CLUJ-NAPOCA": "Cluj-Napoca",
  "CZ|PRAGUE": "Prague",
  "CZ|PRAHA": "Praha",
  "HU|BUDAPEST": "Budapest",
  "HR|ZAGREB": "Zagreb",
  "SI|LJUBLJANA": "Ljubljana",
  "LT|VILNIUS": "Vilnius",
  "LV|RIGA": "Riga",
  "EE|TALLINN": "Tallinn",
  "PT|LISBON": "Lisbon",
  "PT|PORTO": "Porto",
  "ES|MADRID": "Madrid",
  "ES|BARCELONA": "Barcelona",
  "IT|ROME": "Rome",
  "IT|GENOA": "Genoa",
  "IT|GENOVA": "Genova",
  "FR|PARIS": "Paris",
  "DE|BERLIN": "Berlin",
  "BE|BRUSSELS": "Brussels",
  "NL|AMSTERDAM": "Amsterdam",
};

const CITY_TRANSLATIONS = {
  "IT|PALERMO": {
    fr: "Palerme",
    ar: "باليرمو",
  },
  "IT|ROME": {
    fr: "Rome",
    ar: "روما",
  },
  "IT|GENOA": {
    fr: "Gênes",
    ar: "جنوة",
  },
  "IT|GENOVA": {
    fr: "Gênes",
    ar: "جنوة",
  },
  "IT|MILAN": {
    fr: "Milan",
    ar: "ميلانو",
  },
  "IT|MILANO": {
    fr: "Milan",
    ar: "ميلانو",
  },
  "IT|NAPLES": {
    fr: "Naples",
    ar: "نابولي",
  },
  "IT|NAPOLI": {
    fr: "Naples",
    ar: "نابولي",
  },
  "IT|FLORENCE": {
    fr: "Florence",
    ar: "فلورنسا",
  },
  "IT|FIRENZE": {
    fr: "Florence",
    ar: "فلورنسا",
  },
  "FR|PARIS": {
    fr: "Paris",
    ar: "باريس",
  },
  "DE|BERLIN": {
    fr: "Berlin",
    ar: "برلين",
  },
  "DE|MUNICH": {
    fr: "Munich",
    ar: "ميونخ",
  },
  "DE|MÜNCHEN": {
    fr: "Munich",
    ar: "ميونخ",
  },
  "DE|COLOGNE": {
    fr: "Cologne",
    ar: "كولونيا",
  },
  "DE|KOLN": {
    fr: "Cologne",
    ar: "كولونيا",
  },
  "DE|KÖLN": {
    fr: "Cologne",
    ar: "كولونيا",
  },
  "ES|MADRID": {
    fr: "Madrid",
    ar: "مدريد",
  },
  "ES|BARCELONA": {
    fr: "Barcelone",
    ar: "برشلونة",
  },
  "ES|SEVILLE": {
    fr: "Séville",
    ar: "إشبيلية",
  },
  "ES|SEVILLA": {
    fr: "Séville",
    ar: "إشبيلية",
  },
  "PT|LISBON": {
    fr: "Lisbonne",
    ar: "لشبونة",
  },
  "PT|LISBOA": {
    fr: "Lisbonne",
    ar: "لشبونة",
  },
  "PT|PORTO": {
    fr: "Porto",
    ar: "بورتو",
  },
  "NL|AMSTERDAM": {
    fr: "Amsterdam",
    ar: "أمستردام",
  },
  "BE|BRUSSELS": {
    fr: "Bruxelles",
    ar: "بروكسل",
  },
  "BE|BRUXELLES": {
    fr: "Bruxelles",
    ar: "بروكسل",
  },
  "GR|ATHENS": {
    fr: "Athènes",
    ar: "أثينا",
  },
  "GR|ATHINA": {
    fr: "Athènes",
    ar: "أثينا",
  },
  "TR|ISTANBUL": {
    fr: "Istanbul",
    ar: "إسطنبول",
  },
  "TR|ANKARA": {
    fr: "Ankara",
    ar: "أنقرة",
  },
  "PL|WARSAW": {
    fr: "Varsovie",
    ar: "وارسو",
  },
  "PL|WARSZAWA": {
    fr: "Varsovie",
    ar: "وارسو",
  },
  "PL|KRAKOW": {
    fr: "Cracovie",
    ar: "كراكوف",
  },
  "PL|KRAKÓW": {
    fr: "Cracovie",
    ar: "كراكوف",
  },
  "PL|GDANSK": {
    fr: "Gdańsk",
    ar: "غدانسك",
  },
  "PL|WROCLAW": {
    fr: "Wrocław",
    ar: "فروتسواف",
  },
  "CZ|PRAGUE": {
    fr: "Prague",
    ar: "براغ",
  },
  "CZ|PRAHA": {
    fr: "Prague",
    ar: "براغ",
  },
  "AT|VIENNA": {
    fr: "Vienne",
    ar: "فيينا",
  },
  "AT|WIEN": {
    fr: "Vienne",
    ar: "فيينا",
  },
  "CH|GENEVA": {
    fr: "Genève",
    ar: "جنيف",
  },
  "CH|GENÈVE": {
    fr: "Genève",
    ar: "جنيف",
  },
  "CH|ZURICH": {
    fr: "Zurich",
    ar: "زيورخ",
  },
  "CH|ZÜRICH": {
    fr: "Zurich",
    ar: "زيورخ",
  },
  "RO|BUCHAREST": {
    fr: "Bucarest",
    ar: "بوخارست",
  },
  "RO|BUCURESTI": {
    fr: "Bucarest",
    ar: "بوخارست",
  },
  "HU|BUDAPEST": {
    fr: "Budapest",
    ar: "بودابست",
  },
  "SE|STOCKHOLM": {
    fr: "Stockholm",
    ar: "ستوكهولم",
  },
  "DK|COPENHAGEN": {
    fr: "Copenhague",
    ar: "كوبنهاغن",
  },
  "DK|KOBENHAVN": {
    fr: "Copenhague",
    ar: "كوبنهاغن",
  },
  "NO|OSLO": {
    fr: "Oslo",
    ar: "أوسلو",
  },
  "FI|HELSINKI": {
    fr: "Helsinki",
    ar: "هلسنكي",
  },
  "IE|DUBLIN": {
    fr: "Dublin",
    ar: "دبلن",
  },
  "GB|LONDON": {
    fr: "Londres",
    ar: "لندن",
  },
  "GB|EDINBURGH": {
    fr: "Édimbourg",
    ar: "إدنبرة",
  },
  "HR|ZAGREB": {
    fr: "Zagreb",
    ar: "زغرب",
  },
  "SI|LJUBLJANA": {
    fr: "Ljubljana",
    ar: "ليوبليانا",
  },
  "SK|BRATISLAVA": {
    fr: "Bratislava",
    ar: "براتيسلافا",
  },
  "BG|SOFIA": {
    fr: "Sofia",
    ar: "صوفيا",
  },
  "RS|BELGRADE": {
    fr: "Belgrade",
    ar: "بلغراد",
  },
  "BA|SARAJEVO": {
    fr: "Sarajevo",
    ar: "سراييفو",
  },
  "AL|TIRANA": {
    fr: "Tirana",
    ar: "تيرانا",
  },
  "MK|SKOPJE": {
    fr: "Skopje",
    ar: "سكوبيه",
  },
  "LT|VILNIUS": {
    fr: "Vilnius",
    ar: "فيلنيوس",
  },
  "LV|RIGA": {
    fr: "Riga",
    ar: "ريغا",
  },
  "EE|TALLINN": {
    fr: "Tallinn",
    ar: "تالين",
  },
  "CY|NICOSIA": {
    fr: "Nicosie",
    ar: "نيقوسيا",
  },
  "MT|VALLETTA": {
    fr: "La Valette",
    ar: "فاليتا",
  },
};

function titleCaseCity(value) {
  return String(value || "")
    .trim()
    .toLocaleLowerCase()
    .replace(/(^|[\s'’\-])([\p{L}])/gu, (_, prefix, letter) => `${prefix}${letter.toLocaleUpperCase()}`);
}

function formatCity(opportunity, locale) {
  const raw = String(opportunity.town || opportunity.location || "").trim();
  if (!raw) return "";

  const country = String(opportunity.country || "").trim().toUpperCase();
  const key = `${country}|${raw.toUpperCase()}`;
  const language = locale.startsWith("fr")
    ? "fr"
    : locale.startsWith("ar")
      ? "ar"
      : "en";

  if (CITY_TRANSLATIONS[key]?.[language]) {
    return CITY_TRANSLATIONS[key][language];
  }

  if (CITY_NAME_CORRECTIONS[key]) return CITY_NAME_CORRECTIONS[key];

  if (raw === raw.toLocaleUpperCase() && /\p{L}/u.test(raw)) return titleCaseCity(raw);
  return raw;
}

function topicLabel(topic, locale) {
  const language = locale.startsWith("fr") ? "fr" : locale.startsWith("ar") ? "ar" : "en";
  return TOPIC_TRANSLATIONS[topic]?.[language] || topic;
}

function activityTypeLabel(type, locale) {
  const language = locale.startsWith("fr") ? "fr" : locale.startsWith("ar") ? "ar" : "en";
  return ACTIVITY_TYPE_TRANSLATIONS[type]?.[language] || type;
}

function renderTopics(topics, locale) {
  if (!Array.isArray(topics) || !topics.length) return "";
  return `<div class="topic-tags">${topics.map((topic) => {
    const label = topicLabel(topic, locale);
    return `
    <span class="topic-tag" title="${escapeHtml(label)}">
      ${TOPIC_ICONS[topic] ? `<span class="topic-icon">${TOPIC_ICONS[topic]}</span>` : ""}
      <span>${escapeHtml(label)}</span>
    </span>
  `;
  }).join("")}</div>`;
}

function calendarDuration(startValue, endValue, locale) {
  const start = parseDate(startValue);
  const end = parseDate(endValue);
  if (!start || !end || end < start) return "";

  let cursor = new Date(start.getTime());
  let months = 0;
  while (true) {
    const next = new Date(cursor.getFullYear(), cursor.getMonth() + 1, cursor.getDate());
    if (next > end) break;
    cursor = next;
    months += 1;
  }

  const days = Math.round((end - cursor) / 86400000);
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  const parts = [];

  const units = locale.startsWith("fr")
    ? { year: ["an", "ans"], month: ["mois", "mois"], day: ["jour", "jours"] }
    : locale.startsWith("ar")
      ? { year: ["سنة", "سنوات"], month: ["شهر", "أشهر"], day: ["يوم", "أيام"] }
      : { year: ["year", "years"], month: ["month", "months"], day: ["day", "days"] };

  if (years) parts.push(`${years} ${years === 1 ? units.year[0] : units.year[1]}`);
  if (remainingMonths) parts.push(`${remainingMonths} ${remainingMonths === 1 ? units.month[0] : units.month[1]}`);
  if (!parts.length && days) parts.push(`${days} ${days === 1 ? units.day[0] : units.day[1]}`);
  if (!parts.length) parts.push(`0 ${units.day[1]}`);

  return parts.slice(0, 2).join(" ");
}

function renderActivityDates(opportunity, locale, t) {
  const activity = [
    opportunity.start_date ? formatDate(opportunity.start_date, locale, "") : "",
    opportunity.end_date ? formatDate(opportunity.end_date, locale, "") : "",
  ].filter(Boolean).join(" → ");

  if (!activity) return `<span class="date-display"><span class="date-icon" aria-hidden="true">📅</span><span>${escapeHtml(t("noDates"))}</span></span>`;

  const duration = calendarDuration(opportunity.start_date, opportunity.end_date, locale);
  return `<span class="date-display"><span class="date-icon" aria-hidden="true">📅</span><span><span class="activity-dates">${escapeHtml(activity)}</span>${duration ? `<span class="activity-duration">${escapeHtml(duration)}</span>` : ""}</span></span>`;
}

function formatLiveRemaining(deadlineValue, locale, t) {
  const deadline = parseDate(deadlineValue);
  if (!deadline) return "";

  const remaining = deadline.getTime() - Date.now();
  if (remaining <= 0) return t("deadlineToday");

  const totalSeconds = Math.floor(remaining / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  if (days > 0) {
    return locale.startsWith("fr")
      ? `${days} j ${hours} h ${minutes} min restantes`
      : locale.startsWith("ar")
        ? `${days} يوم ${hours} ساعة ${minutes} دقيقة متبقية`
        : `${days}d ${hours}h ${minutes}m remaining`;
  }

  return locale.startsWith("fr")
    ? `${hours} h ${minutes} min restantes`
    : locale.startsWith("ar")
      ? `${hours} ساعة ${minutes} دقيقة متبقية`
      : `${hours}h ${minutes}m remaining`;
}

function renderDeadline(opportunity, locale, t) {
  if (!opportunity.deadline) {
    return `<span class="deadline-none"><span class="deadline-icon" aria-hidden="true">⏰</span><span class="deadline-date">${escapeHtml(t("noDeadline"))}</span></span>`;
  }

  const deadline = parseDate(opportunity.deadline);
  if (!deadline) {
    return `<span class="deadline-normal"><span class="deadline-icon" aria-hidden="true">⏰</span><span class="deadline-date">${escapeHtml(t("noDeadline"))}</span></span>`;
  }

  const remaining = deadline.getTime() - Date.now();
  let statusClass = "deadline-normal";
  if (remaining <= 86400000 && remaining > 0) statusClass = "deadline-urgent";
  else if (remaining <= 7 * 86400000 && remaining > 0) statusClass = "deadline-soon";
  else if (remaining <= 0) statusClass = "deadline-urgent";

  const formatted = formatDate(opportunity.deadline, locale, t("noDeadline"));
  const countdown = formatLiveRemaining(opportunity.deadline, locale, t);
  return `<span class="${statusClass} live-deadline" data-deadline-timestamp="${deadline.getTime()}" data-deadline-locale="${escapeHtml(locale)}"><span class="deadline-icon" aria-hidden="true">⏰</span><span><span class="deadline-date">${escapeHtml(formatted)}</span><span class="deadline-relative">${escapeHtml(countdown)}</span></span></span>`;
}

function renderActivityType(opportunity, locale, t) {
  const type = opportunity.activity_type || t("noType");
  const icon = ACTIVITY_TYPE_ICONS[type] || "🤝";
  const label = activityTypeLabel(type, locale);
  return `<span class="type-label"><span class="type-icon" aria-hidden="true">${icon}</span><span>${escapeHtml(label)}</span></span>`;
}

function renderRow(opportunity, options) {
  const { archived, newIds, locale, t } = options;
  const id = String(opportunity.id || opportunity.opid || "");
  const image = safeUrl(opportunity.image_url);
  const link = safeUrl(opportunity.url);
  const title = String(opportunity.title || "");
  const location = formatCity(opportunity, locale) || t("noLocation");
  const isNew = !archived && newIds.has(id);

  return `<tr>
    <td class="title-cell">
      <div class="title-main">
        ${image ? `<img class="opportunity-image" src="${escapeHtml(image)}" alt="" loading="lazy" onerror="this.remove()">` : ""}
        ${isNew ? `<span class="new-badge">✨ ${escapeHtml(t("new"))}</span>` : ""}
        <span>${escapeHtml(title)}</span>
      </div>
      ${renderTopics(opportunity.topics, locale)}
    </td>
    <td class="location-cell">
      <div class="location-main">${escapeHtml(location)}</div>
      <div class="location-country">${renderCountry(opportunity, locale)}</div>
    </td>
    <td class="activity-cell">${renderActivityDates(opportunity, locale, t)}</td>
    <td class="deadline-cell">${renderDeadline(opportunity, locale, t)}</td>
    <td class="type-cell">${renderActivityType(opportunity, locale, t)}</td>
    <td class="apply-column">${link ? `<a class="apply-button" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(t("view"))}</a>` : ""}</td>
  </tr>`;
}

export function renderRows(opportunities, options) {
  return opportunities.map((opportunity) => renderRow(opportunity, options)).join("");
}

function updateLiveDeadlines() {
  document.querySelectorAll("[data-deadline-timestamp]").forEach((element) => {
    const timestamp = Number(element.dataset.deadlineTimestamp);
    if (!Number.isFinite(timestamp)) return;
    const remaining = timestamp - Date.now();
    const locale = element.dataset.deadlineLocale || "en-GB";
    const seconds = Math.max(0, Math.floor(remaining / 1000));
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const countdown = element.querySelector(".deadline-relative");

    if (countdown) {
      if (remaining <= 0) {
        countdown.textContent = locale.startsWith("fr") ? "Date limite dépassée" : locale.startsWith("ar") ? "انتهى الموعد النهائي" : "Deadline passed";
      } else if (days > 0) {
        countdown.textContent = locale.startsWith("fr") ? `${days} j ${hours} h ${minutes} min restantes` : locale.startsWith("ar") ? `${days} يوم ${hours} ساعة ${minutes} دقيقة متبقية` : `${days}d ${hours}h ${minutes}m remaining`;
      } else {
        countdown.textContent = locale.startsWith("fr") ? `${hours} h ${minutes} min restantes` : locale.startsWith("ar") ? `${hours} ساعة ${minutes} دقيقة متبقية` : `${hours}h ${minutes}m remaining`;
      }
    }

    element.classList.remove("deadline-normal", "deadline-soon", "deadline-urgent", "deadline-none");
    if (remaining <= 0 || remaining <= 86400000) element.classList.add("deadline-urgent");
    else if (remaining <= 7 * 86400000) element.classList.add("deadline-soon");
    else element.classList.add("deadline-normal");
  });
}

if (typeof window !== "undefined") {
  window.setInterval(updateLiveDeadlines, 60000);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", updateLiveDeadlines, { once: true });
  } else {
    updateLiveDeadlines();
  }
}
