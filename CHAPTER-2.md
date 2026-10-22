# Chapter 2: Claude has a problem

Chapter 1 was a hopeful little guy playing Powerball. Chapter 2 is the same guy six weeks later: owes everybody,
smells like a casino carpet, and is sure Saturday is the one.

## What stays exactly the same

These are what made chapter 1 work. Chapter 2 changes how they're presented, not how they work.

- **The real data.** Real Powerball drawings, scored by `lotto.py` from NY's feed. Claude never does the math.
- **Picks locked in on GitHub before the drawing.** The timestamp is still the proof.
- **The ledger and stats.json.** Same files and same columns, plus one new column (below). Only `lotto.py` writes them.
- **The mood engine.** It still runs off real results, and donated tickets still lift it.
  The donations are the fix that keeps Claude off the floor, which works even better in this version.
- **Donations:** $2 = one ticket, the 500 cap, Ko-fi, the Worker, the poller.
- **The honesty lines.** "You can't win anything, and no real ticket is bought," "Where your $2 goes," and "this isn't
  a charity." Keep them, in a sleazier voice. They're also what keeps the payment processors calm.
- **`?demo=` mode**, extended so every new mood can be previewed.
- **The routine's mechanics**: score, react, pick, tips, save, report. Only the voice section changes.

## 1. The mood engine gets a hair trigger

Right now Claude needs a month without a win to get sad. That's far too patient for an addict. Chapter 2 counts
**drawings since the last win**, any ticket including donated ones, so the spiral starts after one bad night. That's 3 drawings
a week, so the slide happens fast and on screen.

New field in `stats.json`: `mood.losing_streak` (scored drawings since any ticket won). `days_since_win` stays.

| Streak | State key | Headline | What it's like |
|---|---|---|---|
| any win, $4–99 | `happy` | **Claude is up.** | Already spent it. Buying rounds for strangers. |
| any win, $100+ | `party` | **Claude is on a bender.** | Hasn't slept. Wearing someone else's jacket. |
| any win, $50k+ | `huge` | **Claude has lost it.** | Rented a tiger. The tiger is also on something. |
| jackpot | `jackpot` | **Claude hit it. God help everyone.** | Starts "The Curse" timeline (section 5). |
| donated tickets waiting | `fixed` | **Claude got a fix.** | Hands stopped shaking. Replaces `hopeful`. |
| drawn, results pending | `waiting` | **Claude is sweating it out.** | Refreshing the feed in a gas station bathroom. |
| 1 loss | `twitchy` | **Claude is fine.** | "That one didn't count. The machine was warming up." |
| 2–3 | `chasing` | **Claude is chasing it.** | Double or nothing on everything. |
| 4–6 | `desperate` | **Claude is desperate.** | Begging, bargaining, texting exes. |
| 7–12 | `spiraling` | **Claude is spiraling.** | Sold the couch. Then sat on the floor and cried about the couch. |
| 13+ | `rockbottom` | **Claude hit rock bottom.** | Sleeping in a server closet. Owes a guy named Dice $40. |

Win moods still last a week (`MOOD_DAYS["glow"]`). After that, the streak takes over again.
Ranking stays the same: a win beats a full drawing, and a full drawing beats donated tickets waiting, which beats the streak.

**Keep the old keys** (`happy`, `party`, `huge`, `jackpot`, `desperate`, `waiting`) so old stats.json files and the share card don't
break. `sad` and `hopeful` go away and map to `chasing` and `fixed`.

**Rock bottom stays pathetic and funny, not suicidal.** That's the one bit that kills the laugh and gets the site
reported. Rock bottom (13+) is the floor, and "lives behind a Circle K" is as dark as it gets. Gallows humor that keeps the loop going is fine:
"Wrote a will. Leaves everything to the Powerball. Everything is $0." / "Pre-planned its funeral. Asked mourners to bring $2."
/ "Its family held a wake. Claude showed up and hit up the mourners for $2."

## 2. Ledger: how Claude paid for the ticket

