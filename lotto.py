#!/usr/bin/env python3
"""Claude's imaginary Powerball tickets: pick numbers, score them, keep the books.

    python3 lotto.py pick 07 19 23 41 58 11 --note "why"   add a ticket for the next drawing
    python3 lotto.py tips                                   how many donated tickets to pick next
    python3 lotto.py pick-tips FILE                         add those picks, one per line
    python3 lotto.py score                                  score finished drawings
    python3 lotto.py status                                 print the running totals

No real tickets are bought. ledger.csv is the record; stats.json is a summary for the site.
"""
import argparse
import csv
import json
import os
import sys
from time import sleep
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.csv"
STATS = ROOT / "stats.json"
FIELDS = ["draw_date", "ticket", "source", "picked_at", "pick", "note", "result", "match", "prize", "donation"]
SOURCES = ("claude", "tip")

ET = ZoneInfo("America/New_York")
DRAW_DAYS = {0, 2, 5}  # Mon, Wed, Sat
CUTOFF = time(22, 0)  # picks close at 10 PM ET; the drawing is at 10:59 PM ET
TICKET_COST = 2
RESULTS_URL = "https://data.ny.gov/resource/d6yy-54nr.json"  # NY Lottery's official Powerball results
# The Worker in worker/ that records Ko-fi donations. The environment variable overrides it for local testing.
DONATIONS_URL = os.environ.get("CLAUDE_PICKS_DONATIONS_URL", "https://claude-picks-donations.claude-picks.workers.dev")
TIP_CAP = 500  # donated tickets Claude picks per drawing; the rest wait for the next one
TIP_BATCH = 50  # donated tickets per pick-tips run, so each batch gets real attention

# (white balls matched, Powerball matched) -> prize in dollars
PRIZES = {
    (5, True): "JACKPOT",
    (5, False): 1_000_000,
    (4, True): 50_000,
    (4, False): 100,
    (3, True): 100,
    (3, False): 7,
    (2, True): 7,
    (1, True): 4,
    (0, True): 4,
}
BIG_WIN = 100  # a prize this size or bigger is a party
HUGE_WIN = 50_000  # and this size or bigger is huge; the jackpot is its own celebration
# Moods from a win, smallest to biggest. Each lasts a week after the drawing.
WIN_MOODS = ["happy", "party", "huge", "jackpot"]
# A win lifts the mood for a week; a month without one is sad, and two months is desperate.
MOOD_DAYS = {"glow": 7, "sad": 30, "desperate": 60}


def format_numbers(whites, pb):
    return " ".join(f"{n:02d}" for n in sorted(whites)) + f" | {pb:02d}"


def parse_numbers(text):
    whites, pb = text.split("|")
    return [int(n) for n in whites.split()], int(pb)


def validate(numbers):
    if len(numbers) != 6:
        raise ValueError("need 6 numbers: five white balls, then the Powerball")
    whites, pb = numbers[:5], numbers[5]
    if len(set(whites)) != 5:
        raise ValueError("the five white balls must all be different")
    if not all(1 <= n <= 69 for n in whites):
        raise ValueError("white balls must be between 1 and 69")
    if not 1 <= pb <= 26:
        raise ValueError("the Powerball must be between 1 and 26")
    return whites, pb


def next_draw(now):
    """The next drawing still open for picks at `now`, as a date."""
    now = now.astimezone(ET)
    day = now.date()
    if now.time() >= CUTOFF:
        day += timedelta(days=1)
    while day.weekday() not in DRAW_DAYS:
        day += timedelta(days=1)
    return day


def score_ticket(pick, result):
    """Returns (match, prize), e.g. ("3+PB", 100)."""
    whites, pb = parse_numbers(pick)
    result_whites, result_pb = parse_numbers(result)
    hits = len(set(whites) & set(result_whites))
    pb_hit = pb == result_pb
    match = f"{hits}+PB" if pb_hit else str(hits)
    return match, PRIZES.get((hits, pb_hit), 0)


def add_ticket(rows, numbers, note, source, now, donation=""):
    """Appends a ticket for the next drawing. Claude gets one ticket of its own per drawing."""
    whites, pb = validate(numbers)
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    draw = next_draw(now).isoformat()
    same_draw = [r for r in rows if r["draw_date"] == draw]
    if source == "claude" and any(r["source"] == "claude" for r in same_draw):
        raise ValueError(f"Claude already has a ticket for {draw}")
    row = {
        "draw_date": draw,
        "ticket": str(len(same_draw) + 1),
        "source": source,
        "picked_at": now.astimezone(ET).isoformat(timespec="seconds"),
        "pick": format_numbers(whites, pb),
        "note": note,
        "result": "",
        "match": "",
        "prize": "",
        "donation": donation,
    }
    rows.append(row)
    return row


