#!/usr/bin/env python3
"""V4 final verification wrapper.

Loads the V4 collector policy so Entertainment specialist sources are trusted, keeps
specialist-refined surfaces from being second-guessed by the legacy generic classifier,
finalizes verified Entertainment GUIDs and Underreported cross-links, and applies the
conservative cross-tab duplicate guard.
"""
import re
import sys

import classify_live_feed as classifier
import update_news_v4 as v4

_base_source_is_trusted = v4.core.source_is_trusted


def v4_source_is_trusted(source):
    """Use the production trust policy plus legacy specialist-source compatibility."""
    tokens = set(re.findall(r"[a-z0-9]+", (source or "").lower()))
    if tokens & {"xbiz", "avn"}:
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
