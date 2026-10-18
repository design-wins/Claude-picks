-- One row per Ko-fi payment that buys tickets. Nothing about the donor is kept: no name, email, or message.
CREATE TABLE IF NOT EXISTS donations (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  kofi_transaction_id TEXT NOT NULL UNIQUE,
  received_at TEXT NOT NULL,
  type TEXT NOT NULL,
  amount TEXT NOT NULL,
  currency TEXT NOT NULL,
  tickets INTEGER NOT NULL
);

-- A running total for the site's live count, so a page view reads one row instead of every donation.
CREATE TABLE IF NOT EXISTS totals (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  tickets INTEGER NOT NULL
);
INSERT OR IGNORE INTO totals (id, tickets) SELECT 1, COALESCE(SUM(tickets), 0) FROM donations;

-- When the Worker's cron last started the Score workflow for a drawing, so it doesn't start it every 5 minutes.
CREATE TABLE IF NOT EXISTS score_dispatches (
  draw_date TEXT PRIMARY KEY,
  dispatched_at INTEGER NOT NULL
);
