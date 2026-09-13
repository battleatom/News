#!/usr/bin/env bash
# Applied in CI to a disposable copy of the V4 feed before V5 audit/tests.
python scripts/cross_tab_integrity_fast.py --apply --report /tmp/v5-cross-tab.json
python scripts/enforce_editorial_integrity.py
# Rank the existing Underreported pool deterministically in per-fix CI. Discovery and
# network enrichment remain final-build stages so regressions do not depend on live web responses.
python scripts/underreported_priority.py --rank
python scripts/update_why_matters.py
