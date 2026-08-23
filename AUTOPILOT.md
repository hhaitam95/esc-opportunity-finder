# ESC Opportunity Finder — Autopilot Operations

This repository is designed to run unattended through GitHub Actions.

## Normal operation

- `update.yml` runs every 30 minutes at minutes 07 and 37 UTC.
- The scraper reads the European Youth Portal API, performs incremental detail checks, and persists its checkpoint.
- `data/opportunities.json` is the published active dataset.
- `data/expired.json` contains only the recently expired window.
- A successful data update triggers `deploy.yml`, which validates the published data and deploys GitHub Pages.
- `health.yml` runs hourly at minute 17 UTC and fails if there has not been a successful scraper run within two hours.

The schedule deliberately avoids minute 00 and 30 to reduce the chance of GitHub Actions schedule contention.

## Data rules

An opportunity is active when:

- it has a deadline that has not passed, or
- it has no deadline and its activity end date has not passed.

An opportunity is recently expired only when:

- its deadline passed within the last 7 days, or
- it has no deadline and its activity end date passed within the last 7 days.

Future-dated records must never appear in the expired dataset.

## NEW badge

`new_opportunity_ids` belongs to the same published dataset version as `generated_at`.

A NEW badge therefore remains visible for that dataset version and disappears on the next successful update when `generated_at` changes. No browser `localStorage` or per-device timer controls the badge.

Failed workflow runs do not publish a new dataset version.

## Validation and recovery

Every scraper run validates:

- Python source syntax
- installed dependencies
- active and expired JSON structure
- required opportunity fields
- duplicate IDs
- active/expired date classification
- seven-day expired retention
- dataset freshness
- `new_opportunity_ids` consistency
- browser JavaScript syntax

The Pages deployment repeats the published-data and JavaScript validation before deployment.

If the health workflow fails, inspect the failed `Update ESC Opportunities` run first. Do not edit `data/checkpoint.json` manually.

## Notifications

GitHub can notify the workflow owner when scheduled Actions runs fail. For unattended operation, enable Actions notifications and select **Only notify for failed workflows** for this repository.

The `health.yml` monitor is intentionally separate from the scraper so a scraper that silently stops scheduling is still detected and generates a workflow failure.

## Six-month maintenance

Approximately every six months:

1. Open the Actions tab and confirm recent `Update ESC Opportunities`, `Deploy ESC Website`, and `ESC Opportunity Finder Health` runs are green.
2. Open the website and verify that the opportunity count, last-updated timestamp, filters, language switcher, dark mode, NEW badges, and Recently expired section render correctly.
3. Check that the European Youth Portal still exposes the same public opportunity pages and API behavior.
4. Review GitHub Actions warnings for any action-version deprecations.

No routine manual data refresh is required.