def score_rows(rows, results):
    """Scores every unscored ticket whose drawing is in `results`. Returns the tickets scored."""
    scored = []
    for r in rows:
        if r["result"] or r["draw_date"] not in results:
            continue
        r["result"] = results[r["draw_date"]]
        r["match"], prize = score_ticket(r["pick"], r["result"])
        r["prize"] = str(prize)
        scored.append(r)
    return scored


def get_json(url):
    # Cloudflare turns away Python's default User-Agent, so name ourselves.
    request = urllib.request.Request(url, headers={"User-Agent": "claude-picks/1.0"})
    # data.ny.gov sometimes serves another site's certificate; a retry usually lands on a good server.
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.URLError:
            if attempt == 3:
                raise
            sleep(5 * (attempt + 1))


def fetch_results(since):
    """Winning numbers for every drawing on or after `since`, as {"2026-10-10": "01 04 19 33 51 | 15"}."""
    query = urllib.parse.urlencode({
        "$where": f"draw_date >= '{since}T00:00:00'",
        "$order": "draw_date",
        "$limit": 5000,
    })
    data = get_json(f"{RESULTS_URL}?{query}")
    results = {}
    for row in data:
        numbers = [int(n) for n in row["winning_numbers"].split()]
        results[row["draw_date"][:10]] = format_numbers(numbers[:5], numbers[5])
    return results


def donation_after(rows):
    """Donations are filled oldest first, so every one before the newest in the ledger is complete.
    The newest may still have tickets left, so fetching starts just before it."""
    seqs = [int(r["donation"].split(".")[0]) for r in rows if r.get("donation")]
    return max(seqs) - 1 if seqs else 0


def fetch_donations(after):
    """Donations from the Worker with seq > `after`, oldest first: [{"seq": 17, "tickets": 3, ...}]."""
    return get_json(f"{DONATIONS_URL}/donations?" + urllib.parse.urlencode({"after": after}))


def tips_due(rows, donations, now):
    """The drawing donated tickets go into at `now`, the donation slots Claude should pick for it
    (oldest first, up to the cap), and how many slots wait beyond that."""
    draw = next_draw(now).isoformat()
    filled = {r["donation"] for r in rows if r.get("donation")}
    open_slots = [f"{d['seq']}.{n}" for d in donations for n in range(1, d["tickets"] + 1)]
    open_slots = [s for s in open_slots if s not in filled]
    room = max(0, TIP_CAP - sum(1 for r in rows if r["draw_date"] == draw and r["source"] == "tip"))
    return draw, open_slots[:room], len(open_slots) - min(room, len(open_slots))


def add_tips(rows, picks, slots, now):
    """Adds one donated ticket per pick, filling `slots` in order. Picks in one drawing must all differ."""
    if len(picks) > TIP_BATCH:
        raise ValueError(f"{len(picks)} picks in one batch; add at most {TIP_BATCH} at a time")
    if len(picks) > len(slots):
        raise ValueError(f"{len(picks)} picks but only {len(slots)} donated tickets to fill")
    draw = next_draw(now).isoformat()
    taken = {r["pick"] for r in rows if r["draw_date"] == draw}
    new = []
    for numbers in picks:
        whites, pb = validate(numbers)
        pick = format_numbers(whites, pb)
        if pick in taken:
            raise ValueError(f"{pick} is already a ticket for {draw}; every pick needs to be different")
        taken.add(pick)
        new.append(numbers)
    return [add_ticket(rows, numbers, "", "tip", now, donation=slot) for numbers, slot in zip(new, slots)]


def read_picks(path):
    """Reads one pick per line, like "07 19 23 41 58 11" or "07 19 23 41 58 | 11". Skips blanks and # comments."""
    picks = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#")[0].replace("|", " ").strip()
        if line:
            picks.append([int(n) for n in line.split()])
    return picks


def totals(rows):
    scored = [r for r in rows if r["result"]]
    spent = TICKET_COST * len(scored)
    won = sum(int(r["prize"]) for r in scored if r["prize"] != "JACKPOT")
    return {
        "tickets": len(scored),
        "drawings": len({r["draw_date"] for r in scored}),
        "spent": spent,
        "won": won,
        "net": won - spent,
        "jackpots": sum(r["prize"] == "JACKPOT" for r in scored),
    }


def win_mood(prize):
    """The celebration a winning prize earns: jackpot, huge, party, or happy for anything smaller."""
    if prize == "JACKPOT":
        return "jackpot"
    return "huge" if int(prize) >= HUGE_WIN else "party" if int(prize) >= BIG_WIN else "happy"


