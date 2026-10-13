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
