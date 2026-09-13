#!/usr/bin/env bash
# Applied in CI to a disposable copy of the V4 feed before V5 audit/tests.
python scripts/cluster_related_coverage.py
python scripts/cross_tab_integrity_fast.py --apply --report /tmp/v5-cross-tab.json
python scripts/enforce_editorial_integrity.py
python scripts/update_why_matters.py
