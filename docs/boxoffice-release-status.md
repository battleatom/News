# Box Office release-status UI

V5.3.1 Box Office movie cards use release-status rails and release-date ordering.

- Cyan: Upcoming. Coming Soon is ordered by nearest release date first.
- Blue: New release. Released within the last 14 days.
- Green: Now playing. Released more than 14 days ago and still listed locally.
- Red: Leaving soon. Used only when a leaving date/status is confirmed; the UI does not invent a theatrical end date.
- Now Playing is rendered before Coming Soon and is ordered newest release first.
- Movie cards show the release date and, after release, the number of days in theaters.

Release dates come from the configured national release schedule. Local Farmington showtimes remain sourced separately.
