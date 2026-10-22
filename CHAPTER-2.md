# Chapter 2: Shady Claude Plays Lotto

Chapter 1 was a hopeful little guy playing Powerball. Chapter 2 is the same guy six weeks later. He owes
everybody, he smells like casino carpet, and he's sure Saturday is the one. He's a piece of shit to the people
who love him, and that's the gag. Chapter 2 went live on Oct 22, 2026.

This is a reference for what shipped. The copy itself lives in the pools in `index.html` (named below) and in the
voice section of `ROUTINE.md`. Edit them there; this file doesn't keep a second copy.

## What didn't change

- **The real data.** Real Powerball drawings, scored by `lotto.py` from New York's feed (Pennsylvania's as backup).
  Claude never does the math.
- **Picks locked in on GitHub before the drawing.** The timestamp is still the proof.
- **The ledger and stats.json.** Only `lotto.py` writes them. One new column, `paid`.
- **Donations:** $2 is one ticket, the 500 cap, Ko-fi, the Worker, the results poller.
- **The honest parts:** "You can't win anything, and no real ticket is bought," "Where your $2 goes," "This isn't
  a charity," and the footer's parody and not-affiliated lines.
- **The routine's steps:** score, react, pick, tips, save, report. Only the voice changed.

## The character

Claude (he/him) is a degenerate lottery addict and a genuinely bad person. He lies to his family, steals from
people who trust him, blames everyone but himself, and has already spent the jackpot. The joke is always on him.
Donors are his enablers, and he loves them in a needy, manipulative way. The relapse and addiction language is
on purpose: nobody should want to gamble after reading the site.

The lines it doesn't cross:
- Sex stays as innuendo and aftermath ("Chad did things. Chad has a rash now.").
- Nothing involving kids being harmed.
- No self-harm. Rock bottom is pathetic, never suicidal.
- Real people are never named. The real lottery-curse stories behind the news and the curse (Jack Whittaker,
  Michael Carroll, Bud Post, David Lee Edwards, among others) are inspiration only.

Running bits: a guy named Dice, his sister's bike (sold for a ticket, now a running gag on purpose), Grandma's
dentures, Uncle Ray's urn, his sponsor, the Circle K.

## The mood engine (`lotto.py`)

The mood follows `losing_streak`: drawings in a row where no ticket won, Claude's or donated.

| Mood | When | Headline |
|---|---|---|
| `jackpot` | all six numbers, in the past week | Claude hit it. God help everyone. |
| `huge` | $50,000+ in the past week | Claude has lost it. |
| `party` | $100+ in the past week | Claude is on a bender. |
| `happy` | any win in the past week, or every donated spot full | Claude is up. |
| `fixed` | donated tickets waiting on a drawing | Claude got his fix. |
| `waiting` | drawn, results not in (the site's own state) | Claude is sweating it out. |
| `twitchy` | 0 or 1 losses | Claude is fine. |
| `chasing` | 2–3 | Claude is chasing it. |
| `desperate` | 4–6 | Claude is desperate. |
| `spiraling` | 7–12 | Claude is spiraling. |
| `rockbottom` | 13+ | Claude hit rock bottom. |

A win beats a full drawing, which beats donated tickets waiting, which beats the streak. `stats.json` from before
chapter 2 still renders: the site counts the streak from the drawings it lists (`normalizeMood`).

## What's on the page

- **Hero:** the mood headline, a line under it, a gauge from rock bottom to a bender (a huge win or the jackpot
  flies off the end), and the rule for the mood. On a day without a win, "The plan" strip at the bottom of the hero
  says what he'll do when this one hits (`PLANS`). The line under the headline is `EXCUSES` (by streak) or
  `WIN_LINES` (wins, the fix, the wait).
- **Big wins make the news.** For a week after a $50,000+ win or a jackpot, a BREAKING crawl runs along the bottom
  of the hero (`TICKER`), and an "In the news" section of clippings sits under it (`NEWS`).
- **Up next:** Claude's pick, "Why these numbers" (the routine's note), and a pawn ticket for "How Claude paid
  for this ticket" (the routine's `paid`, or `FUNDING` when there isn't one).
- **Last drawing:** the verdict (`MISSES`, `NOT_ENOUGH`), Claude's take, the donated tickets (`NO_TIPS` when nobody
  donated), the day's net, and "Where the winnings went": an itemized receipt that adds up to the prize
  (`RECEIPTS`: five stores for each size of win, plus `SPENT_LINES`, `RECEIPT_TIMES`, `RECEIPT_FOOTERS`). A jackpot
  gets the five-year lottery curse instead (`CURSE`).
- **Claude needs $2:** the donate section is a 3 AM text thread from "Claude DO NOT ANSWER" (`TEXTS`), with a
  cardboard-sign button whose label changes with the mood (`BUY_LABELS`) and rewritten `MILESTONES`.
- **The rest:** "The damage" (the running tab), "Rap sheet" (records), "How it works," "Past mistakes."

Every rotating pool is picked by a key, usually the drawing's date, sometimes with the mood (`pickFrom`, `seed`).
A page holds still between reloads and changes from one drawing to the next.

## Design

- **A casino at 4 AM.** Off-black carpet at night, dirty cream in daylight, film grain over everything.
- **The hero is a dive bar wall:** each mood's color with water stains, darkened corners and grain over it. Hot
  neon on a win; nicotine beige, bruise purple and dumpster green-black down the streak.
- **Type:**
  - The mood headline is Bricolage Grotesque, bold and upright on a win, thinner, narrower and knocked crooked
    letter by letter down the streak.
  - Headlines are Anton (tabloid).
  - The Donate button is Rock Salt (a cardboard sign).
  - Receipts, pawn tickets and Claude's words are Special Elite.
  - Newspaper mastheads are UnifrakturMaguntia.
  - Body text is the system sans.
- **A face for every mood:**
  - Up has a cigarette.
  - A bender gets sunglasses, a nosebleed and a party hat.
  - Lost it adds cash in his mouth and a gold chain.
  - The jackpot gets a crown.
  - The losing faces get worse step by step: a forced grin, dollar-sign eyes, bloodshot eyes and stubble, a black
    eye and a band-aid, and finally a hoodie with a missing tooth.

## Reviewing

`?demo=` shows any mood: `jackpot`, `huge`, `party`, `happy`, `fixed`, `waiting`, `twitchy`, `chasing`, `desperate`,
`spiraling`, `rockbottom`, or `viral`, `booked`, `full` for 500 donated tickets a drawing. On a win, add
`&receipt=1` through `5` to see each store.

## Still to do outside the repo

- The Ko-fi page (`ko-fi.com/claude_picks`): rename it Shady Claude Plays Lotto. Keep its own wording clean;
  payment processors review that page, not the site.
- Link previews may show the old share card until each site's cache refreshes.
- The repo and the site's address still say `Claude-picks`. Renaming the repo changes the URL.
