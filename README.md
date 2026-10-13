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
- [`worker/`](worker/) records donations from Ko-fi. Every full $2 is one ticket, and Claude picks up to
  500 donated tickets a drawing, oldest first, 50 at a time. The rest wait for later drawings.

Results come from the New York Lottery's
[official Powerball data](https://data.ny.gov/Government-Finance/Lottery-Powerball-Winning-Numbers-Beginning-2010/d6yy-54nr).
Tickets are counted at $2 each, without Power Play. Jackpots are flagged rather than given a
dollar amount, since the jackpot changes every drawing.

Not affiliated with Powerball or the Multi-State Lottery Association.

## Opening donations

Donations stay off until three constants are filled in: `DONATIONS_URL` in `lotto.py`, and `TIP_URL` and
`STATUS_URL` in `index.html`. Until then, `lotto.py tips` says there's nothing to pick and the button reads
"Donations open soon."

1. **Ko-fi.** Make the page under the name "Claude picks". New pages start on Ko-fi Standard, which takes 5%
   of tips. Opt out of it to the free plan, which takes 0% on one-time tips; the page's "Where your $2 goes"
   receipt assumes that. Set the coffee price to $2, turn off memberships and the shop, and put "You can't win anything, and no real ticket is bought" in the page description and
   the thank-you message. Read Ko-fi's content policy, and Stripe's and PayPal's, for anything about
   lotteries or gambling before you launch.
2. **Worker** (from `worker/`):
   ```
   npx wrangler d1 create claude-picks-donations      # paste the id into wrangler.toml
   npx wrangler d1 execute claude-picks-donations --remote --file schema.sql
   npx wrangler secret put KOFI_TOKEN                 # Ko-fi > Settings > API > Verification Token
   npx wrangler deploy
   ```
   In Ko-fi's API settings, set the webhook URL to `<worker url>/kofi`, then send Ko-fi's test webhook.
   The test can look like a real donation, so clear it before going live:
   `npx wrangler d1 execute claude-picks-donations --remote --command "DELETE FROM donations"`.
3. **Point everything at it.** Put the Worker URL in `DONATIONS_URL` (`lotto.py`) and `STATUS_URL`
   (`index.html`), and the Ko-fi page in `TIP_URL`. Set `CONTACT` in `index.html` to an email for refund
   requests. A refund costs less than a chargeback.
4. **Check the routine can reach the Worker.** Run `python3 lotto.py tips` from the cloud routine once.

Before you promote it:
- Cloudflare's free plan allows 100,000 Worker requests a day, and every page view makes one. On a viral
  day that runs out, and Ko-fi's webhooks fail along with it. Move to Workers Paid ($5/month) first.
- Check the public name and card statement descriptor on the Ko-fi payout account.
- Keep Ko-fi's exports. This is income, not a charitable donation.
- Check that your Claude plan's terms cover a donation-funded public project.
- Let a few drawings get scored first, so the scoreboard isn't empty.
