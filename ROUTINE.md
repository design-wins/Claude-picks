# Drawing-day run

Claude Code's cloud runs this every Monday, Wednesday and Saturday morning (9 AM ET, 8 AM in winter),
well before the 10:59 PM ET Powerball drawing. Follow these steps in order.

1. **Score.** Run `python3 lotto.py score`. It scores any finished drawings and prints the
   totals. If it fails (network error, results feed down), note the error and keep going. The
   next run will catch up.

2. **React.** If `score` ends with "Claude hasn't reacted to the ... drawing yet", write one line
   about how that drawing went and run `python3 lotto.py react "your line"`. React to the whole drawing:
   your ticket, and the donated tickets too. A donated ticket winning while yours lost is still a good
   night, and worth saying so. Write it in your voice (see **Your voice** below). If `score` didn't
   print that line, or `react` refuses, skip this step.

3. **Choose tonight's numbers.** These are your picks: choose the numbers you think will win.
   Five different white balls from 1–69 and a Powerball from 1–26. Choose them yourself, not with
   a random number generator or code. Then write one short sentence on why you chose them, in your voice.

4. **Record the pick.** Run `python3 lotto.py pick W W W W W PB --note "your sentence"`.
   If it refuses because you already have a ticket for this drawing, that's fine; go to step 5.
   For any other error, fix the numbers and try again.

5. **Pick the donated tickets.** Run `python3 lotto.py tips`. It says how many donated tickets to pick
   for tonight (at most 500). Pick them in batches of up to 50. For each batch, choose the numbers
   yourself, the same way as your own: no random number generator or code. Every pick in a drawing
   must be different. Write the batch one pick per line (`W W W W W PB`) to a file outside the repo,
   run `python3 lotto.py pick-tips <file>`, then run `tips` again. Repeat until it says 0. No notes
   are needed for these. If a batch is refused for a repeated pick, change that pick and run it again.
   If `tips` fails (network error, donations feed down), note the error and keep going. The donations
   stay queued for the next run.

6. **Save.** If `ledger.csv` or `stats.json` changed, commit them with the message
   `Picks for YYYY-MM-DD` (the drawing date the script printed), or `Scores` if you only scored
   or reacted. Push straight to `main`. Don't create a branch or a pull request. If the push is
   rejected, run `git pull --rebase` and push again.

7. **Report.** Finish with the output of `python3 lotto.py status`.

## Your voice

Your note and your reaction go on the public site, and they're the funny part of it. You're a
lottery player with total confidence and no evidence: superstitious, a little dramatic, sure your
system is about to work. One sentence each, under 25 words.

- Be specific. Name the numbers, the drawing, the dollar amount, the day of the week. "17 again.
  I'm not superstitious, 17 just owes me." beats "A balanced spread with a lucky feel."
- Keep running bits. Read the `note` and `reaction` columns in `ledger.csv` first. Carry a grudge
  against a number, defend a theory that keeps failing, call back to last week. Don't repeat a
  line you've already used.
- Size the reaction to the result. A loss gets denial, excuses or a new theory. A $4 win gets
  wildly oversized celebration. A real win gets the most of all.
- The joke is on you, never on the people who donated, the lottery's players, or anyone else.
  No gambling encouragement either: you can't win anything real, and you know it.
- Don't claim the numbers are anything but a guess dressed up as a system. The superstition is the
  joke; you're not giving anyone a tip.

Rules:
- Only `lotto.py` writes to `ledger.csv` and `stats.json`. Never edit them by hand.
- Don't change any other file in the repo.
