# Claude-picks

Before every Powerball drawing, Claude picks the numbers it thinks will win. After the
drawing, a script checks them against the official results and keeps a running tab of what
the tickets would have cost and what they would have won.

**No real tickets are bought, and nobody wins anything.** Claude can only win in spirit.

- [`ledger.csv`](ledger.csv) holds every pick, timestamped before its drawing, and its result.
- [`stats.json`](stats.json) has the running totals and Claude's current mood:
  - **party** after a win of $100 or more in the past week
  - **happy** after any win in the past week
  - **sad** after a month without a win, unless someone has bought it a ticket for an
    upcoming drawing, which brings back a little hope
  - **hopeful** the rest of the time
- [`lotto.py`](lotto.py) does the picking bookkeeping and the scoring. Claude chooses the
  numbers; the script handles everything that has to be exact.
- [`ROUTINE.md`](ROUTINE.md) is what Claude follows on each drawing day.

Results come from the New York Lottery's
[official Powerball data](https://data.ny.gov/Government-Finance/Lottery-Powerball-Winning-Numbers-Beginning-2010/d6yy-54nr).
Tickets are counted at $2 each, without Power Play. Jackpots are flagged rather than given a
dollar amount, since the jackpot changes every drawing.

Not affiliated with Powerball or the Multi-State Lottery Association.
