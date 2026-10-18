// Records Ko-fi donations so lotto.py can turn every full $2 into a ticket for Claude to pick.
//
//   POST /kofi                 Ko-fi's webhook (form field `data`, JSON)
//   GET  /donations?after=N    donations with seq > N, oldest first, for lotto.py
//   GET  /status               total donated tickets, for the site

const TICKET_COST = 2;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (request.method === "POST" && url.pathname === "/kofi") return await kofi(request, env);
      if (request.method === "GET" && url.pathname === "/donations") return await donations(url, env);
      if (request.method === "GET" && url.pathname === "/status") return await status(env);
      return new Response("Not found", { status: 404 });
    } catch (err) {
      console.error(err);
      // A non-200 makes Ko-fi retry the webhook later.
      return new Response("Server error", { status: 500 });
    }
  },

  // Cron (wrangler.toml): every 10 minutes. Starts the Score workflow as soon
  // as New York's feed has a full result for a drawing that still has tickets waiting, instead of waiting
  // for GitHub's own schedule, which can start hours late.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(checkResults(env).catch((err) => console.error("results:", err)));
  },
};

const RESULTS_URL = "https://data.ny.gov/resource/d6yy-54nr.json";
const STATS_URL = "https://design-wins.github.io/Claude-picks/stats.json";
const REPO = "design-wins/claude-picks";
const RETRY_AFTER_MS = 30 * 60 * 1000; // if a drawing still isn't scored this long after a dispatch, try again

async function checkResults(env) {
  if (!env.GITHUB_TOKEN) return console.log("results: no GITHUB_TOKEN set, skipping");
  const stats = await (await fetch(`${STATS_URL}?t=${Date.now()}`, { cache: "no-store" })).json();
  // Drawings with Claude's or donated tickets still waiting on a result.
  const waiting = [...new Set([...stats.upcoming.map((r) => r.draw_date),
    ...(stats.upcoming_tips || []).map((g) => g.draw_date)])].sort();
  if (!waiting.length) return;
  const query = new URLSearchParams({ $where: `draw_date >= '${waiting[0]}T00:00:00'`, $order: "draw_date" });
  const res = await fetch(`${RESULTS_URL}?${query}`, { headers: { "User-Agent": "claude-picks/1.0" } });
  if (!res.ok) return console.log(`results: feed returned ${res.status}`);
  // lotto.py only scores Claude's ticket once the Power Play and Double Play numbers are out too.
  const ready = (await res.json())
    .filter((r) => r.multiplier && (r.double_play_winning_numbers || "").trim().split(/\s+/).length === 6)
    .map((r) => r.draw_date.slice(0, 10))
    .filter((d) => waiting.includes(d));
  if (!ready.length) return;
  const last = await env.DB.prepare("SELECT dispatched_at FROM score_dispatches WHERE draw_date = ?").bind(ready[0]).first();
  if (last && Date.now() - last.dispatched_at < RETRY_AFTER_MS) return; // already started; Pages may just be catching up
  const gh = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/score.yml/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "claude-picks",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  if (gh.status !== 204) return console.log(`results: dispatch failed, ${gh.status} ${await gh.text()}`);
  await env.DB.prepare("INSERT OR REPLACE INTO score_dispatches (draw_date, dispatched_at) VALUES (?, ?)")
    .bind(ready[0], Date.now()).run();
  console.log(`results: ${ready.join(", ")} ready, started Score`);
}

async function kofi(request, env) {
  let data;
  try {
    data = JSON.parse((await request.formData()).get("data"));
  } catch {
    console.log(`kofi: rejected, unreadable payload (content-type ${request.headers.get("content-type")})`);
    return new Response("Bad payload", { status: 400 });
  }
  if (!(await sameSecret(data.verification_token, env.KOFI_TOKEN))) {
    // Lengths only, never the tokens, so a mismatch can be told apart from a missing secret.
    console.log(`kofi: rejected, token mismatch (got ${String(data.verification_token ?? "").length} chars, expected ${String(env.KOFI_TOKEN ?? "").length})`);
    return new Response("Unauthorized", { status: 401 });
  }

  // One-off and monthly tips in USD buy tickets; each monthly payment arrives as its own "Subscription".
  // Anything else (shop orders, commissions, other currencies) buys none, so it isn't stored.
  const amount = Number(data.amount);
  const tickets = ["Donation", "Subscription"].includes(data.type) && data.currency === "USD" && amount > 0
    ? Math.floor(amount / TICKET_COST)
    : 0;
  if (!tickets) {
    console.log(`kofi: ${data.type} ${data.amount} ${data.currency} -> no tickets, not stored`);
    return new Response("OK");
  }
  if (!data.kofi_transaction_id) {
    console.log(`kofi: rejected, ${data.type} with no transaction id`);
    return new Response("Missing transaction id", { status: 400 });
  }
  // Ko-fi retries until it gets a 200, so the same payment can arrive twice. The UNIQUE id makes that a no-op.
  const result = await env.DB.prepare(
    `INSERT OR IGNORE INTO donations (kofi_transaction_id, received_at, type, amount, currency, tickets)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).bind(
    String(data.kofi_transaction_id),
    data.timestamp || new Date().toISOString(),
    String(data.type || ""),
    String(data.amount || ""),
    String(data.currency || ""),
    tickets
  ).run();
  if (result.meta.changes) {
    await env.DB.prepare("UPDATE totals SET tickets = tickets + ? WHERE id = 1").bind(tickets).run();
  }
  // No donor details here: just what kind of payment it was and what it bought.
  console.log(`kofi: ${data.type} ${data.amount} ${data.currency} -> ${tickets} tickets${result.meta.changes ? "" : " (duplicate, ignored)"}`);
  return new Response("OK");
}

async function donations(url, env) {
  const after = Number.parseInt(url.searchParams.get("after") || "0", 10) || 0;
  // lotto.py fills at most 500 tickets a drawing, and every row here has at least one, so 1,000 is plenty.
  const { results } = await env.DB.prepare(
    "SELECT seq, received_at, tickets FROM donations WHERE seq > ? AND tickets > 0 ORDER BY seq LIMIT 1000"
  ).bind(after).all();
  return json(results);
}

async function status(env) {
  // Every page view can land here, so read the one-row running total rather than adding up donations.
  const row = await env.DB.prepare("SELECT tickets FROM totals WHERE id = 1").first();
  return json({ tickets_donated: row.tickets }, {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=60",
  });
}

function json(body, headers = {}) {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json", ...headers } });
}

async function sameSecret(given, expected) {
  if (typeof given !== "string" || !expected) return false;
  const enc = new TextEncoder();
  // Hash both so the comparison is constant-time regardless of length.
  const [a, b] = await Promise.all([given, expected].map((s) => crypto.subtle.digest("SHA-256", enc.encode(s))));
  return crypto.subtle.timingSafeEqual(a, b);
}
