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
};

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
