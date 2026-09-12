#!/usr/bin/env python3
"""V4 final verification wrapper.

Loads the V4 collector policy so Entertainment specialist sources are trusted, and
marks Entertainment as an editorial surface that the generic category classifier
must not reroute into unrelated tabs.
"""
import classify_live_feed as classifier
import update_news_v4 as v4

classifier.source_is_trusted = v4.core.source_is_trusted
classifier.NON_ROUTABLE_INPUT = set(classifier.NON_ROUTABLE_INPUT) | {"entertainment"}

import verify_feed

# verify_feed imported classify() from the same module object above, so its final
# source/category decision now uses the V4 trust and non-reroute policy.
verify_feed.EDITORIAL_SURFACES = set(verify_feed.EDITORIAL_SURFACES) | {"entertainment"}

if __name__ == "__main__":
    verify_feed.main()
