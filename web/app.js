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

const state = createState();

const dom = {
  participantCountry: document.getElementById("participant-country"),
  applyParticipantCountry: document.getElementById("apply-participant-country"),
  clearFilters: document.getElementById("clear-filters"),
  searchInput: document.getElementById("search-input"),
  countryFilter: document.getElementById("country-filter"),
  typeFilter: document.getElementById("type-filter"),
  sortSelect: document.getElementById("sort-select"),
  newOpportunitiesSection: document.getElementById("new-opportunities-section"),
  newOpportunitiesToggle: document.getElementById("new-opportunities-toggle"),
  newOpportunitiesBody: document.getElementById("new-opportunities-body"),
  newOpportunityCount: document.getElementById("new-opportunity-count"),
  newOpportunitiesContent: document.getElementById("new-opportunities-content"),
  newOpportunitiesArrow: document.getElementById("new-opportunities-arrow"),
  activeToggle: document.getElementById("active-toggle"),
  activeContent: document.getElementById("active-content"),
  activeArrow: document.getElementById("active-arrow"),
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
  placeholder.selected = !selected;
  dom.participantCountry.appendChild(placeholder);

  countries
    .map((code) => displayCountry(code, locale()))
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((country) => {
      const option = document.createElement("option");
      option.value = country.code;
      option.textContent = `${country.flag} ${country.name}`;
      option.selected = selected === country.code;
      dom.participantCountry.appendChild(option);
    });

  dom.participantCountry.value = selected && countries.includes(selected) ? selected : "";
}

function populateTableFilters() {
  const active = activeForParticipantCountry();
  if (dom.countryFilter && enabled("filters")) {
    const countries = [...new Set(active.map((item) => normalizeCountryCode(item.country)).filter(Boolean))].sort();
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
    const types = [...new Set(active.map((item) => String(item.activity_type || "").trim()).filter(Boolean))].sort();
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

function isNewOpportunity(opportunity) {
  const id = String(opportunity.id ?? opportunity.opid ?? "").trim();
  return Boolean(id && state.data?.newIds?.has(id));
}

function newOpportunitiesFrom(results) {
  return sortRows(results.filter(isNewOpportunity), "created");
}

function renderNewOpportunities(results) {
  if (!dom.newOpportunitiesSection || !dom.newOpportunitiesBody) return;

  const newest = state.participantSearchApplied && enabled("newBadges")
    ? newOpportunitiesFrom(results)
    : [];

  if (!newest.length) {
    dom.newOpportunitiesBody.innerHTML = "";
    if (dom.newOpportunityCount) {
      dom.newOpportunityCount.textContent = "0";
      dom.newOpportunityCount.removeAttribute("aria-label");
    }
    show(dom.newOpportunitiesSection, false);
    return;
  }

  if (dom.newOpportunityCount) {
    dom.newOpportunityCount.textContent = String(newest.length);
    dom.newOpportunityCount.setAttribute("aria-label", `${newest.length} new opportunities`);
  }

  show(dom.newOpportunitiesSection, true);
  dom.newOpportunitiesBody.innerHTML = renderRows(newest, {
    archived: false,
    newIds: state.data?.newIds || new Set(),
    locale: locale(),
    t,
  });
  window.normalizeCountryDisplay?.(dom.newOpportunitiesBody);
  window.updateRelativeDeadlineLabels?.();
}

function renderActive() {
  if (!state.participantSearchApplied) {
    dom.opportunitiesBody.innerHTML = "";
    renderCounts(0);
    renderNewOpportunities([]);
    show(dom.emptyMessage, false);
    return;
  }

  const results = filteredActive();
  renderCounts(results.length);
  dom.opportunitiesBody.innerHTML = renderRows(results, {
    archived: false,
    newIds: state.data?.newIds || new Set(),
    locale: locale(),
    t,
  });
  renderNewOpportunities(results);
  window.normalizeCountryDisplay?.(dom.opportunitiesBody);
  window.updateRelativeDeadlineLabels?.();
  show(dom.emptyMessage, results.length === 0);
}

function renderArchived() {
  const results = archivedForParticipantCountry();
  if (!state.participantSearchApplied || !results.length) {
    show(dom.expiredSection, false);
    return;
  }
  show(dom.expiredSection, true);
  if (dom.expiredCount) dom.expiredCount.textContent = String(results.length);
  dom.expiredBody.innerHTML = renderRows(sortRows(results, "expired"), {
    archived: true,
    newIds: new Set(),
    locale: locale(),
    t,
  });
  window.normalizeCountryDisplay?.(dom.expiredBody);
}

function setSectionExpanded(toggle, content, arrow, expanded) {
  if (!toggle || !content) return;
  toggle.setAttribute("aria-expanded", String(expanded));
  content.classList.toggle("hidden", !expanded);
  if (arrow) arrow.textContent = expanded ? "⌃" : "⌄";
}

function bindCollapsibleSection(toggle, content, arrow) {
  if (!toggle || !content || toggle.dataset.collapsibleBound === "true") return;
  toggle.dataset.collapsibleBound = "true";
  toggle.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    setSectionExpanded(toggle, content, arrow, !expanded);
  });
}

