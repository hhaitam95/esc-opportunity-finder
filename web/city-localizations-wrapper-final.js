import { localizeNewCity as localizeCityName } from "./city-localizations-original.js";

function clean(value) {
  return String(value || "")
    .replace(/[\u200e\u200f\u202a-\u202e]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[,;:\-–]+|[,;:]+$/gu, "")
    .trim();
}

function extractPrimaryLocation(value) {
  let text = clean(value);
  if (!text) return "";

  text = text.replace(/^\d{4,6}\s*[-–]\s*/u, "");
  text = text.replace(/,?\s+(?:Italy|Italia|France|Germany|Deutschland|Spain|España|Portugal|Poland|Polska|Czechia|Türkiye|Turkey|Bolivia|Senegal|Romania|Nederland|Netherlands|Armenia|Georgia)$/iu, "");
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

export function localizeNewCity(country, city, locale) {
  const primary = extractPrimaryLocation(city);
  if (!primary) return "";
  return localizeCityName(country, primary, locale) || primary;
}

export function normalizedCityKey(country, city) {
  return `${String(country || "").trim().toUpperCase()}|${extractPrimaryLocation(city).toUpperCase()}`;
}

export { extractPrimaryLocation };
