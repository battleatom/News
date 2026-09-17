const LIVE_JSON = new Set([
  "/feed.json",
  "/status.json",
  "/nfl.json",
  "/boxoffice.json",
  "/markets.json"
]);

function noStore(response) {
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate");
  headers.set("Pragma", "no-cache");
  headers.set("Expires", "0");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/healthz") {
      try {
        const statusUrl = new URL("/status.json", url);
        const statusResponse = await env.ASSETS.fetch(new Request(statusUrl, {
          method: "GET",
          headers: { "Accept": "application/json" }
        }));
        if (!statusResponse.ok) {
          return Response.json({
            ok: false,
            service: "underreported-news",
            status: statusResponse.status
          }, { status: 503 });
        }
        const status = await statusResponse.json();
        return Response.json({
          ok: true,
          service: "underreported-news",
          version: status.version || "6",
          generatedAt: status.generatedAt || null,
          storyCount: status.storyCount ?? null,
          poolStoryCount: status.poolStoryCount ?? null,
          reserveStoryCount: status.reserveStoryCount ?? null,
          collectorErrors: Array.isArray(status.collectorErrors) ? status.collectorErrors.length : null
        }, {
          headers: {
            "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate"
          }
        });
      } catch (error) {
        return Response.json({
          ok: false,
          service: "underreported-news",
          error: String(error?.message || error)
        }, { status: 503 });
      }
    }

    const response = await env.ASSETS.fetch(request);
    return LIVE_JSON.has(url.pathname) ? noStore(response) : response;
  }
};
