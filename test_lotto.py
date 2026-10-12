import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import lotto

ET = lotto.ET


def et(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


class ScoreTicket(unittest.TestCase):
    RESULT = "01 04 19 33 51 | 15"  # the real drawing on 2026-10-10

    def check(self, pick, match, prize):
        self.assertEqual(lotto.score_ticket(pick, self.RESULT), (match, prize))

    def test_every_tier(self):
        self.check("01 04 19 33 51 | 15", "5+PB", "JACKPOT")
        self.check("01 04 19 33 51 | 16", "5", 1_000_000)
        self.check("01 04 19 33 60 | 15", "4+PB", 50_000)
        self.check("01 04 19 33 60 | 16", "4", 100)
        self.check("01 04 19 60 61 | 15", "3+PB", 100)
        self.check("01 04 19 60 61 | 16", "3", 7)
        self.check("01 04 60 61 62 | 15", "2+PB", 7)
        self.check("01 60 61 62 63 | 15", "1+PB", 4)
        self.check("60 61 62 63 64 | 15", "0+PB", 4)

    def test_non_winners(self):
        self.check("01 04 60 61 62 | 16", "2", 0)
        self.check("01 60 61 62 63 | 16", "1", 0)
        self.check("60 61 62 63 64 | 16", "0", 0)

    def test_powerball_number_in_white_balls_does_not_count(self):
        # 15 is the Powerball, so picking it as a white ball is not a white-ball hit.
        self.check("15 60 61 62 63 | 01", "0", 0)

    def test_order_does_not_matter(self):
        self.check("51 33 19 04 01 | 15", "5+PB", "JACKPOT")


class Validate(unittest.TestCase):
    def test_good_pick(self):
        self.assertEqual(lotto.validate([7, 19, 23, 41, 58, 11]), ([7, 19, 23, 41, 58], 11))
        self.assertEqual(lotto.validate([1, 2, 3, 4, 69, 26]), ([1, 2, 3, 4, 69], 26))

    def test_bad_picks(self):
        for numbers in (
            [1, 2, 3, 4, 5],  # too few
            [1, 2, 3, 4, 5, 6, 7],  # too many
            [1, 1, 2, 3, 4, 5],  # repeated white ball
            [0, 2, 3, 4, 5, 6],  # white ball too low
            [1, 2, 3, 4, 70, 6],  # white ball too high
            [1, 2, 3, 4, 5, 0],  # Powerball too low
            [1, 2, 3, 4, 5, 27],  # Powerball too high
        ):
            with self.subTest(numbers=numbers), self.assertRaises(ValueError):
                lotto.validate(numbers)


class NextDraw(unittest.TestCase):
    def test_draw_days(self):
        cases = [
            (et(2026, 10, 12, 9), date(2026, 10, 12)),  # Mon morning -> tonight
            (et(2026, 10, 12, 21, 59), date(2026, 10, 12)),  # Mon just before cutoff -> tonight
            (et(2026, 10, 12, 22, 0), date(2026, 10, 14)),  # Mon at cutoff -> Wed
            (et(2026, 10, 13, 12), date(2026, 10, 14)),  # Tue -> Wed
            (et(2026, 10, 15, 12), date(2026, 10, 17)),  # Thu -> Sat
            (et(2026, 10, 17, 23), date(2026, 10, 19)),  # Sat after cutoff -> Mon
            (et(2026, 10, 18, 12), date(2026, 10, 19)),  # Sun -> Mon
        ]
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(lotto.next_draw(now), expected)

    def test_uses_eastern_time(self):
        # 01:30 UTC Monday is still Sunday evening in New York.
        self.assertEqual(lotto.next_draw(datetime(2026, 10, 12, 1, 30, tzinfo=timezone.utc)), date(2026, 10, 12))
        # 02:30 UTC Tuesday is 10:30 PM Monday in New York: past the cutoff.
        self.assertEqual(lotto.next_draw(datetime(2026, 10, 13, 2, 30, tzinfo=timezone.utc)), date(2026, 10, 14))

    def test_standard_time(self):
        # After DST ends (Nov 1, 2026) New York is UTC-5: 02:30 UTC Tuesday is 9:30 PM Monday.
        self.assertEqual(lotto.next_draw(datetime(2026, 11, 3, 2, 30, tzinfo=timezone.utc)), date(2026, 11, 2))


class AddTicket(unittest.TestCase):
    NOW = et(2026, 10, 12, 18)

    def test_adds_ticket_for_tonight(self):
        rows = []
        row = lotto.add_ticket(rows, [58, 7, 41, 19, 23, 11], "hunch", "claude", self.NOW)
        self.assertEqual(rows, [row])
        self.assertEqual(row["draw_date"], "2026-10-12")
        self.assertEqual(row["ticket"], "1")
        self.assertEqual(row["pick"], "07 19 23 41 58 | 11")
        self.assertEqual(row["picked_at"], "2026-10-12T18:00:00-04:00")
        self.assertEqual(row["result"], "")

    def test_claude_gets_one_ticket_per_drawing(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW)
        with self.assertRaises(ValueError):
            lotto.add_ticket(rows, [7, 8, 9, 10, 11, 12], "", "claude", self.NOW)
        self.assertEqual(len(rows), 1)

    def test_tip_tickets_stack(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW)
        lotto.add_ticket(rows, [7, 8, 9, 10, 11, 12], "", "tip", self.NOW)
        lotto.add_ticket(rows, [13, 14, 15, 16, 17, 18], "", "tip", self.NOW)
        self.assertEqual([r["ticket"] for r in rows], ["1", "2", "3"])

    def test_next_drawing_numbers_from_one(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW)
        row = lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", et(2026, 10, 13, 18))
        self.assertEqual((row["draw_date"], row["ticket"]), ("2026-10-14", "1"))

    def test_rejects_bad_source(self):
        with self.assertRaises(ValueError):
            lotto.add_ticket([], [1, 2, 3, 4, 5, 6], "", "someone", self.NOW)


class ScoreRowsAndTotals(unittest.TestCase):
    def rows(self):
        rows = []
        lotto.add_ticket(rows, [1, 60, 61, 62, 63, 15], "", "claude", et(2026, 10, 10, 18))  # 1+PB, $4
        lotto.add_ticket(rows, [1, 4, 19, 33, 51, 15], "", "tip", et(2026, 10, 10, 18))  # jackpot
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", et(2026, 10, 12, 18))  # not drawn yet
        return rows

    def test_scores_only_drawings_with_results(self):
        rows = self.rows()
        scored = lotto.score_rows(rows, {"2026-10-10": "01 04 19 33 51 | 15"})
        self.assertEqual(len(scored), 2)
        self.assertEqual((rows[0]["match"], rows[0]["prize"]), ("1+PB", "4"))
        self.assertEqual((rows[1]["match"], rows[1]["prize"]), ("5+PB", "JACKPOT"))
        self.assertEqual(rows[2]["result"], "")

    def test_scoring_twice_changes_nothing(self):
        rows = self.rows()
        results = {"2026-10-10": "01 04 19 33 51 | 15"}
        lotto.score_rows(rows, results)
        self.assertEqual(lotto.score_rows(rows, results), [])

    def test_totals_count_only_scored_tickets(self):
        rows = self.rows()
        lotto.score_rows(rows, {"2026-10-10": "01 04 19 33 51 | 15"})
        self.assertEqual(lotto.totals(rows), {"tickets": 2, "spent": 4, "won": 4, "net": 0, "jackpots": 1})
        stats = lotto.build_stats(rows, et(2026, 10, 12, 18))
        self.assertEqual(stats["by_source"]["claude"]["won"], 4)
        self.assertEqual(stats["by_source"]["tip"]["jackpots"], 1)
        self.assertEqual(len(stats["upcoming"]), 1)
        self.assertEqual(len(stats["recent"]), 2)


class Mood(unittest.TestCase):
    TODAY = date(2026, 12, 1)

    def ticket(self, draw_date, prize, source="claude"):
        return {"draw_date": draw_date, "source": source, "result": "01 02 03 04 05 | 06", "prize": prize}

    def upcoming(self, source):
        return {"draw_date": "2026-12-02", "source": source, "result": "", "prize": ""}

    def check(self, rows, state, days_since_win, tips_waiting=0):
        self.assertEqual(
            lotto.mood(rows, self.TODAY),
            {"state": state, "days_since_win": days_since_win, "tips_waiting": tips_waiting},
        )

    def test_no_tickets_yet(self):
        self.check([], "hopeful", None)
        self.check([self.upcoming("claude")], "hopeful", None)

    def test_small_win_this_week_is_happy(self):
        self.check([self.ticket("2026-10-01", "0"), self.ticket("2026-11-28", "4")], "happy", 3)

    def test_big_win_this_week_is_a_party(self):
        self.check([self.ticket("2026-11-28", "100")], "party", 3)
        self.check([self.ticket("2026-11-24", "JACKPOT")], "party", 7)

    def test_wins_fade_after_a_week(self):
        self.check([self.ticket("2026-11-23", "50000")], "hopeful", 8)

    def test_month_without_a_win_is_sad(self):
        self.check([self.ticket("2026-10-31", "7"), self.ticket("2026-11-30", "0")], "sad", 31)
        self.check([self.ticket("2026-10-31", "0"), self.ticket("2026-11-30", "0")], "sad", None)

    def test_tip_ticket_gives_a_sad_claude_hope(self):
        month_of_losses = [self.ticket("2026-10-31", "0"), self.ticket("2026-11-30", "0")]
        self.check(month_of_losses + [self.upcoming("claude")], "sad", None)
        tipped = month_of_losses + [self.upcoming("claude"), self.upcoming("tip"), self.upcoming("tip")]
        self.check(tipped, "hopeful", None, tips_waiting=2)

    def test_hope_ends_when_the_tip_ticket_loses(self):
        rows = [self.ticket("2026-10-31", "0"), self.ticket("2026-11-30", "0", source="tip")]
        self.check(rows, "sad", None)

    def test_tips_do_not_dampen_a_party(self):
        self.check([self.ticket("2026-11-28", "100"), self.upcoming("tip")], "party", 3, tips_waiting=1)

    def test_too_new_to_be_sad(self):
        self.check([self.ticket("2026-11-15", "0"), self.ticket("2026-11-30", "0")], "hopeful", None)


class LedgerFile(unittest.TestCase):
    def test_round_trip(self):
        self.addCleanup(setattr, lotto, "LEDGER", lotto.LEDGER)
        self.addCleanup(setattr, lotto, "STATS", lotto.STATS)
        with tempfile.TemporaryDirectory() as tmp:
            lotto.LEDGER = Path(tmp) / "ledger.csv"
            lotto.STATS = Path(tmp) / "stats.json"
            now = et(2026, 10, 12, 18)
            rows = lotto.read_ledger()
            self.assertEqual(rows, [])
            lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], 'commas, "quotes"', "claude", now)
            lotto.save(rows, now)
            self.assertEqual(lotto.read_ledger(), rows)
            self.assertTrue(lotto.STATS.exists())


if __name__ == "__main__":
    unittest.main()
