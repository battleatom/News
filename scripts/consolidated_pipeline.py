from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAGES = [
    ("collector-preflight", [sys.executable, "scripts/preflight_feed.py"]),
    ("collect-news", [sys.executable, "scripts/update_news_normalized.py"]),
    ("refine-tech-gaming", [sys.executable, "scripts/refine_tech_gaming.py"]),
    ("collect-legislation", [sys.executable, "scripts/collect_official_legislation_strict.py"]),
    ("enrich-world", [sys.executable, "scripts/enrich_world_content.py"]),
    ("discover-underreported", [sys.executable, "scripts/underreported_priority.py", "--discover"]),
    ("enrich-underreported", [sys.executable, "scripts/enrich_underreported.py"]),
    ("rank-underreported", [sys.executable, "scripts/underreported_priority.py", "--rank"]),
    ("enrich-legislation", [sys.executable, "scripts/enrich_legislation.py"]),
    ("official-legislation-guard", [sys.executable, "scripts/enforce_official_legislation.py"]),
    ("enrich-x", [sys.executable, "scripts/enrich_x_issues.py"]),
    ("enrich-boxoffice", [sys.executable, "scripts/enrich_box_office.py"]),
    ("boxoffice-location", [sys.executable, "scripts/patch_boxoffice_location.py"]),
    ("clean-news", [sys.executable, "scripts/clean_news.py"]),
    ("filter-landings", [sys.executable, "scripts/filter_landing_pages.py"]),
    ("record-preverify-stats", [sys.executable, "scripts/record_pull_stats.py"]),
    ("cluster-events", [sys.executable, "scripts/cluster_related_coverage.py"]),
    ("verify-feed", [sys.executable, "scripts/verify_feed.py", "--apply"]),
    ("federal-routing-guard", [sys.executable, "scripts/enforce_us_federal.py"]),
    ("official-legislation-final-guard", [sys.executable, "scripts/enforce_official_legislation.py"]),
    ("rebuild-x", [sys.executable, "scripts/enrich_x_issues.py"]),
    ("finalize-stats", [sys.executable, "scripts/record_pull_stats.py", "--finalize"]),
    ("content-briefs", [sys.executable, "scripts/create_content_briefs.py"]),
    ("why-it-matters", [sys.executable, "scripts/update_why_matters.py"]),
    ("build-site", [sys.executable, "scripts/build_site.py"]),
    ("site-audit", [sys.executable, "scripts/site_audit.py"]),
]


def run(stage: str, cmd: list[str]) -> None:
    print(f"\n=== {stage} ===", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    subprocess.run([sys.executable, "-m", "py_compile", *[str(p) for p in sorted((ROOT / "scripts").glob("*.py"))]], cwd=ROOT, check=True)
    for stage, cmd in STAGES:
        run(stage, cmd)
    print("\nConsolidated pipeline completed successfully.")


if __name__ == "__main__":
    main()
