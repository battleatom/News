#!/usr/bin/env bash
# Build a deterministic V5 candidate from the frozen V4 feed/site.
# Route/filter first, then dedupe the final categories so reroutes cannot create
# second-pass differences in the canonical preview.
python scripts/enforce_editorial_integrity.py
python scripts/enforce_tab_quality_v5.py
python scripts/cross_tab_integrity_fast.py --apply --report /tmp/v5-cross-tab.json
python scripts/underreported_priority.py --rank
python scripts/update_why_matters.py
# One canonical build now owns every UI mutation, including location, NFL streaming,
# system health and Entertainment wiring.
python scripts/build_site.py