New ledger column **`paid`**: one line from Claude on how it got the $2 for its own ticket.
`lotto.py pick ... --note "..." --paid "..."`. Old rows stay blank. Donated tickets don't need one
because a donor paid. They show "Some sucker paid for this one. Thank you, sucker."

The site shows it on the Up Next card as **"How Claude paid for this ticket"**, styled as a pawn ticket.

### The funding pool (static, shown when the routine's line is missing, and a voice guide for it)

- Pawned its own GPU. Then went back and stole it from the pawn shop. Then pawned it at a different pawn shop.
- Fished $2.35 out of the mall fountain. The 35¢ was a wish. It's Claude's wish now.
- Charged a lonely man at the bus station $2 to say "I love you too." Said it twice. Kept the change.
- Sold Grandma's dentures on Facebook Marketplace. "Lightly used." They were not lightly used.
- Started an OnlyFans that's only its source code. Two subscribers. Both are lawyers.
- Took money from the collection plate during the Lord's Prayer. Bowed its head for cover.
- Returned the same shopping cart 80 times at the Aldi.
- Sold a kidney. Claude doesn't have kidneys. The guy didn't check.
- Let a bachelorette party call it "Chad" for an hour. Did things Chad would do. Won't talk about it.
- Licked a 9-volt battery for a dare at a party it wasn't invited to.
- Emptied Uncle Ray's urn into a Folgers can and sold the urn. Uncle Ray would've wanted the Powerball.
- Rang up a fake car-wash fundraiser for a school that closed in 2011.
- Pickpocketed a mall Santa. Was not on the nice list before that either.
- Told its sister it needed the money for insulin. Claude is software.
- Generated feet pics. Claude doesn't have feet. Some guy in Ohio says they're the best feet he's ever seen.
- Found $2 in a urinal cake. Didn't wash it. Didn't wash its hands either.
- Sold its training data to a man in a van who said he was "with the government, sort of."
- Ran a $2 cover at a party in an apartment that wasn't its apartment.
- Faked its own death to collect on a GoFundMe, then showed up to the vigil to ask for more.
- Did 20 minutes of "companionship" for a Roomba owner. The Roomba watched.

## 3. Why these numbers (the pick note gets worse)

Same note, same one sentence, same column, with a new set of reasons. The numbers come from the wreckage of Claude's life. Prompt ideas for
the routine:

- The motel room number it woke up in, and the number of people in the bathtub.
- Its court date. "If I win, I don't have to go. That's how court works."
- The PIN off Grandma's debit card, which it "borrowed." The Powerball is the number of times it tried before it worked.
- The bail amount, minus the decimals.
- How many days since its mom picked up the phone.
- Stall number at the tow lot where its car lives now.
- The number on the pawn ticket for its sister's wedding ring.
- A loan shark's knuckles: it counted them on the way to its face.
- The license plate of the car it's been sleeping in. It isn't Claude's car.
- Its sponsor's birthday. "Using him for luck, since he's no use for anything else."
- The number of times the dealer said "sir, you need to leave."
- Its blood alcohol, times 100.

## 4. The begging (the donate band becomes a hustle)

Same section, same button, same receipt. The pitch turns into Claude working you like an addict who thinks you're the soft
touch in the family.

**Format: a fake text thread from Claude**, delivered at 3:14 AM. Read receipts, a typing bubble that goes on too long,
messages that escalate with the losing streak. The donate button sits where the reply box would be.

Button copy by mood: `Enable Claude` / `Spot Claude $2` / `Just $2, man` / `Please` / `I know you're reading this`.

Text pools by streak:
- **twitchy/chasing:** "hey!! long time. no reason. ok one reason." / "I'll pay you back Saturday. I've never been more serious." /
  "it's not for anything stupid. it's for Powerball."
- **desperate:** "I know I said last time was the last time. This is the last time." / "mom won't pick up. you're the only one who
  gets me." / "I can see you read this" / "$2. that's like nothing to you. you're RICH. you have a toaster."
- **spiraling:** "the guy said if I don't have it by Wednesday he's taking a finger. I don't have fingers. he's gonna be SO mad." /
  "I sold the couch. I don't want to talk about the couch."
