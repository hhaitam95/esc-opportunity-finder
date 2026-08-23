# ESC Opportunity Finder

A lightweight, static website for discovering European Solidarity Corps (ESC) volunteering opportunities from the European Youth Portal.

The project is designed to run unattended through GitHub Actions: the scraper refreshes the dataset every 30 minutes, publishes validated JSON, and a successful update automatically deploys the website to GitHub Pages.

## How it works

```text
European Youth Portal API
        |
        v
scraper/run.py
        |
        +--> data/checkpoint.json
        +--> data/opportunities.json
        +--> data/expired.json
        |
        v
scraper/validate_published.py
        |
        v
Git commit + push
        |
        v
Deploy ESC Website workflow
        |
        v
GitHub Pages
```

The browser does not scrape the European Youth Portal. It loads the published JSON dataset and performs participant-country filtering, searching, sorting, localization, and presentation entirely client-side.

## Repository layout

```text
.github/workflows/
  update.yml              Scheduled scraper + publication workflow
  deploy.yml              GitHub Pages deployment
  health.yml              Freshness / autopilot health check

data/
  checkpoint.json         Persistent scraper state; do not edit manually
  opportunities.json      Published active opportunities
  expired.json            Seven-day recently-expired dataset

scraper/
  scraper.py              Canonical scraper and checkpoint logic
  run.py                  Production entry point with urgent rechecks
  prune_expired.py        Seven-day expired-data pruning
  validate_published.py   Shared production data validator
  test_archive.py         Archive behavior tests

web/
  index.html              Website shell
  app.js                  Application state and UI orchestration
  data-provider.js        Published-data loading and defensive filtering
  table.js                Opportunity rendering, localization and formatting
  table-sort.js           Clickable table-header sorting
  country.js              Participant-country filtering helpers
  state.js                Frontend state management
  features/               Language and theme modules
  style.css               Main stylesheet
  ui-fixes.css            Targeted UI fixes

update.py                 Maintainer/development guardrail script
AUTOPILOT.md              Six-month maintenance and recovery guide
```

## Automatic operation

`update.yml` runs every 30 minutes. It retrieves the authoritative opportunity list, incrementally checks detail pages using the persistent checkpoint, validates the resulting datasets, and commits changed data.

A successful data update triggers `deploy.yml`. The deployment workflow validates the published data again before deploying the `web/` directory to GitHub Pages.

`health.yml` runs hourly and checks that the scraper has successfully produced a recent dataset. A stale or broken pipeline therefore becomes an explicit GitHub Actions failure instead of silently serving old data forever.

See [`AUTOPILOT.md`](AUTOPILOT.md) for the intended long-term operating procedure.

## Data rules

An opportunity is **active** when:

- it has a deadline that has not passed, or
- it has no deadline and its activity end date has not passed.

An opportunity is **recently expired** only when:

- its deadline passed within the last seven days, or
- it has no deadline and its activity end date passed within the last seven days.

Future-dated opportunities must never appear in the expired table.

## NEW badge behavior

`data/opportunities.json` contains both `generated_at` and `new_opportunity_ids`.

The `NEW` badge is tied to that dataset version. A newly discovered opportunity keeps its badge for the lifetime of that published dataset version. When the next successful update changes `generated_at`, the previous NEW state is replaced by the new update's `new_opportunity_ids`.

The badge does not depend on browser storage, cookies, or a per-device timer.

## Languages and UI

The website supports:

- English
- French
- Arabic with RTL layout

It includes participant-country selection, translated country names and flags, active/expired tables, live deadline countdowns, activity duration labels, clickable column sorting, dark mode, responsive layout, and defensive expiry filtering.

## Development

### Requirements

Python 3.11 or newer is recommended. The scraper uses:

- `requests`
- `beautifulsoup4`
- `pycountry`

Install them with:

```bash
python -m pip install requests beautifulsoup4 pycountry
```

### Validate the scraper

```bash
python -m py_compile scraper/run.py scraper/scraper.py scraper/prune_expired.py scraper/validate_published.py
```

The production validator can be run against the checked-in datasets with:

```bash
python scraper/validate_published.py
```

### Production scraper

```bash
python scraper/run.py
```

The scraper is intentionally resumable. Do not delete or manually edit `data/checkpoint.json` unless you are deliberately performing a recovery operation and understand the checkpoint schema.

## Maintainer tooling

`update.py` is a development/maintenance guardrail for controlled repository changes. It is not required by the GitHub Actions runtime and should not be confused with `.github/workflows/update.yml`, which is the production data-update workflow.

## Source and disclaimer

Opportunity data is sourced from the European Youth Portal. The website is an independent convenience interface and does not replace the official opportunity page. Users should always open the official ESC opportunity page and verify the current details before applying.
