const CITY_LOCALIZATION_OVERRIDES = {
  "IT|CAGLIARI": { fr: "Cagliari", ar: "كالياري" },
  "IT|PALERMO": { fr: "Palerme", ar: "باليرمو" },
  "IT|ROME": { fr: "Rome", ar: "روما" },
  "IT|GENOA": { fr: "Gênes", ar: "جنوة" },
  "IT|MILAN": { fr: "Milan", ar: "ميلانو" },
  "IT|NAPLES": { fr: "Naples", ar: "نابولي" },
  "IT|FLORENCE": { fr: "Florence", ar: "فلورنسا" },
  "DE|MUNICH": { fr: "Munich", ar: "ميونخ" },
  "DE|COLOGNE": { fr: "Cologne", ar: "كولونيا" },
  "ES|BARCELONA": { fr: "Barcelone", ar: "برشلونة" },
  "ES|SEVILLE": { fr: "Séville", ar: "إشبيلية" },
  "PT|LISBON": { fr: "Lisbonne", ar: "لشبونة" },
  "BE|BRUSSELS": { fr: "Bruxelles", ar: "بروكسل" },
  "GR|ATHENS": { fr: "Athènes", ar: "أثينا" },
  "TR|ISTANBUL": { fr: "Istanbul", ar: "إسطنبول" },
  "TR|ANKARA": { fr: "Ankara", ar: "أنقرة" },
  "PL|WARSAW": { fr: "Varsovie", ar: "وارسو" },
  "PL|KRAKOW": { fr: "Cracovie", ar: "كراكوف" },
  "CZ|PRAGUE": { fr: "Prague", ar: "براغ" },
  "CZ|NACHOD": { fr: "Náchod", ar: "ناخود" },
  "AT|VIENNA": { fr: "Vienne", ar: "فيينا" },
  "CH|GENEVA": { fr: "Genève", ar: "جنيف" },
  "RO|BUCHAREST": { fr: "Bucarest", ar: "بوخارست" },
  "GB|LONDON": { fr: "Londres", ar: "لندن" },
  "GB|EDINBURGH": { fr: "Édimbourg", ar: "إدنبرة" },
  "IE|DUBLIN": { fr: "Dublin", ar: "دبلن" },
  "HR|ZAGREB": { fr: "Zagreb", ar: "زغرب" },
  "SI|LJUBLJANA": { fr: "Ljubljana", ar: "ليوبليانا" },
  "SK|BRATISLAVA": { fr: "Bratislava", ar: "براتيسلافا" },
  "BG|SOFIA": { fr: "Sofia", ar: "صوفيا" },
  "RS|BELGRADE": { fr: "Belgrade", ar: "بلغراد" },
  "BA|SARAJEVO": { fr: "Sarajevo", ar: "سراييفو" },
  "AL|TIRANA": { fr: "Tirana", ar: "تيرانا" },
  "MK|SKOPJE": { fr: "Skopje", ar: "سكوبيه" },
  "LT|VILNIUS": { fr: "Vilnius", ar: "فيلنيوس" },
  "LV|RIGA": { fr: "Riga", ar: "ريغا" },
  "EE|TALLINN": { fr: "Tallinn", ar: "تالين" },
  "CY|NICOSIA": { fr: "Nicosie", ar: "نيقوسيا" },
  "MT|VALLETTA": { fr: "La Valette", ar: "فاليتا" },
};

function normalizeCityKey(country, city) {
  const normalizedCountry = String(country || "").trim().toUpperCase();
  const normalizedCity = String(city || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\u200e\u200f\u202a-\u202e]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();
  return `${normalizedCountry}|${normalizedCity}`;
}

const ARABIC_DIGRAPHS = [
  ["sch", "ش"],
  ["tch", "تش"],
  ["shr", "شر"],
  ["sh", "ش"],
  ["ch", "خ"],
  ["th", "ث"],
  ["dh", "ذ"],
  ["kh", "خ"],
  ["gh", "غ"],
  ["ph", "ف"],
  ["ck", "ك"],
  ["qu", "ك"],
  ["ou", "و"],
  ["oo", "و"],
  ["ee", "ي"],
  ["ie", "ي"],
  ["ei", "ي"],
];

const ARABIC_LETTERS = {
  a: "ا",
  b: "ب",
  c: "ك",
  d: "د",
  e: "ي",
  f: "ف",
  g: "غ",
  h: "ه",
  i: "ي",
  j: "ج",
  k: "ك",
  l: "ل",
  m: "م",
  n: "ن",
  o: "و",
  p: "ب",
  q: "ق",
  r: "ر",
  s: "س",
  t: "ت",
  u: "و",
  v: "ف",
  w: "و",
  x: "كس",
  y: "ي",
  z: "ز",
};

function arabicTransliteration(city) {
  let value = String(city || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleLowerCase();
  if (!value) return "";

  for (const [from, to] of ARABIC_DIGRAPHS) {
    value = value.replaceAll(from, to);
  }

  let output = "";
  for (const char of value) {
    if (/\p{Script=Arabic}/u.test(char)) {
      output += char;
      continue;
    }
    output += ARABIC_LETTERS[char] || char;
  }

  return output
    .replace(/[\s-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function localizeNewCity(country, city, locale) {
  const language = String(locale || "en-GB").startsWith("fr")
    ? "fr"
    : String(locale || "en-GB").startsWith("ar")
      ? "ar"
      : "en";

  const original = String(city || "").trim();
  if (language === "en" || !original) return original;

  const key = normalizeCityKey(country, original);
  const override = CITY_LOCALIZATION_OVERRIDES[key];
  if (override?.[language]) return override[language];

  // French city names are often identical to the local/international name.
  // Do not invent French translations for obscure towns.
  if (language === "fr") return original;

  // For previously unseen Arabic locations, use a deterministic transliteration
  // rather than a network lookup. Explicit overrides remain authoritative.
  return arabicTransliteration(original) || original;
}

export function normalizedCityKey(country, city) {
  return normalizeCityKey(country, city);
}
