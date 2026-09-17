import { DurableObject } from "cloudflare:workers";

const CONFIG_URLS = [
  "https://raw.githubusercontent.com/battleatom/News/v6/v6/config/sources.json",
  "https://raw.githubusercontent.com/battleatom/News/v6/v6/config/sources-extra.json"
];
const BATCH_SIZE = 36;
const RETIRE_RATIO = 0.075;
const LIVE_JSON = new Set(["/feed.json", "/status.json", "/nfl.json", "/boxoffice.json", "/markets.json"]);

function noStore(response) {
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate");
  headers.set("Pragma", "no-cache");
  headers.set("Expires", "0");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function clean(value = "") {
  return String(value)
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ").trim();
}
function tag(block, name) {
  const match = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${name}>`, "i"));
  return clean(match?.[1] || "");
}
function normalizeTitle(value = "") { return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }
function stableId(value) {
  let h1 = 0xdeadbeef ^ value.length, h2 = 0x41c6ce57 ^ value.length;
  for (let i = 0; i < value.length; i++) {
    const ch = value.charCodeAt(i); h1 = Math.imul(h1 ^ ch, 2654435761); h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return ((h2 >>> 0).toString(16).padStart(8, "0") + (h1 >>> 0).toString(16).padStart(8, "0"));
}
function googleNewsUrl(query) {
  return `https://news.google.com/rss/search?q=${encodeURIComponent(`${query} when:7d`)}&hl=en-US&gl=US&ceid=US:en`;
}
function whyMatters(category) {
  if (["local", "region", "nm"].includes(category)) return "This story has direct state or regional relevance and may affect nearby communities.";
  if (category === "technology") return "This could affect technology products, services, security, or the companies behind them.";
  if (category === "gaming") return "This could affect games, hardware, studios, releases, pricing, or platform users.";
  if (category === "military") return "This concerns defense, armed forces, security, or an active conflict and may have broader implications.";
  if (category === "entertainment") return "This is a current entertainment-industry development involving a release, creator, company, event, or public figure.";
  if (category === "legislation") return "This policy or legislation item may change government action, rules, or legal requirements.";
  return "This is a current development selected for recency, source quality, and potential public impact.";
}
function parseRss(xml, sourceCfg) {
  const items = xml.match(/<item\b[\s\S]*?<\/item>/gi) || [];
  const rows = [];
  for (const item of items.slice(0, 60)) {
    let title = tag(item, "title"), url = tag(item, "link") || tag(item, "guid");
    if (!title || !url) continue;
    let source = tag(item, "source") || sourceCfg.name || "Unknown";
    if (!tag(item, "source") && title.includes(" - ")) {
      const parts = title.split(" - "); const maybe = parts.at(-1)?.trim();
      if (maybe && maybe.length <= 80) { source = maybe; title = parts.slice(0, -1).join(" - ").trim(); }
    }
    const rawDate = tag(item, "pubDate") || tag(item, "published");
    const date = new Date(rawDate); if (!Number.isFinite(date.getTime())) continue;
    const summary = tag(item, "description");
    rows.push({
      id: stableId(`${sourceCfg.category}|${url}|${title}`), category: sourceCfg.category, title, url, source,
      published_at: date.toISOString(), summary, why_matters: whyMatters(sourceCfg.category),
      state: sourceCfg.state || "", region: sourceCfg.region || "", market: sourceCfg.market || "", source_id: sourceCfg.id,
      cloudflare_collected: true
    });
  }
  return rows;
}
async function collectSource(sourceCfg) {
  const url = sourceCfg.kind === "google_news" ? googleNewsUrl(sourceCfg.query) : sourceCfg.url;
  try {
    const response = await fetch(url, { headers: { "User-Agent": "Underreported-V6-Cloudflare/1.0", "Accept": "application/rss+xml, application/xml, text/xml" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = parseRss(await response.text(), sourceCfg);
    return { source: sourceCfg, rows, error: "" };
  } catch (error) {
    return { source: sourceCfg, rows: [], error: String(error?.message || error) };
  }
}
function storyTime(row) { const n = Date.parse(row?.published_at || ""); return Number.isFinite(n) ? n : 0; }
function dedupe(rows) {
  const seenId = new Set(), seenUrl = new Set(), seenTitle = new Set(), out = [];
  for (const row of rows.sort((a, b) => storyTime(b) - storyTime(a))) {
    const id = String(row.id || stableId(`${row.category}|${row.url}|${row.title}`));
    const url = String(row.url || "").trim(); const title = normalizeTitle(row.title);
    if (seenId.has(id) || (url && seenUrl.has(url)) || (title && seenTitle.has(title))) continue;
    row.id = id; seenId.add(id); if (url) seenUrl.add(url); if (title) seenTitle.add(title); out.push(row);
  }
  return out;
}
function mergeFeed(feed, incoming, categories) {
  const grouped = new Map();
  for (const key of Object.keys(feed.categories || categories || {})) grouped.set(key, [...(feed.stories?.[key] || []), ...(feed.reserves?.[key] || [])]);
  for (const row of incoming) { if (!grouped.has(row.category)) grouped.set(row.category, []); grouped.get(row.category).push(row); }
  const stories = {}, reserves = {}, categoryCounts = {}, reserveCounts = {};
  let retired = 0;
  for (const [key, rows0] of grouped) {
    const cfg = categories[key] || feed.categories?.[key] || {}; let rows = dedupe(rows0);
    const visibleTarget = Number(cfg.visible_target || cfg.target || 50); const poolTarget = Number(cfg.target || visibleTarget + Number(cfg.reserve || 0));
    const incomingCount = incoming.filter(r => r.category === key).length;
    if (incomingCount && rows.length > visibleTarget) {
      const now = Date.now(), maxRetire = Math.min(Math.floor(rows.length * RETIRE_RATIO), Math.max(0, rows.length - visibleTarget));
      const candidates = rows.filter(r => Number(r.views || r.view_count || 0) < 10 && now - storyTime(r) > 48 * 3600000).sort((a, b) => storyTime(a) - storyTime(b));
      const remove = new Set(candidates.slice(0, maxRetire).map(r => r.id));
      if (remove.size) { rows = rows.filter(r => !remove.has(r.id)); retired += remove.size; }
    }
    rows = rows.slice(0, Math.max(visibleTarget, poolTarget));
    stories[key] = rows.slice(0, visibleTarget); reserves[key] = rows.slice(visibleTarget);
    categoryCounts[key] = stories[key].length; reserveCounts[key] = reserves[key].length;
  }
  return { stories, reserves, categoryCounts, reserveCounts, retired };
}

export class FeedState extends DurableObject {
  constructor(ctx, env) { super(ctx, env); this.ctx = ctx; this.env = env; }

  async seed() {
    let feed = await this.ctx.storage.get("feed"), status = await this.ctx.storage.get("status");
    if (feed && status) return { feed, status };
    const [fr, sr] = await Promise.all([this.env.ASSETS.fetch("https://asset/feed.json"), this.env.ASSETS.fetch("https://asset/status.json")]);
    if (!fr.ok || !sr.ok) throw new Error("Unable to seed Cloudflare feed state from static assets");
    feed = await fr.json(); status = await sr.json();
    await this.ctx.storage.put({ feed, status, cursor: 0 }); return { feed, status };
  }

  async refresh() {
    const seeded = await this.seed();
    const configResponses = await Promise.all(CONFIG_URLS.map(url => fetch(url, { cf: { cacheTtl: 300 } })));
    const configs = await Promise.all(configResponses.map(async r => { if (!r.ok) throw new Error(`registry ${r.status}`); return r.json(); }));
    const categories = configs[0].categories || seeded.feed.categories || {};
    const sources = configs.flatMap(cfg => cfg.sources || []);
    let cursor = Number(await this.ctx.storage.get("cursor") || 0); if (cursor >= sources.length) cursor = 0;
    const batch = Array.from({ length: Math.min(BATCH_SIZE, sources.length) }, (_, i) => sources[(cursor + i) % sources.length]);
    const results = await Promise.all(batch.map(collectSource));
    const incoming = results.flatMap(r => r.rows);
    const merged = mergeFeed(seeded.feed, incoming, categories);
    const generatedAt = new Date().toISOString();
    const nextFeed = { ...seeded.feed, version: "6", generatedAt, categories, stories: merged.stories, reserves: merged.reserves, cloudflareRuntime: true };
    const oldStatus = seeded.status || {}; const sourceMap = new Map((oldStatus.sourceStatuses || []).map(r => [r.id, r]));
    for (const result of results) sourceMap.set(result.source.id, { id: result.source.id, name: result.source.name || result.source.id, category: result.source.category, status: result.error ? "error" : (result.rows.length ? "live" : "degraded"), storyCount: result.rows.length, error: result.error });
    const visibleStoryCount = Object.values(merged.categoryCounts).reduce((a, b) => a + b, 0); const reserveStoryCount = Object.values(merged.reserveCounts).reduce((a, b) => a + b, 0); const poolStoryCount = visibleStoryCount + reserveStoryCount;
    const collectorErrors = results.filter(r => r.error).map(r => ({ source: r.source.id, name: r.source.name || r.source.id, error: r.error }));
    const nextStatus = { ...oldStatus, version: "6", generatedAt, storyCount: visibleStoryCount, visibleStoryCount, poolStoryCount, reserveStoryCount, categoryCounts: merged.categoryCounts, reserveCounts: merged.reserveCounts, collectorErrors, sourceStatuses: [...sourceMap.values()], sourceCount: sourceMap.size, healthySourceCount: [...sourceMap.values()].filter(r => r.status === "live").length, buildMode: "cloudflare-live", cloudflareRuntime: true, cloudflareBatch: { cursor, size: batch.length, nextCursor: (cursor + batch.length) % Math.max(1, sources.length), sourceCount: sources.length, incomingStories: incoming.length, retiredLowView: merged.retired } };
    await this.ctx.storage.put({ feed: nextFeed, status: nextStatus, cursor: nextStatus.cloudflareBatch.nextCursor, lastRefresh: nextStatus.cloudflareBatch });
    return nextStatus;
  }

  async fetch(request) {
    const path = new URL(request.url).pathname;
    try {
      if (path === "/refresh" && request.method === "POST") return Response.json(await this.refresh());
      const seeded = await this.seed();
      if (path === "/feed.json") return Response.json(seeded.feed);
      if (path === "/status.json" || path === "/healthz") return Response.json(seeded.status);
      return new Response("Not found", { status: 404 });
    } catch (error) {
      return Response.json({ ok: false, error: String(error?.message || error) }, { status: 503 });
    }
  }
}

function stateStub(env) { return env.FEED_STATE.getByName("production"); }

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(stateStub(env).fetch("https://state/refresh", { method: "POST" }));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/healthz") {
      const response = await stateStub(env).fetch("https://state/healthz");
      if (!response.ok) return noStore(response);
      const status = await response.json();
      const generated = Date.parse(status.generatedAt || ""); const ageMinutes = Number.isFinite(generated) ? Math.round((Date.now() - generated) / 60000) : null;
      return Response.json({ ok: ageMinutes == null ? false : ageMinutes <= 35, service: "underreported-news", runtime: status.cloudflareRuntime ? "cloudflare" : "static-seed", generatedAt: status.generatedAt || null, ageMinutes, storyCount: status.storyCount ?? null, poolStoryCount: status.poolStoryCount ?? null, reserveStoryCount: status.reserveStoryCount ?? null, collectorErrors: Array.isArray(status.collectorErrors) ? status.collectorErrors.length : null, batch: status.cloudflareBatch || null }, { status: ageMinutes != null && ageMinutes <= 35 ? 200 : 503, headers: { "Cache-Control": "no-store" } });
    }
    if (url.pathname === "/feed.json" || url.pathname === "/status.json") {
      const response = await stateStub(env).fetch(`https://state${url.pathname}`);
      if (response.ok) return noStore(response);
    }
    const response = await env.ASSETS.fetch(request);
    return LIVE_JSON.has(url.pathname) ? noStore(response) : response;
  }
};
