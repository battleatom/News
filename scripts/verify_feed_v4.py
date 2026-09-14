#!/usr/bin/env python3
"""V4 final verification wrapper.

Loads the V4 collector policy so Entertainment and curated specialist sources are
trusted, keeps specialist-refined surfaces from being second-guessed by the legacy
generic classifier, finalizes verified Entertainment GUIDs and Underreported
cross-links, and applies the conservative cross-tab duplicate guard.
"""
import re
import sys

import classify_live_feed as classifier
import refine_tech_gaming as specialist
import update_news_v4 as v4

_base_source_is_trusted = v4.core.source_is_trusted
_SPECIALIST_SOURCES = tuple(dict.fromkeys(
    specialist.TECH_TRUSTED + specialist.GAMING_TRUSTED + specialist.US_TRUSTED
))


def v4_source_is_trusted(source):
    """Use production trust plus sources explicitly curated by specialist refiners."""
    value = re.sub(r"[^a-z0-9]+", " ", (source or "").lower()).strip()
    tokens = set(value.split())
    if tokens & {"xbiz", "avn"}:
        return True
    if any(name in value for name in _SPECIALIST_SOURCES):
        return True
    return _base_source_is_trusted(source)


classifier.source_is_trusted = v4_source_is_trusted
# Entertainment, Technology, Gaming and U.S. are already cleaned by dedicated
# specialist passes before verification. Keep source-trust checks and dedupe here,
# but do not run a second generic category reroute over those curated pools. The
# final V5 authoritative filter still owns the last routing decision.
classifier.NON_ROUTABLE_INPUT = set(classifier.NON_ROUTABLE_INPUT) | {
    "entertainment", "technology", "gaming", "us"
}

import verify_feed

# verify_feed calls classify() from the same module object above, so its final
# source/category decision uses the V4 trust and non-reroute policy.
verify_feed.EDITORIAL_SURFACES = set(verify_feed.EDITORIAL_SURFACES) | {"entertainment"}

if __name__ == "__main__":
    verify_feed.main()

    # The generic verifier intentionally clusters within tabs. Follow it with a
    # conservative cross-tab pass that removes only obvious duplicate copies among
    # ordinary subject tabs, preserving the removed coverage as relatedArticles.
    import cross_tab_integrity_fast
    cross_tab_integrity_fast.run(
        'News',
        'cross-tab-integrity-report.json',
        '--apply' in sys.argv,
    )

    import finalize_entertainment_v4
    finalize_entertainment_v4.main()
