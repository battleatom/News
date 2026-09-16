# Underreported V6 — Clean Architecture Test Build

V6 is a standalone rebuild. It does not import, execute, patch, or depend on the V4/V5 runtime or build scripts.

## Design rules

- One normalized `Story` model.
- One central source registry: `config/sources.json`.
- One collector entry point: `src/build.py`.
- One deterministic pipeline for normalization, ranking, source caps, and dedupe.
- One frontend store and one renderer registry.
- One pagination owner.
- No `MutationObserver`.
- No `canonicalRender`, HTML patching, injected runtime CSS, or version-layer wrappers.
- One stylesheet.
- Generated output lives only in `v6/dist/`.
- Production `main` is not modified by the V6 workflow.
- V4 remains preserved on the existing `V4` branch.

## Runtime modules

`store.js` owns application state and pagination.

`renderers.js` owns category rendering. Specialized renderers register once for NFL and Box Office; every other category uses the generic story renderer.

`location.js` resolves and caches location. Local and Region filtering happens before cards are rendered, not by post-render DOM mutation.

`feedback.js` talks directly to the existing persistent D / NR / NW feedback endpoint. Suppression happens before rendering; no DOM observer is needed.

## Data pipeline

`registry.py` validates the source registry.

`collector.py` collects direct RSS or Google News discovery feeds without depending on the old collector stack.

`pipeline.py` normalizes URLs, scores stories, applies per-source caps, removes near duplicates, and creates deterministic Why It Matters text from the actual story/category.

`specialized.py` owns independent NFL and Box Office adapters. NFL uses ESPN scoreboard data. Box Office uses TMDB only when `TMDB_API_KEY` is available; it does not fall back to V5-generated movie data.

`build.py` performs a single build and writes `feed.json`, `nfl.json`, `boxoffice.json`, `status.json`, and the static frontend.

`audit.py` rejects legacy architecture markers, duplicate story IDs/URLs, missing artifacts, missing sticky structure, and any V6 use of `MutationObserver` or `canonicalRender`.

## Testing

The V6 CI workflow runs:

1. Python syntax validation.
2. Unit tests.
3. Deterministic fixture build.
4. Static architecture audit.
5. Chromium browser smoke test.
6. Independent live-source build.
7. Live build audit.
8. Uploads fixture and live V6 builds as workflow artifacts.

Nothing in V6 deploys to the production root until it is explicitly promoted.
