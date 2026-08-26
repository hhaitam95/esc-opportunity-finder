import { localizeNewCity as localizeCityName } from "./city-localizations-original.js";

const ARABIC_LOCALITY_OVERRIDES = {
  "IS|HAFNARFJÖRÐUR": "هافنارفيوردور",
  "IS|HAFNARFJORDUR": "هافنارفيوردور",
};

function clean(value) {
  return String(value || "")
    .replace(/[\u200e\u200f\u202a-\u202e]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[,;:\-–]+|[,;:]+$/gu, "")
    .trim();
}

function languageFor(locale) {
  const value = String(locale || "en-GB");
  if (value.startsWith("fr")) return "fr";
  if (value.startsWith("ar")) return "ar";
  return "en";
}

function extractPrimaryLocation(value) {
  let text = clean(value);
  if (!text) return "";

  text = text.replace(/^\d{4,6}\s*[-–]\s*/u, "");
  text = text.replace(/,?\s+(?:Italy|Italia|France|Germany|Deutschland|Spain|España|Portugal|Poland|Polska|Czechia|Türkiye|Turkey|Bolivia|Senegal|Romania|Nederland|Netherlands|Armenia|Georgia|Iceland|Ísland)$/iu, "");
  text = clean(text);

  const sentence = text.match(/\b(?:living in|will be living in|based in|located in)\s+(.+?)(?:\s+\([^)]*\))?(?:\s+and\s+(?:work|working)\s+in\s+[^.;]+)?[.;]?$/iu);
  if (sentence?.[1]) text = clean(sentence[1]);

  if (/\b(?:via|viale|rue|avenue|av\.?|boulevard|blvd\.?|street|st\.?|road|rd\.?|lane|ln\.?|straße|strasse|strada)\b/iu.test(text)) {
    const addressParts = text.split(/\s*,\s*/u).map(clean).filter(Boolean);
    if (addressParts.length > 1) text = addressParts[addressParts.length - 1];
  }

  const parts = text.split(/\s*\/\s*|\s*;\s*|\s*,\s*/u).map(clean).filter(Boolean);
  if (parts.length > 1) text = parts[0];

  text = text.replace(/^(Praha|Prague)\s+\d+(?:\s*[-–].*)?$/iu, "$1");
  text = text.replace(/^((?:Paris|Dublin|Berlin|Hamburg|Munich|München))\s+\d+$/iu, "$1");
  text = text.replace(/\s+-\s+(?:Nová Ves|Stodůlky|Stodulky)$/iu, "").trim();
  text = text.replace(/\s*\([^)]*\)$/u, "").trim();

  return clean(text);
}

function asciiLocality(value) {
  return clean(value)
    .replace(/ð/gi, "d")
    .replace(/þ/gi, "th")
    .replace(/æ/gi, "ae")
    .replace(/œ/gi, "oe")
    .replace(/ø/gi, "o")
    .replace(/ł/gi, "l")
    .replace(/đ/gi, "d")
    .replace(/ħ/gi, "h")
    .replace(/[áàâäãåā]/gi, "a")
    .replace(/[éèêëēėę]/gi, "e")
    .replace(/[íìîïīį]/gi, "i")
    .replace(/[óòôöõøō]/gi, "o")
    .replace(/[úùûüūů]/gi, "u")
    .replace(/[ýÿŷ]/gi, "y")
    .replace(/ñ/gi, "n")
    .replace(/ç/gi, "c")
    .replace(/š/gi, "s")
    .replace(/ž/gi, "z")
    .replace(/ß/gi, "ss");
}

export function localizeNewCity(country, city, locale) {
  const language = languageFor(locale);
  const source = String(city || "").trim();
  if (!source) return "";

  const primary = extractPrimaryLocation(source);
  if (!primary) return "";

  const countryCode = String(country || "").trim().toUpperCase();
  if (language === "ar") {
    const normalizedKey = `${countryCode}|${primary.normalize("NFC").toUpperCase()}`;
    const explicit = ARABIC_LOCALITY_OVERRIDES[normalizedKey];
    if (explicit) return explicit;

    const ascii = asciiLocality(primary);
    const localized = localizeCityName(countryCode, ascii, language);
    if (localized && !/[A-Za-zÀ-ÿÐ-ðÞ-þØ-øŁłĐđ]/u.test(localized)) {
      return localized;
    }

    return localizeCityName(countryCode, ascii, language) || ascii;
  }

  const localized = localizeCityName(countryCode, primary, language);
  return extractPrimaryLocation(localized || primary) || primary;
}

export function normalizedCityKey(country, city) {
  return `${String(country || "").trim().toUpperCase()}|${extractPrimaryLocation(city).normalize("NFC").toUpperCase()}`;
}

export { extractPrimaryLocation };