function bindCollapsibleSections() {
  bindCollapsibleSection(dom.newOpportunitiesToggle, dom.newOpportunitiesContent, dom.newOpportunitiesArrow);
  bindCollapsibleSection(dom.activeToggle, dom.activeContent, dom.activeArrow);
  bindCollapsibleSection(dom.expiredToggle, dom.expiredContent, dom.expiredArrow);
}

function renderAll() {
  populateParticipantCountries();
  populateTableFilters();
  renderActive();
  renderArchived();
  updateLastUpdated();
}

function applyParticipantSearch() {
  const country = normalizeCountryCode(dom.participantCountry?.value || "");
  setParticipantCountry(state, country);
  renderAll();
}

function clearFiltersAndRender() {
  clearTableFilters(state);
  if (dom.searchInput) dom.searchInput.value = "";
  renderAll();
}

function handleLanguageChange() {
  populateParticipantCountries();
  populateTableFilters();
  renderAll();
}

function handleSearchInput() {
  if (searchRenderTimer) window.clearTimeout(searchRenderTimer);
  searchRenderTimer = window.setTimeout(renderAll, 120);
}

function handleFilterChange() {
  state.filters.country = dom.countryFilter?.value || "";
  state.filters.type = dom.typeFilter?.value || "";
  state.filters.sort = dom.sortSelect?.value || "deadline";
  renderAll();
}

async function initialize() {
  show(dom.loadingMessage, true);
  show(dom.errorMessage, false);

  let data;
  try {
    data = await loadData();
  } catch (error) {
    console.error("ESC opportunity data load failed:", error);
    show(dom.loadingMessage, false);
    show(dom.errorMessage, true);
    return;
  }

  state.data = data;
  updateLastUpdated();

  try {
    initTheme(t);
    initLanguage(handleLanguageChange);
    bindCollapsibleSections();
    renderAll();
    show(dom.errorMessage, false);
  } catch (error) {
    console.error("ESC Opportunity Finder UI initialization failed:", error);
    renderCounts(0);
    show(dom.newOpportunitiesSection, false);
    show(dom.emptyMessage, false);
  } finally {
    show(dom.loadingMessage, false);
  }
}

dom.applyParticipantCountry?.addEventListener("click", applyParticipantSearch);
dom.clearFilters?.addEventListener("click", clearFiltersAndRender);
dom.searchInput?.addEventListener("input", handleSearchInput);
dom.countryFilter?.addEventListener("change", handleFilterChange);
dom.typeFilter?.addEventListener("change", handleFilterChange);
dom.sortSelect?.addEventListener("change", handleFilterChange);

initialize();
