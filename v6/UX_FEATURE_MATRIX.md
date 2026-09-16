# V6 UX parity matrix

V6 uses V5.3.1 as a behavioral specification only. No V2/V3/V4/V5 runtime assets, patch scripts, canonical renderer wrappers, or MutationObserver decorators are imported by V6.

## Shell and status
- [x] Single sticky application shell
- [x] Underreported masthead and health state
- [x] Local date/time
- [x] Device/IP location resolution with cached location and manual refresh
- [x] Current local weather
- [x] Market strip with S&P 500, Dow, Nasdaq, Bitcoin, Gold and Oil
- [x] Automatic feed update status/countdown
- [x] New-story notification toast and lightweight audio cue
- [x] Responsive mobile layout and dark mode

## Navigation
- [x] All V5 content tabs
- [x] Per-tab counts
- [x] Icons
- [x] Horizontal mobile tab scrolling with active-tab centering
- [x] Scroll-to-top on tab change
- [x] Bookmarks tab

## Story cards
- [x] 20-card pagination / Show more
- [x] Five age rails and age legend
- [x] D / NR / NW feedback legend and persistent feedback pools
- [x] Immediate removal/backfill through rerender after feedback
- [x] Source marks
- [x] NEW badges
- [x] Summary
- [x] WHY IT MATTERS hierarchy
- [x] Related coverage expansion
- [x] Local bookmarks

## Specialized tabs
- [x] Underreported heuristic signal and supporting coverage context
- [x] Entertainment labels and Underreported connections
- [x] Legislation official-source badges and bill identifiers
- [x] Local / Region location-aware filtering
- [x] NFL live/final/upcoming cards
- [x] NFL team logos, scores, kickoff, broadcaster/streaming links
- [x] NFL live center and live play feed when ESPN provides plays
- [x] Box Office Now Playing / Coming Soon ordering
- [x] Box Office cyan upcoming / blue new / green playing / red leaving-soon states
- [x] Leaving-soon calculation from confirmed local showtime horizon, not movie age
- [x] Movie description/poster when available
- [x] Local theater showtimes when the build source provides them
- [x] Fallback local showtime search when theater data is unavailable
- [x] Movie news links
- [x] Local/theater news section

## Architecture acceptance
- [x] One renderer registry
- [x] One store
- [x] One pagination owner
- [x] One stylesheet
- [x] No MutationObserver
- [x] No patch chain
- [x] No imports from prior-version runtime code
- [x] Static audit plus Chromium fixture/live smoke tests
