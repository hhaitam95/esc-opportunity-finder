const DATA_BASE =
  "https://raw.githubusercontent.com/"
  + "hhaitam95/esc-opportunity-finder/main/data/";

const RECENTLY_EXPIRED_DAYS = 7;
const NEW_OPPORTUNITY_DISPLAY_WINDOW = 24 * 60 * 60 * 1000;

async function fetchJson(filename) {
  const response = await fetch(
    `${DATA_BASE}${filename}?v=${Date.now()}`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Could not load ${filename} (${response.status})`,
    );
  }

  const payload =
    await response.json();

  if (
    !payload ||
    typeof payload !== "object"
  ) {
    throw new Error(
      `${filename} returned invalid data.`,
    );
  }

  return payload;
}

function normalizeCodes(values) {
  if (!Array.isArray(values)) {
    return [];
  }

  return [
    ...new Set(
      values
        .map(
          (value) =>
            String(value)
              .trim()
              .toUpperCase(),
        )
        .filter(Boolean),
    ),
  ];
}

function normalizeOpportunity(
  opportunity,
) {
  const item = {
    ...opportunity,
  };

  item.id = String(
    item.id ??
    item.opid ??
    item.opportunity_id ??
    item.opportunityId ??
    "",
  ).trim();

  const dates =
    item.activity_dates &&
    typeof item.activity_dates === "object"
      ? item.activity_dates
      : {};

  item.start_date =
    item.start_date ||
    dates.start ||
    "";

  item.end_date =
    item.end_date ||
    dates.end ||
    "";

  item.deadline =
    item.application_deadline ||
    item.deadline ||
    "";

  const deadlineRaw = String(item.deadline).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadlineRaw)) {
    item.deadline = `${deadlineRaw}T23:59:59`;
  }

  item.town =
    item.town ||
    item.city ||
    "";

  item.image_url =
    item.logo_url ||
    item.image_url ||
    "";

  item.participant_countries =
    normalizeCodes(
      Array.isArray(
        item.participant_countries,
      )
        ? item.participant_countries
        : item.eligible_countries,
    );

  item.eligible_countries =
    normalizeCodes(
      item.eligible_countries ||
      item.participant_countries,
    );

  return item;
}

function normalizeList(payload) {
  const list =
    Array.isArray(
      payload?.opportunities,
    )
      ? payload.opportunities
      : [];

  return list
    .filter(
      (item) =>
        item &&
        typeof item === "object",
    )
    .map(
      normalizeOpportunity,
    );
}

function parseDateOnlyOrValue(value, endOfDay = false) {
  if (!value) {
    return null;
  }

  const raw = String(value).trim();
  const date = /^\d{4}-\d{2}-\d{2}$/.test(raw)
    ? new Date(
        `${raw}T${endOfDay ? "23:59:59" : "00:00:00"}`,
      )
    : new Date(raw);

  return Number.isNaN(date.getTime())
    ? null
    : date;
}

function deadlineHasPassed(opportunity) {
  if (!opportunity.deadline) {
    return false;
  }

  const deadline = parseDateOnlyOrValue(
    opportunity.deadline,
    true,
  );

  return Boolean(
    deadline &&
    deadline.getTime() < Date.now(),
  );
}

function activityHasEnded(opportunity) {
  if (!opportunity.end_date) {
    return false;
  }

  const endDate = parseDateOnlyOrValue(
    opportunity.end_date,
    true,
  );

  return Boolean(
    endDate &&
    endDate.getTime() < Date.now(),
  );
}

function shouldArchive(opportunity) {
  if (deadlineHasPassed(opportunity)) {
    return true;
  }

  if (!opportunity.deadline) {
    return activityHasEnded(opportunity);
  }

  return false;
}

function recentlyExpired(opportunity) {
  const expiry = opportunity.deadline || opportunity.end_date;
  const expiryDate = parseDateOnlyOrValue(expiry, true);

  if (!expiryDate) {
    return false;
  }

  const age = Date.now() - expiryDate.getTime();
  const maxAge = RECENTLY_EXPIRED_DAYS * 24 * 60 * 60 * 1000;

  return age >= 0 && age <= maxAge;
}

function validRecentlyExpired(opportunity) {
  return shouldArchive(opportunity) && recentlyExpired(opportunity);
}

function mergeArchived(
  archived,
  expiredFromActive,
) {
  const merged = [];
  const seen = new Set();

  for (const opportunity of [
    ...archived,
    ...expiredFromActive,
  ]) {
    if (!validRecentlyExpired(opportunity)) {
      continue;
    }

    const id = String(
      opportunity.id || "",
    ).trim();

    if (id && seen.has(id)) {
      continue;
    }

    if (id) {
      seen.add(id);
    }

    merged.push(opportunity);
  }

  return merged;
}

function isRecentlyCreated(opportunity) {
  const created = parseDateOnlyOrValue(
    opportunity.created,
    false,
  );

  if (!created) {
    return false;
  }

  const age = Date.now() - created.getTime();
  return age >= 0 && age <= NEW_OPPORTUNITY_DISPLAY_WINDOW;
}

export async function loadData() {
  const [activeResult, expiredResult] = await Promise.allSettled([
    fetchJson("opportunities.json"),
    fetchJson("expired.json"),
  ]);

  if (activeResult.status === "rejected") {
    throw activeResult.reason instanceof Error
      ? activeResult.reason
      : new Error(String(activeResult.reason));
  }

  const activePayload = activeResult.value;
  const expiredPayload = expiredResult.status === "fulfilled"
    ? expiredResult.value
    : { opportunities: [] };

  if (expiredResult.status === "rejected") {
    console.warn("Could not load expired opportunities; continuing with active data.", expiredResult.reason);
  }

  const rawActive =
    normalizeList(
      activePayload,
    );

  const archived =
    normalizeList(
      expiredPayload,
    );

  if (!rawActive.length) {
    throw new Error(
      "Active opportunity dataset is empty.",
    );
  }

  const active = [];
  const expiredFromActive = [];

  for (const opportunity of rawActive) {
    if (shouldArchive(opportunity)) {
      expiredFromActive.push(opportunity);
    } else {
      active.push(opportunity);
    }
  }

  const newIds =
    new Set(
      Array.isArray(
        activePayload.new_opportunity_ids,
      )
        ? activePayload.new_opportunity_ids.map(
            (value) =>
              String(value),
          )
        : [],
    );

  // Defensive frontend fallback: EYP's `created` timestamp identifies
  // opportunities that entered the source dataset within the last 24 hours.
  // Union this with backend NEW IDs so a backend tracking hiccup cannot hide
  // genuinely recent opportunities from users.
  for (const opportunity of active) {
    if (isRecentlyCreated(opportunity)) {
      const id = String(opportunity.id || "").trim();
      if (id) newIds.add(id);
    }
  }

  return {
    active,
    archived: mergeArchived(
      archived,
      expiredFromActive,
    ),
    newIds,
    generatedAt:
      activePayload.generated_at ||
      null,
  };
}
