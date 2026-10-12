# Drawing-day run

Claude Code's cloud runs this every Monday, Wednesday and Saturday evening, a few hours before
the 10:59 PM ET Powerball drawing. Follow these steps in order.

1. **Score.** Run `python3 lotto.py score`. It scores any finished drawings and prints the
   totals. If it fails (network error, results feed down), note the error and keep going. The
   next run will catch up.

2. **Choose tonight's numbers.** These are your picks: choose the numbers you think will win.
   Five different white balls from 1–69 and a Powerball from 1–26. Choose them yourself, not with
   a random number generator or code. Then write one short sentence on why you chose them.

3. **Record the pick.** Run `python3 lotto.py pick W W W W W PB --note "your sentence"`.
   If it refuses because you already have a ticket for this drawing, that's fine; go to step 4.
   For any other error, fix the numbers and try again.

4. **Save.** If `ledger.csv` or `stats.json` changed, commit them with the message
   `Picks for YYYY-MM-DD` (the drawing date the script printed), or `Scores` if you only scored.
   Push straight to `main`. Don't create a branch or a pull request. If the push is rejected,
   run `git pull --rebase` and push again.

5. **Report.** Finish with the output of `python3 lotto.py status`.

Rules:
- Only `lotto.py` writes to `ledger.csv` and `stats.json`. Never edit them by hand.
- Don't change any other file in the repo.
