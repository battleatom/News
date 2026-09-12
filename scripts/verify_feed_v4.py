#!/usr/bin/env python3
"""V4 final verification wrapper.

Loads the V4 collector policy so Entertainment specialist sources are trusted, keeps
Entertainment on its editorial surface, and finalizes verified Entertainment GUIDs
and Underreported cross-links after the generic verifier finishes.
"""
import re

import classify_live_feed as classifier
import update_news_v4 as v4

_base_source_is_trusted = v4.core.source_is_trusted


def v4_source_is_trusted(source):
    """Use the production trust policy plus the adult-industry trade sources
    intentionally collected by the authoritative Dirty Entertainment pass.
    """
    tokens = set(re.findall(r"[a-z0-9]+", (source or "").lower()))
    if tokens & {"xbiz", "avn"}:
        return True
    return _base_source_is_trusted(source)


classifier.source_is_trusted = v4_source_is_trusted
classifier.NON_ROUTABLE_INPUT = set(classifier.NON_ROUTABLE_INPUT) | {"entertainment"}

import verify_feed

# verify_feed calls classify() from the same module object above, so its final
# source/category decision uses the V4 trust and non-reroute policy.
verify_feed.EDITORIAL_SURFACES = set(verify_feed.EDITORIAL_SURFACES) | {"entertainment"}

if __name__ == "__main__":
    verify_feed.main()
    import finalize_entertainment_v4
    finalize_entertainment_v4.main()
