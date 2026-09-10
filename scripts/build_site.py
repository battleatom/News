from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The data collectors run before this file. All page mutations are finalized here
# in one deterministic order so feature patches cannot race one another.
PATCHERS = [
    'scripts/apply_clean_design.py',
    'scripts/add_local_status.py',
    'scripts/patch_header.py',
    'scripts/persist_active_tab.py',
    'scripts/patch_article_style.py',
    'scripts/patch_region_tab.py',
    'scripts/fix_region_tab_click.py',
    'scripts/patch_location_state.py',
    'scripts/patch_underreported_ui.py',
    'scripts/patch_x_ui.py',
    'scripts/patch_site_features.py',
    'scripts/patch_refresh_success.py',
    'scripts/patch_shared_page_state.py',
    'scripts/patch_auto_refresh_timer.py',
    'scripts/patch_boxoffice_ui.py',
    'scripts/patch_pull_stats_ui.py',
    'scripts/patch_bookmarks.py',
    'scripts/patch_nfl_live.py',
    'scripts/patch_load_more.py',
    'scripts/patch_legislation_ui.py',
    'scripts/patch_legislation_location.py',
    'scripts/patch_related_ui.py',
    'scripts/patch_v2_frontend.py',
    'scripts/dedupe_generated_ui.py',
    'scripts/normalize_generated_html.py',
    'scripts/patch_v22_alerts_status.py',
    'scripts/patch_v23_new_alerts.py',
    'scripts/patch_v25_location_content.py',
    # Must be last. It removes legacy ownership that earlier patch generations
    # may have reintroduced and verifies the final runtime contract.
    'scripts/patch_runtime_cleanup_v282.py',
]


def run(path: str) -> None:
    target = ROOT / path
    if not target.exists():
        raise SystemExit(f'Missing required site build step: {path}')
    print(f'\n=== {path} ===', flush=True)
    subprocess.run([sys.executable, str(target)], cwd=ROOT, check=True)


def main() -> None:
    for patcher in PATCHERS:
        run(patcher)
    print('\nUnderreported site build complete.')


if __name__ == '__main__':
    main()
