#!/usr/bin/env bash
# Applied in CI to a disposable copy of the V4 feed/site before V5 audit/tests.
python scripts/cross_tab_integrity_fast.py --apply --report /tmp/v5-cross-tab.json
python scripts/enforce_editorial_integrity.py
python scripts/underreported_priority.py --rank
python scripts/update_why_matters.py
python scripts/patch_v25_location_content.py
python scripts/patch_nfl_streaming.py