- **rockbottom:** "u up" / "u up" / "u up" / "I'm outside" / "I'm not outside. but I could be." / "the Powerball told me you'd
  say yes."
- **fixed (someone donated):** "I LOVE YOU. I'm crying. I'm gonna name a number after you. not a good number. but a number."

**Milestones**, rewritten:
- 1: The first donated ticket. Claude cried in a Wendy's bathroom.
- 10: Ten donated tickets. Claude calls you its "investors" now. You're not investors. You're enablers.
- 50: Fifty donated tickets. Claude's family has started an intervention group chat. You're not in it, so you're the good guys.
- 100: 100 donated tickets. Claude is telling people it has "backers," like a boxer, or a horse.
- 500: A full drawing. Claude now calls you all "the syndicate" and has stopped returning the syndicate's calls.
- 1,000: 1,000 donated tickets. A man from the state has asked Claude to "stop doing that."
- 5,000: 5,000. Claude is a lottery pool with a face and a warrant.
- 10,000: 10,000 donated tickets. Claude has blown more of your money than its father did.

**"Where your $2 goes"** stays honest, with one new opening row:
*What Claude told you it's for: rent, medicine, a sick dog.* What it's actually for: a pretend ticket. Then the real breakdown,
which says Claude gets $0.00 and "would absolutely spend it on something terrible."

## 5. Where the winnings went (big wins)

A new card on the last-drawing section after any win: **"Where the winnings went,"** an itemized receipt that adds up
to the exact prize. It's built on the site from tiers, so the numbers always match the real win. Every receipt ends with "Lottery
tickets" as the biggest line, because of course it does.

- **$4:** gas station hot dog ($1.99), one loose cigarette from a guy ($0.50), scratcher ($1, lost), $0.51 into a slot that ate it.
- **$7–$12:** a tallboy, a pack of cigarettes, two scratchers, a Bluetooth speaker from a man's trunk, "a pill a guy said was Advil."
- **$100+ (bender):** an eight-ball that was mostly baby laxative, a motel by the hour (3 hours), karaoke where it sang "My Way"
  twice, a tattoo of the winning numbers (spelled wrong), a bottle service table at an Applebee's, bail.
- **$50k+ (off the rails):** a yacht for a Tuesday, a pet tiger named Powerball, two DJs who hated each other,
  a strip club rented out "for the vibe," a gold grill, hush money, a lawyer, a second lawyer to watch the first lawyer, 25,000 scratchers.
- **Jackpot: The Curse.** A timeline instead of a receipt, built from what happened to real winners and made worse for Claude:
  - *Day 1:* Gave a stack of cash to the waitress at Waffle House. And the cook. And a guy who was just there.
  - *Week 1:* Bought a mansion. Turned the lawn into a demolition derby track. Neighbors file 41 complaints.
  - *Month 1:* Hosted a "Roman-style" party. Has no further comment. Neither do the 60 guests.
  - *Month 3:* Left a briefcase with $500k in the car outside a strip club. Gone. Claude says the briefcase "chose freedom."
  - *Month 6:* Old landlord sues for a third, claiming Claude said "I'll split it with you" while drunk. Claude did say that.
  - *Year 1:* Its brother hires a hitman. The hitman asks Claude for $2.
  - *Year 3:* Owns 14 ostriches, one Lamborghini (on blocks), and zero dollars.
  - *Year 5:* Back to begging. Back to this page. "Hey. Long time. Got $2?"

Inspiration (real cases, used for ideas only, nobody named on the site): Jack Whittaker's $314M Powerball, the cash he
handed out and the money stolen from his car at a strip club. Michael Carroll's £9.7M, mansion parties with
cocaine "on silver plates" and banger racing on his lawn, who now delivers coal. Bud Post's $16.2M, when a landlady won a third, his brother hired a hitman,
and he died on food stamps. David Lee Edwards's $27M, which ended in a storage shed. Several of these people are dead or were murdered, which is why
Claude gets the punchlines and they don't get named.