def mood(rows, today):
    """How Claude feels. A win in the past week sets the mood by its size (happy, party, huge, jackpot).
    Otherwise a drawing with every donated spot filled makes Claude happy, and a month without a win
    makes it sad (two months, desperate), unless donated tickets are waiting on a drawing, which keeps
    it hopeful."""
    waiting = [r for r in rows if not r["result"] and r["source"] == "tip"]
    tips_waiting = len(waiting)
    full = any(sum(r["draw_date"] == d for r in waiting) >= TIP_CAP for d in {r["draw_date"] for r in waiting})
    scored = [r for r in rows if r["result"]]
    wins = [r for r in scored if r["prize"] != "0"]

    def days_ago(r):
        return (today - date.fromisoformat(r["draw_date"])).days

    recent_wins = [r for r in wins if days_ago(r) <= MOOD_DAYS["glow"]]
    days_since_win = min(days_ago(r) for r in wins) if wins else None

    def dry_for(days):
        """Claude has been playing at least `days` and hasn't won in that time."""
        return max(days_ago(r) for r in scored) >= days and (days_since_win is None or days_since_win >= days)

    if recent_wins:
        state = max((win_mood(r["prize"]) for r in recent_wins), key=WIN_MOODS.index)
    elif full:
        state = "happy"
    elif tips_waiting:
        state = "hopeful"
    elif scored and dry_for(MOOD_DAYS["desperate"]):
        state = "desperate"
    elif scored and dry_for(MOOD_DAYS["sad"]):
        state = "sad"
    else:
        state = "hopeful"
    return {"state": state, "days_since_win": days_since_win, "tips_waiting": tips_waiting, "full": full}


def drawing_summaries(rows, limit=12):
    """The latest drawings, newest first: how every ticket did on the day (spent, won, net), with
    donated tickets added up instead of listed."""
    scored = [r for r in rows if r["result"]]
    dates = sorted({r["draw_date"] for r in scored}, reverse=True)[:limit]
    out = []
    for d in dates:
        day = [r for r in scored if r["draw_date"] == d]
        tips = [r for r in day if r["source"] == "tip"]
        t = totals(tips)
        out.append({
            "draw_date": d,
            "result": day[0]["result"],
            **{k: v for k, v in totals(day).items() if k in ("tickets", "spent", "won", "net", "jackpots")},
            "tip_tickets": t["tickets"],
            "tip_wins": sum(r["prize"] != "0" for r in tips),
            "tip_won": t["won"],
            "tip_jackpots": t["jackpots"],
        })
    return out


def upcoming_tips(rows):
    """Donated tickets waiting on a drawing, grouped by drawing with just their numbers."""
    groups = {}
    for r in rows:
        if not r["result"] and r["source"] == "tip":
            group = groups.setdefault(r["draw_date"], {"draw_date": r["draw_date"], "picked_at": r["picked_at"], "picks": []})
            group["picks"].append(r["pick"])
    return sorted(groups.values(), key=lambda g: g["draw_date"])


def best_win(rows, today):
    """The biggest win of the past week (the latest, on a tie), which the site's mood line brags about."""
    wins = [
        r for r in rows
        if r["result"] and r["prize"] != "0" and (today - date.fromisoformat(r["draw_date"])).days <= MOOD_DAYS["glow"]
    ]
    if not wins:
        return None
    best = max(wins, key=lambda r: (r["prize"] == "JACKPOT", 0 if r["prize"] == "JACKPOT" else int(r["prize"]), r["draw_date"]))
    return {"draw_date": best["draw_date"], "prize": best["prize"], "source": best["source"]}


def build_stats(rows, now):
    # Donated tickets can run to 500 a drawing, so the site gets them added up per drawing, the numbers
    # of the ones still waiting, and the winners from the latest drawing. The ledger has every ticket.
    summaries = drawing_summaries(rows)
    shown = {d["draw_date"] for d in summaries}
    latest = summaries[0]["draw_date"] if summaries else None
    recent = [
        r for r in rows
        if r["result"] and r["draw_date"] in shown
        and (r["source"] == "claude" or (r["draw_date"] == latest and r["prize"] != "0"))
    ]
    return {
        "updated_at": now.astimezone(ET).isoformat(timespec="seconds"),
        "ticket_cost": TICKET_COST,
        "tip_cap": TIP_CAP,
        "mood": mood(rows, now.astimezone(ET).date()),
        "first_draw": min((r["draw_date"] for r in rows), default=None),
        "totals": totals(rows),
        "by_source": {s: totals([r for r in rows if r["source"] == s]) for s in SOURCES},
        "best_win": best_win(rows, now.astimezone(ET).date()),
        "upcoming": [r for r in rows if not r["result"] and r["source"] != "tip"],
        "upcoming_tips": upcoming_tips(rows),
        "recent": recent[::-1],
        "drawings": summaries,
    }


def money(n):
    return f"-${-n:,}" if n < 0 else f"${n:,}"


