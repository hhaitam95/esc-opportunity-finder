import { localizeNewCity } from "./city-localizations.js";

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

function extractPrimaryLocality(value) {
  let text = clean(value);
  if (!text) return "";

  // Remove postal-code prefixes and obvious country suffixes.
  text = text.replace(/^\d{4,6}\s*[-–]\s*/u, "");
  text = text.replace(/,?\s+(?:Italy|Italia|France|Germany|Deutschland|Spain|España|Portugal|Poland|Polska|Czechia|Türkiye|Turkey|Bolivia|Senegal|Romania|Nederland|Netherlands|Armenia|Georgia)$/iu, "");
  text = clean(text);

  // When EYP stores a sentence instead of a place, take the first place after the
  // location phrase. The rest of the sentence is intentionally discarded.
  const sentence = text.match(/\b(?:living in|will be living in|based in|located in)\s+(.+?)(?:\s+\([^)]*\))?(?:\s+and\s+(?:work|working)\s+in\s+[^.;]+)?[.;]?$/iu);
  if (sentence?.[1]) text = clean(sentence[1]);

  // Street/address strings are not city names. Prefer the final meaningful segment,
  // which is normally the locality in an address-like value.
  if (/\b(?:via|viale|rue|avenue|av\.?|boulevard|blvd\.?|street|st\.?|road|rd\.?|lane|ln\.?|straße|strasse|strada)\b/iu.test(text)) {
    const addressParts = text.split(/\s*,\s*/u).map(clean).filter(Boolean);
    if (addressParts.length > 1) text = addressParts[addressParts.length - 1];
  }

  // EYP frequently appends district/region/country details after commas or slashes.
  // The first meaningful segment is the primary locality for this compact table.
  const parts = text
    .split(/\s*\/\s*|\s*;\s*|\s*,\s*/u)
    .map(clean)
    .filter(Boolean);
  if (parts.length > 1) text = parts[0];

  // Collapse common neighbourhood/administrative detail attached to a city.
  text = text.replace(/^(Praha|Prague)\s+\d+(?:\s*[-–].*)?$/iu, "$1");
  text = text.replace(/^(Paris|Dublin|Berlin|Hamburg|Munich|München)\s+\d+$/iu, "$1");
  text = text.replace(/\s+\([^)]*\)$/u, "").trim();
  text = text.replace(/\s+-\s+(?:Nová Ves|Stodůlky|Stodulky)$/iu, "").trim();

  return clean(text);
}

export function formatPrimaryLocation(country, town, location, locale) {
  const source = String(town || location || "").trim();
  const primary = extractPrimaryLocality(source);
  if (!primary) return "";

  // Delegate the actual FR/AR city naming to the established localization map.
  // This means known names retain their correct exonyms/transliterations, while
  // unseen future localities still use the existing safe fallback.
  return localizeNewCity(String(country || "").trim().toUpperCase(), primary, locale);
}

export { extractPrimaryLocality };
