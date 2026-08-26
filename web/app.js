import { enabled } from "./features.js";

import {
  createState,
  setParticipantCountry,
  clearTableFilters,
} from "./state.js";

import {
  initLanguage,
  locale,
  t,
} from "./features/i18n.js";

import {
  initTheme,
  updateThemeControl,
} from "./features/theme.js";

import {
  loadData,
} from "./data-provider.js";

import {
  collectParticipantCountries,
  displayCountry,
  matchesParticipantCountry,
  normalizeCountryCode,
} from "./country.js";

import {
  filterRows,
  sortRows,
  renderRows,
} from "./table.js";

import { localizeNewCity } from "./city-localizations.js";

const state = createState();

const dom = {
  participantCountry: document.getElementById("participant-country"),
  applyParticipantCountry: document.getElementById("apply-participant-country"),
  clearFilters: document.getElementById("clear-filters"),
  searchInput: document.getElementById("search-input"),
  countryFilter: document.getElementById("country-filter"),
  typeFilter: document.getElementById("type-filter"),
  sortSelect: document.getElementById("sort-select"),
  opportunitiesBody: document.getElementById("opportunities-body"),
  opportunityCount: document.getElementById("opportunity-count"),
  activeResultCount: document.getElementById("active-result-count"),
  lastUpdated: document.getElementById("last-updated"),
  emptyMessage: document.getElementById("empty-message"),
  loadingMessage: document.getElementById("loading-message"),
  errorMessage: document.getElementById("error-message"),
  expiredSection: document.getElementById("expired-section"),
  expiredBody: document.getElementById("expired-body"),
  expiredCount: document.getElementById("expired-count"),
  expiredToggle: document.getElementById("expired-toggle"),
  expiredContent: document.getElementById("expired-content"),
  expiredArrow: document.getElementById("expired-arrow"),
};

let searchRenderTimer = null;
let lastRenderedSearch = "";
let lastRenderedState = null;

function show(element, value) {
  element?.classList.toggle("hidden", !value);
}

function activeForParticipantCountry() {
  if (!state.data || !state.participantSearchApplied) return [];
  return state.data.active.filter((opportunity) =>
    matchesParticipantCountry(opportunity, state.selectedParticipantCountry),
  );
}

function archivedForParticipantCountry() {
  if (!state.data || !state.participantSearchApplied) return [];
  return state.data.archived.filter((opportunity) =>
    matchesParticipantCountry(opportunity, state.selectedParticipantCountry),
  );
}