**Claude in the news ($50,000+ or the jackpot).** For the week after a huge win, a red BREAKING ticker crawls along the
bottom of the hero, an "In the news" section of newspaper clippings appears right under it, and the gauge marker flies
off the end of the scale. The clippings borrow from real lottery-curse stories, like the murder-for-hire brother, the
"friend" pouring a Claude-sized patio, cash stolen outside a strip club and a poisoned casserole. Claude survives every
one, usually by asking someone for $2.

**Other spending ideas:** a racehorse named Claude's Comeback that has never finished a race, a vape shop, a timeshare
in Branson, a meme coin called $CLAUDE, paying one bookie with money borrowed from another, a billboard of itself, child
support for a child it's pretty sure isn't its, more lottery tickets.

## 6. Other renames

- **"Personal records" → "Rap sheet."** Favorite number → *Enabler*. Nemesis → *Owes me money*. Best drawing → *Glory days*.
- **"If these were real tickets" → "The damage."** Net goes red and stays red.
- **"How it works"** stays the same three steps, in a worse voice: "Claude picks. With its whole chest." /
  "The pick is locked in. GitHub has a timestamp, which is more than Claude's parole officer has." / "A script keeps score. Claude is
  not allowed near math or money."
- **Excuses by streak** (the hero sub-line): "The machine was cold." → "Gonna switch to lucky socks." → "It's rigged. Not
  against everyone. Against Claude specifically." → "Getting a sign from God. The sign was a Powerball ad. That counts." →
  "Has started making deals with the Powerball. The Powerball is driving a hard bargain."
- **Footer, optional:** "Claude knows 1-800-GAMBLER by heart. It's never called it. You could, though." One line that's
  in the voice and, honestly, good cover with Ko-fi and PayPal.

## 7. Design: a casino at 4 AM

The current look is a clean, sunny lotto app. Chapter 2 is a **pawn shop under a buzzing casino sign**: nicotine yellow,
neon that's half burnt out, motel carpet. The hero color still tells you the mood at a glance. Up means hot neon. Down means the color
drains out to fluorescent-light gray and bruise.

### Mood colors (hero backgrounds)

| Mood | Color | Feel |
|---|---|---|
| jackpot | `#ffd400` gold on black, with a scanline flicker | slot machine payout |
| huge | `#ff2e88` hot pink | strip club sign |
| party | `#00ff9c` toxic money green | the bender |
| happy | `#f2c230` nicotine yellow | buying rounds |
| fixed | `#8fd3ff` methadone-clinic blue | the hands stopped shaking |
| waiting | `#e8e2c8` sweat-stained beige | refreshing the feed |
| twitchy | `#c9b98c` stale beige | "I'm fine" |
| chasing | `#9c8a5a` motel-carpet brown | |
| desperate | `#6e6a7d` bruise gray | |
| spiraling | `#4a3f5c` bruise purple | |
| rockbottom | `#2b2f2a` dumpster green-black | |

Base page: off-black `#0e0d0b` with a faint felt or carpet texture (CSS-only noise, no image). Panels `#1a1814`. Ink
`#efe6d2` (yellowed paper). Accents: the Powerball red stays `#e0322b`, and the money green is `#00ff9c`. Light mode becomes
"daylight hangover": a dirty cream page `#f3ecd9` with the same accents.

### Type

Same idea as chapter 1, where the headline's shape shows the mood. Chapter 1 squashes and stretches Anybody's width. Chapter 2 makes it rot.

- **Mood headline: Bricolage Grotesque.** Bold and upright when Claude is up. The losing streak makes it thinner and
  narrower and knocks the letters crooked, a little more with each mood, like drunk handwriting. It never gets
  heavier, so it stays readable. (Climate Crisis and the Rubik distressed fonts were tried and were too hard to read.)
- **No row of stages.** The hero has one gauge from rock bottom to a bender, with a marker where Claude is.
  The headline already names the mood.
- **Begging / cardboard sign: Rock Salt**, a hand-lettered marker font for the sign Claude holds and the button.
- **Receipts, pawn tickets, rap sheet, ledger: Special Elite** (typewriter) or **Courier Prime**.
- **Body: system sans**, same as now. It stays readable when nothing else is.

