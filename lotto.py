#!/usr/bin/env python3
"""Claude's imaginary Powerball tickets: pick numbers, score them, keep the books.

    python3 lotto.py pick 07 19 23 41 58 11 --note "why"   add a ticket for the next drawing
    python3 lotto.py score                                  score finished drawings
    python3 lotto.py status                                 print the running totals

No real tickets are bought. ledger.csv is the record; stats.json is a summary for the site.
"""
import argparse
import csv
import json
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
FIELDS = ["draw_date", "ticket", "source", "picked_at", "pick", "note", "result", "match", "prize"]
SOURCES = ("claude", "tip")

ET = ZoneInfo("America/New_York")
DRAW_DAYS = {0, 2, 5}  # Mon, Wed, Sat
CUTOFF = time(22, 0)  # picks close at 10 PM ET; the drawing is at 10:59 PM ET
TICKET_COST = 2
RESULTS_URL = "https://data.ny.gov/resource/d6yy-54nr.json"  # NY Lottery's official Powerball results

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
MOOD_DAYS = {"glow": 7, "sad": 30}  # a win lifts the mood for a week; a month without one is sad


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


def add_ticket(rows, numbers, note, source, now):
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


def fetch_results(since):
    """Winning numbers for every drawing on or after `since`, as {"2026-10-10": "01 04 19 33 51 | 15"}."""
    query = urllib.parse.urlencode({
        "$where": f"draw_date >= '{since}T00:00:00'",
        "$order": "draw_date",
        "$limit": 5000,
    })
    # data.ny.gov sometimes serves another site's certificate; a retry usually lands on a good server.
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{RESULTS_URL}?{query}", timeout=30) as resp:
                data = json.load(resp)
            break
        except urllib.error.URLError:
            if attempt == 3:
                raise
            sleep(5 * (attempt + 1))
    results = {}
    for row in data:
        numbers = [int(n) for n in row["winning_numbers"].split()]
        results[row["draw_date"][:10]] = format_numbers(numbers[:5], numbers[5])
    return results


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


def is_big(prize):
    return prize == "JACKPOT" or int(prize) >= BIG_WIN


def mood(rows, today):
    """How Claude feels: party after a big win, happy after any win, sad after a month without one.
    A tip ticket waiting on a drawing turns sad into hopeful until that drawing is scored."""
    tips_waiting = sum(1 for r in rows if not r["result"] and r["source"] == "tip")
    scored = [r for r in rows if r["result"]]
    if not scored:
        return {"state": "hopeful", "days_since_win": None, "tips_waiting": tips_waiting}
    wins = [r for r in scored if r["prize"] != "0"]

    def days_ago(r):
        return (today - date.fromisoformat(r["draw_date"])).days

    recent_wins = [r for r in wins if days_ago(r) <= MOOD_DAYS["glow"]]
    days_since_win = min(days_ago(r) for r in wins) if wins else None
    if any(is_big(r["prize"]) for r in recent_wins):
        state = "party"
    elif recent_wins:
        state = "happy"
    elif max(days_ago(r) for r in scored) >= MOOD_DAYS["sad"] and (
        days_since_win is None or days_since_win >= MOOD_DAYS["sad"]
    ):
        state = "hopeful" if tips_waiting else "sad"
    else:
        state = "hopeful"
    return {"state": state, "days_since_win": days_since_win, "tips_waiting": tips_waiting}


def build_stats(rows, now):
    scored = [r for r in rows if r["result"]]
    return {
        "updated_at": now.astimezone(ET).isoformat(timespec="seconds"),
        "ticket_cost": TICKET_COST,
        "mood": mood(rows, now.astimezone(ET).date()),
        "first_draw": min((r["draw_date"] for r in rows), default=None),
        "totals": totals(rows),
        "by_source": {s: totals([r for r in rows if r["source"] == s]) for s in SOURCES},
        "upcoming": [r for r in rows if not r["result"]],
        "recent": scored[::-1][:30],
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
        lines.append(f"Waiting on {draw}: " + ", ".join(r["pick"] for r in picks))
    return "\n".join(lines)


def read_ledger():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as f:
        return list(csv.DictReader(f))


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


def cmd_score(args):
    now = datetime.now(ET)
    rows = read_ledger()
    pending = sorted(r["draw_date"] for r in rows if not r["result"])
    # Always fetch at least the past week, so every run reports the latest drawing.
    since = min(pending + [(now.date() - timedelta(days=7)).isoformat()])
    results = fetch_results(since)
    for r in score_rows(rows, results):
        print(f"{r['draw_date']} ticket {r['ticket']}: {r['pick']} vs {r['result']} -> {r['match']}, {r['prize']}")
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
    sub.add_parser("score", help="score finished drawings").set_defaults(func=cmd_score)
    sub.add_parser("status", help="print running totals").set_defaults(func=cmd_status)
    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