function updateLastUpdated() {
  if (!dom.lastUpdated) return;

  const value = state.data?.generatedAt;
  if (!value) {
    dom.lastUpdated.textContent = "—";
    return;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    dom.lastUpdated.textContent = String(value);
    return;
  }

  dom.lastUpdated.textContent = new Intl.DateTimeFormat(locale(), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function renderCounts(count) {
  const text = count === 1 ? `1 ${t("result")}` : `${count} ${t("results")}`;
  if (dom.opportunityCount) dom.opportunityCount.textContent = text;
  if (dom.activeResultCount) dom.activeResultCount.textContent = text;
}

function populateParticipantCountries() {
  if (!enabled("participantCountry") || !dom.participantCountry || !state.data) return;

  const countries = collectParticipantCountries([
    ...state.data.active,
    ...state.data.archived,
  ]);

  const selected = normalizeCountryCode(state.selectedParticipantCountry);

  dom.participantCountry.replaceChildren();

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = t("selectParticipantCountry");
  dom.participantCountry.appendChild(placeholder);

  countries
    .map((code) => displayCountry(code, locale()))
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((country) => {
      const option = document.createElement("option");
      option.value = country.code;
      option.textContent = `${country.flag} ${country.name}`;
      dom.participantCountry.appendChild(option);
    });

  if (selected && countries.includes(selected)) {
    dom.participantCountry.value = selected;
  }
}

function populateTableFilters() {
  const active = activeForParticipantCountry();

  if (dom.countryFilter && enabled("filters")) {
    const countries = [
      ...new Set(
        active
          .map((item) => normalizeCountryCode(item.country))
          .filter(Boolean),
      ),
    ].sort();

    dom.countryFilter.replaceChildren();

    const all = document.createElement("option");
    all.value = "";
    all.textContent = t("allCountries");
    dom.countryFilter.appendChild(all);

    countries.forEach((code) => {
      const display = displayCountry(code, locale());
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${display.flag} ${display.name}`;
      dom.countryFilter.appendChild(option);
    });

    dom.countryFilter.value = state.filters.country;
  }

  if (dom.typeFilter && enabled("filters")) {
    const types = [
      ...new Set(
        active
          .map((item) => String(item.activity_type || "").trim())
          .filter(Boolean),
      ),
    ].sort();

    dom.typeFilter.replaceChildren();

    const all = document.createElement("option");
    all.value = "";
    all.textContent = t("allTypes");
    dom.typeFilter.appendChild(all);

    types.forEach((type) => {
      const option = document.createElement("option");
      option.value = type;
      option.textContent = type;
      dom.typeFilter.appendChild(option);
    });

    dom.typeFilter.value = state.filters.type;
  }

  window.translateTypeFilter?.();
}

function filteredActive() {
  let results = activeForParticipantCountry();
  if (enabled("filters")) results = filterRows(results, state.filters);
  if (enabled("sorting")) results = sortRows(results, state.filters.sort);
  return results;
}

function prepareRowsForDisplay(opportunities) {
  return opportunities.map((opportunity) => {
    const town = String(opportunity.town || "").trim();
    if (!town) return opportunity;

    const country = String(opportunity.country || "").trim().toUpperCase();
    const localizedTown = localizeNewCity(country, town, locale());
    if (!localizedTown || localizedTown === town) return opportunity;

    return { ...opportunity, town: localizedTown };
  });
}

function renderActive() {
  if (!state.participantSearchApplied) {
    dom.opportunitiesBody.innerHTML = "";
    renderCounts(0);
    show(dom.emptyMessage, false);
    return;
  }

  const results = filteredActive();
  renderCounts(results.length);

  if (!results.length) {
    dom.opportunitiesBody.innerHTML = "";
    show(dom.emptyMessage, true);
    return;
  }

  show(dom.emptyMessage, false);
  dom.opportunitiesBody.innerHTML = renderRows(prepareRowsForDisplay(results), {
    archived: false,
    newIds: enabled("newBadges") ? (state.data?.newIds || new Set()) : new Set(),
    locale: locale(),
    t,
  });

  window.normalizeCountryDisplay?.(dom.opportunitiesBody);
  window.updateRelativeDeadlineLabels?.();
}

function renderArchived() {
  if (!enabled("archives") || !state.participantSearchApplied) {
    show(dom.expiredSection, false);
    return;
  }

  const results = archivedForParticipantCountry();
  if (!results.length) {
    show(dom.expiredSection, false);
    return;
  }

  show(dom.expiredSection, true);
  if (dom.expiredCount) dom.expiredCount.textContent = String(results.length);

  dom.expiredBody.innerHTML = renderRows(prepareRowsForDisplay(results), {
    archived: true,
    newIds: new Set(),
    locale: locale(),
    t,
  });

  window.normalizeCountryDisplay?.(dom.expiredBody);
  window.updateRelativeDeadlineLabels?.();
}

function renderAll(force = false) {
  const signature = JSON.stringify({
    participant: state.selectedParticipantCountry,
    applied: state.participantSearchApplied,
    search: state.filters.search,
    country: state.filters.country,
    type: state.filters.type,
    sort: state.filters.sort,
    language: locale(),
  });

  if (!force && signature === lastRenderedState) return;
  lastRenderedState = signature;

  updateLastUpdated();
  renderActive();
  renderArchived();
  window.refreshTableSort?.();
}

function applyParticipantCountry() {
  const value = normalizeCountryCode(dom.participantCountry?.value);
  setParticipantCountry(state, value);
  populateTableFilters();
  renderAll(true);
}

function clearFilters() {
  clearTableFilters(state);

  if (searchRenderTimer) {
    clearTimeout(searchRenderTimer);
    searchRenderTimer = null;
  }

  if (dom.searchInput) dom.searchInput.value = "";
  if (dom.countryFilter) dom.countryFilter.value = "";
  if (dom.typeFilter) dom.typeFilter.value = "";
  if (dom.sortSelect) dom.sortSelect.value = "deadline";

  lastRenderedSearch = "";
  populateTableFilters();
  renderAll(true);
}

function scheduleSearchRender() {
  if (!dom.searchInput) return;

  const value = dom.searchInput.value;
  state.filters.search = value;

  if (searchRenderTimer) clearTimeout(searchRenderTimer);
  if (value === lastRenderedSearch) return;

  searchRenderTimer = setTimeout(() => {
    searchRenderTimer = null;
    lastRenderedSearch = state.filters.search;
    renderAll(true);
  }, 180);
}

function bindEvents() {
  dom.applyParticipantCountry?.addEventListener("click", applyParticipantCountry);
  dom.clearFilters?.addEventListener("click", clearFilters);
  dom.searchInput?.addEventListener("input", scheduleSearchRender);

  dom.countryFilter?.addEventListener("change", () => {
    state.filters.country = dom.countryFilter.value;
    renderAll(true);
  });

  dom.typeFilter?.addEventListener("change", () => {
    state.filters.type = dom.typeFilter.value;
    renderAll(true);
  });

  dom.sortSelect?.addEventListener("change", () => {
    state.filters.sort = dom.sortSelect.value;
    renderAll(true);
  });

  dom.expiredToggle?.addEventListener("click", () => {
    const hidden = dom.expiredContent.classList.contains("hidden");
    dom.expiredContent.classList.toggle("hidden", !hidden);
    dom.expiredArrow?.classList.toggle("open", hidden);
    dom.expiredToggle?.setAttribute("aria-expanded", hidden ? "true" : "false");
  });
}

async function initialize() {
  show(dom.loadingMessage, true);
  show(dom.errorMessage, false);

  try {
    state.data = await loadData();
    populateParticipantCountries();
    state.participantSearchApplied = false;
    populateTableFilters();
    renderAll(true);
  } catch (error) {
    console.error("Could not load frontend data:", error);
    show(dom.errorMessage, true);
    if (dom.lastUpdated) dom.lastUpdated.textContent = "—";
    if (dom.opportunitiesBody) dom.opportunitiesBody.innerHTML = "";
  } finally {
    show(dom.loadingMessage, false);
  }
}

initLanguage(() => {
  populateParticipantCountries();
  populateTableFilters();
  renderAll(true);
  updateThemeControl(t);
  window.translateTypeFilter?.();
  window.refreshTableSort?.();
  window.normalizeCountryDisplay?.();
  window.updateRelativeDeadlineLabels?.();
});

initTheme(t);
bindEvents();
initialize();
