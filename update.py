#!/usr/bin/env python3
"""Read-only local validation for ESC Opportunity Finder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    print("=" * 72)
    print("ESC Opportunity Finder — project validation")
    print("=" * 72)

    required = [
        ROOT / ".github" / "workflows" / "update.yml",
        ROOT / ".github" / "workflows" / "deploy.yml",
        ROOT / ".github" / "workflows" / "health.yml",
        ROOT / "data" / "checkpoint.json",
        ROOT / "data" / "opportunities.json",
        ROOT / "data" / "expired.json",
        ROOT / "scraper" / "run.py",
        ROOT / "scraper" / "scraper.py",
        ROOT / "scraper" / "prune_expired.py",
        ROOT / "scraper" / "validate_published.py",
        ROOT / "web" / "index.html",
        ROOT / "web" / "app.js",
        ROOT / "web" / "data-provider.js",
        ROOT / "web" / "table.js",
        ROOT / "web" / "style.css",
    ]

    for path in required:
        if not path.exists():
            raise SystemExit(f"ERROR: missing required file: {path.relative_to(ROOT)}")

    print("PASS: repository structure is present.")

    run([
        sys.executable,
        "-m",
        "py_compile",
        "scraper/run.py",
        "scraper/scraper.py",
        "scraper/prune_expired.py",
        "scraper/validate_published.py",
    ])
    print("PASS: Python sources compile.")

    run([
        sys.executable,
        "scraper/validate_published.py",
    ])
    print("PASS: published datasets validate.")

    javascript_files = sorted(
        (ROOT / "web").glob("*.js")
    ) + sorted(
        (ROOT / "web" / "features").glob("*.js")
    )

    if not javascript_files:
        raise SystemExit("ERROR: no frontend JavaScript files found.")

    for path in javascript_files:
        run(["node", "--check", str(path.relative_to(ROOT))])

    print("PASS: frontend JavaScript syntax validates.")
    print("PASS: project validation complete.")


if __name__ == "__main__":
    main()
