const DEFAULT_FILTERS = Object.freeze({
  search: "",
  country: "",
  type: "",
  sort: "deadline",
});

export function createState() {
  return {
    data: null,
    selectedParticipantCountry: "",
    participantSearchApplied: false,
    filters: {
      ...DEFAULT_FILTERS,
    },
  };
}

export function setParticipantCountry(
  state,
  value,
) {
  state.selectedParticipantCountry =
    value || "";

  state.participantSearchApplied =
    Boolean(value);

  resetFilters(state);
}

export function resetFilters(state) {
  state.filters = {
    ...DEFAULT_FILTERS,
  };
}

export function clearTableFilters(state) {
  resetFilters(state);
}
