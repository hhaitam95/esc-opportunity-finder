#!/usr/bin/env python3

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pycountry
import requests
from bs4 import BeautifulSoup


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://youth.europa.eu"
API_URL = f"{BASE_URL}/api/rest/eyp/v1/search_en"

# Phase 1 public country.
DEFAULT_PARTICIPANT_COUNTRY = "MA"

# Data schemas.
CHECKPOINT_SCHEMA_VERSION = 4
OUTPUT_SCHEMA_VERSION = 4

# Active detail pages are rechecked at most once per day.
DETAIL_RECHECK_INTERVAL = 24 * 60 * 60

# API.
# Keep the list request modest and paginated. This is deliberately separate
# from the detail-page BATCH_SIZE below.
API_PAGE_SIZE = 1000

# Detail scanning.
BATCH_SIZE = 40
DETAIL_REQUEST_DELAY = 5.0
DETAIL_SCAN_COOLDOWN = 10.0

# HTTP.
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3
MAX_RATE_LIMIT_WAIT = 120

# Archive.
MAX_ARCHIVED_OPPORTUNITIES = 30
