#!/usr/bin/env bash
# Applied in CI to a disposable copy of the V4 feed before V5 audit/tests.
# Full event clustering is covered by its focused regression and runs in the final build;
# per-fix CI uses the fast conservative cross-tab pass to avoid redundant O(n²)-style work.
python scripts/cross_tab_integrity_fast.py --apply --report /tmp/v5-cross-tab.json
python scripts/enforce_editorial_integrity.py
python scripts/update_why_matters.py