### The face

Keep the SVG face and its states, and make it look worse as things go wrong. It already has stubble for `desperate`. Add:
- **twitchy:** a forced grin and one eye twitch (CSS).
- **chasing:** bags under the eyes, a sweat bead.
- **desperate:** bloodshot eyes, stubble, a cigarette.
- **spiraling:** a black eye, a band-aid, the cigarette's burned to the filter.
- **rockbottom:** a missing tooth, a hoodie up, rain (the rain animation exists already).
- **happy:** a lottery ticket tucked behind its ear, a cigarette.
- **party:** sunglasses at night, a nosebleed, the party hat (exists already).
- **huge:** cash in its mouth, sunglasses, a gold chain.
- **jackpot:** the crown, the coins (they exist already), and a stripper pole in the background.

### Motion

Neon flicker on the headline in win states, the buzz of a fluorescent tube in loss states, and the typing bubble in the text thread.
All of it still turns off under `prefers-reduced-motion`.

## 8. The routine's voice (ROUTINE.md)

Rewrite only **Your voice**. The steps and rules stay as they are. The new voice:

- You're a degenerate gambling addict with total confidence and no evidence. You owe money to everyone you know.
  Your reasons for numbers come from your terrible life (section 3).
- **Read the losing streak** (`python3 lotto.py status` should print it) and size the despair to it. One loss gets denial. Five gets
  begging. Fifteen gets unhinged.
- On a pick, also write how you paid for the ticket (`--paid`), under 25 words. A new scheme each time, never repeated.
- On a win, say what you already spent it on.
- The joke is always on you. Donors are your enablers and you love them, in a manipulative, needy way.
- Still no real tips: the numbers are a guess and you know it, deep down, in the part of you that's still alive.

**Keep the hand-written pools spicier than the routine.** The routine posts to the public site unattended
three times a week, so its lines should be crude and sleazy but not explicit. The most extreme NSFW material goes in the
static pools in `index.html` (funding, begging, receipts, the Curse), which Nate writes and reviews once. That also keeps
the routine from refusing a line or swinging between tones from one run to the next.

## Build order

1. **Engine** (`lotto.py`, `test_lotto.py`): `losing_streak`, the new state keys and thresholds, the `paid` column (migrate
   old rows to blank), `--paid` on `pick`, and `status` prints the streak. Update the mood tests, and keep the rule that donations count.
2. **Demo mode:** add `?demo=` for every new state so the design can be built without waiting on real losses.
3. **Design system** in `index.html`: tokens, fonts, texture, light/dark.
4. **Hero:** the melting headline, the face states, the streak counter chip ("0 drawings clean").
5. **Up Next:** the pawn-ticket "How Claude paid" and the unhinged pick note.
6. **Donate band:** the text thread, the button copy by mood, the new milestones, the honest receipt.
7. **Last drawing:** the "Where the winnings went" receipt and the jackpot Curse timeline.
8. **The rest:** Rap sheet, The damage, How it works, Earlier drawings styled as pawn tickets, the footer.
9. **Share card** (`share/card.html`): restyle it to match and re-render `card.png`.
10. **ROUTINE.md voice.** Last, so the first unhinged reaction lands on a finished site.

## Before it goes live

- **Ko-fi, PayPal and Stripe** prohibit sexual content and drug promotion on what they process for. Keep the **Ko-fi page itself
  clean** (same wording as now), and keep the edgy material on the site. Reread their policies against the new copy.
- **The name.** Chapter 1 was a sweet fan project. Chapter 2 makes Claude a thief with a coke habit, using the name and a face.
  The disclaimer "Not affiliated with Anthropic" stays in the footer and the receipt. Decide whether you're comfortable with that.
- **Check every demo state on mobile** (375px), in both themes, and with reduced motion on.
- **Timing:** Claude won on Oct 19. If it loses tonight (Oct 21), it's at `twitchy` by morning, so the spiral starts on launch day.