def status_text(rows):
    t = totals(rows)
    m = mood(rows, datetime.now(ET).date())
    since = "no wins yet" if m["days_since_win"] is None else f"{m['days_since_win']} days since a win"
    lines = [
        f"Lifetime: {t['tickets']} tickets scored, spent {money(t['spent'])}, "
        f"won {money(t['won'])}, net {money(t['net'])}.",
        f"Claude's mood: {m['state']} ({since}).",
    ]
    if t["jackpots"]:
        lines.append(f"JACKPOT x{t['jackpots']}: look up that night's cash value; it isn't counted above.")
    upcoming = [r for r in rows if not r["result"]]
    for draw in sorted({r["draw_date"] for r in upcoming}):
        picks = [r for r in upcoming if r["draw_date"] == draw]
        own = [r["pick"] for r in picks if r["source"] != "tip"]
        line = f"Waiting on {draw}: " + (", ".join(own) or "no ticket of Claude's own")
        if len(picks) > len(own):
            line += f", plus {len(picks) - len(own)} donated tickets"
        lines.append(line)
    return "\n".join(lines)


def read_ledger():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as f:
        # Rows from before a column existed read it as empty.
        return [{k: r.get(k) or "" for k in FIELDS} for r in csv.DictReader(f)]


def save(rows, now):
    with LEDGER.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    STATS.write_text(json.dumps(build_stats(rows, now), indent=2) + "\n")


def cmd_pick(args):
    now = datetime.now(ET)
    rows = read_ledger()
    row = add_ticket(rows, args.numbers, args.note, args.source, now)
    save(rows, now)
    print(f"Ticket {row['ticket']} for {row['draw_date']}: {row['pick']}")


def load_tips(rows, now):
    if not DONATIONS_URL:
        return None
    return tips_due(rows, fetch_donations(donation_after(rows)), now)


def cmd_tips(args):
    now = datetime.now(ET)
    due = load_tips(read_ledger(), now)
    if due is None:
        print("Donations aren't open yet. Nothing to pick.")
        return
    draw, slots, waiting = due
    print(f"Pick {len(slots)} donated tickets for {draw}" + (f", {TIP_BATCH} at a time." if len(slots) > TIP_BATCH else "."))
    if waiting:
        print(f"{waiting} more donated tickets are waiting for later drawings ({TIP_CAP} a drawing).")


def cmd_pick_tips(args):
    now = datetime.now(ET)
    rows = read_ledger()
    picks = read_picks(args.file)
    due = load_tips(rows, now)
    if due is None:
        raise ValueError("donations aren't open yet")
    draw, slots, _ = due
    added = add_tips(rows, picks, slots, now)
    save(rows, now)
    print(f"Added {len(added)} donated tickets for {draw}.")
    if len(slots) > len(added):
        print(f"{len(slots) - len(added)} more are due for {draw}. Run `tips` again.")


def cmd_score(args):
    now = datetime.now(ET)
    rows = read_ledger()
    pending = sorted(r["draw_date"] for r in rows if not r["result"])
    # Always fetch at least the past week, so every run reports the latest drawing.
    since = min(pending + [(now.date() - timedelta(days=7)).isoformat()])
    results = fetch_results(since)
    scored = score_rows(rows, results)
    # Claude's own tickets and every winner get a line; donated losers are only counted.
    for r in scored:
        if r["source"] == "claude" or r["prize"] != "0":
            print(f"{r['draw_date']} ticket {r['ticket']} ({r['source']}): {r['pick']} vs {r['result']} -> {r['match']}, {r['prize']}")
    for draw in sorted({r["draw_date"] for r in scored if r["source"] == "tip"}):
        tips = [r for r in scored if r["draw_date"] == draw and r["source"] == "tip"]
        print(f"{draw}: {len(tips)} donated tickets, {sum(r['prize'] != '0' for r in tips)} won {money(totals(tips)['won'])}.")
    if results:
        latest = max(results)
        print(f"Latest drawing: {latest}: {results[latest]}")
    save(rows, now)
    print(status_text(rows))


def cmd_status(args):
    print(status_text(read_ledger()))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    pick = sub.add_parser("pick", help="add a ticket for the next drawing")
    pick.add_argument("numbers", type=int, nargs="+", help="five white balls, then the Powerball")
    pick.add_argument("--note", default="", help="why these numbers")
    pick.add_argument("--source", default="claude", choices=SOURCES)
    pick.set_defaults(func=cmd_pick)
    sub.add_parser("tips", help="how many donated tickets to pick for the next drawing").set_defaults(func=cmd_tips)
    pick_tips = sub.add_parser("pick-tips", help="add donated tickets from a file, one pick per line")
    pick_tips.add_argument("file")
    pick_tips.set_defaults(func=cmd_pick_tips)
    sub.add_parser("score", help="score finished drawings").set_defaults(func=cmd_score)
    sub.add_parser("status", help="print running totals").set_defaults(func=cmd_status)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, urllib.error.URLError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
