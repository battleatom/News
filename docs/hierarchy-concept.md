# Saved concept: semantic card hierarchy

Status: concept only. No active implementation is intended while this note exists.

The proposed visual hierarchy for ordinary news cards was:

- High impact — red rail / lightning marker
- Analysis — purple rail / diamond marker
- Local — green rail / dot marker
- Trending — blue rail / rising-arrow marker
- Standard — neutral gray rail / dot marker

The intent was to make importance/scope visible at a glance without changing article ordering or category routing.

If revisited later, the preferred architecture is a single renderer-time card finalizer rather than observers or competing CSS layers. A card would receive one explicit hierarchy value at creation time and one authoritative rail style. Browser-level tests should verify computed colors and visible markers before release.

Exceptions that must remain independent of this concept:

- NFL keeps its own game/team presentation.
- Underreported keeps its existing age-based color system and should not be mapped onto the semantic hierarchy above.

This file intentionally contains documentation only; it is not loaded by the site.
