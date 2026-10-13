import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import lotto

ET = lotto.ET


def et(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


def drawn(numbers, multiplier=2, double_play="01 29 34 39 62 | 14"):
    """One drawing as fetch_results returns it."""
    return {"numbers": numbers, "multiplier": multiplier, "double_play": double_play}


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
        scored = lotto.score_rows(rows, {"2026-10-10": drawn("01 04 19 33 51 | 15")})
        self.assertEqual(len(scored), 2)
        self.assertEqual((rows[0]["match"], rows[0]["prize"]), ("1+PB", "4"))
        self.assertEqual((rows[1]["match"], rows[1]["prize"]), ("5+PB", "JACKPOT"))
        self.assertEqual(rows[2]["result"], "")

    def test_scoring_twice_changes_nothing(self):
        rows = self.rows()
        results = {"2026-10-10": drawn("01 04 19 33 51 | 15")}
        lotto.score_rows(rows, results)
        self.assertEqual(lotto.score_rows(rows, results), [])

    def test_totals_count_only_scored_tickets(self):
        rows = self.rows()
        lotto.score_rows(rows, {"2026-10-10": drawn("01 04 19 33 51 | 15")})
        self.assertEqual(
            lotto.totals(rows), {"tickets": 2, "drawings": 1, "spent": 4, "won": 4, "net": 0, "jackpots": 1}
        )
        stats = lotto.build_stats(rows, et(2026, 10, 12, 18))
        self.assertEqual(stats["first_draw"], "2026-10-10")
        self.assertEqual(stats["by_source"]["claude"]["won"], 4)
        self.assertEqual(stats["by_source"]["tip"]["jackpots"], 1)
        self.assertEqual(len(stats["upcoming"]), 1)
        self.assertEqual(len(stats["recent"]), 2)


class AddOns(unittest.TestCase):
    NOW = et(2026, 10, 10, 18)
    RESULT = "01 04 19 33 51 | 15"
    DOUBLE_PLAY = "01 29 34 39 62 | 14"

    def claude_ticket(self, numbers, multiplier=2):
        rows = []
        lotto.add_ticket(rows, numbers, "", "claude", self.NOW, options=lotto.CLAUDE_OPTIONS)
        lotto.score_rows(rows, {"2026-10-10": drawn(self.RESULT, multiplier, self.DOUBLE_PLAY)})
        return rows[0]

    def test_power_play_multiplies_the_main_prize(self):
        r = self.claude_ticket([1, 60, 61, 62, 63, 15], multiplier=3)  # 1+PB: $4
        self.assertEqual((r["match"], r["prize"], r["multiplier"]), ("1+PB", "12", "3"))

    def test_power_play_match_5_is_a_flat_two_million(self):
        self.assertEqual(self.claude_ticket([1, 4, 19, 33, 51, 20], multiplier=10)["prize"], "2000000")

    def test_power_play_leaves_the_jackpot_and_losses_alone(self):
        self.assertEqual(self.claude_ticket([1, 4, 19, 33, 51, 15], multiplier=5)["prize"], "JACKPOT")
        self.assertEqual(self.claude_ticket([60, 61, 62, 63, 64, 20], multiplier=5)["prize"], "0")

    def test_double_play_is_scored_on_its_own_numbers_and_table(self):
        # Misses the main drawing; hits 29 34 39 62 plus Powerball 14 in Double Play: $50,000.
        r = self.claude_ticket([29, 34, 39, 62, 66, 14])
        self.assertEqual((r["match"], r["prize"]), ("0", "0"))
        self.assertEqual((r["dp_result"], r["dp_match"], r["dp_prize"]), (self.DOUBLE_PLAY, "4+PB", "50000"))
        self.assertEqual(lotto.winnings(r), 50_000)

    def test_both_drawings_add_up(self):
        # Main: 1+PB, $4 x2 = $8. Double Play: 01 and 29 hit without the Powerball, which pays nothing.
        r = self.claude_ticket([1, 29, 60, 61, 63, 15])
        self.assertEqual((r["prize"], r["dp_prize"], lotto.winnings(r)), ("8", "0", 8))

    def test_add_on_ticket_costs_four_dollars(self):
        r = self.claude_ticket([60, 61, 62, 63, 64, 20])
        self.assertEqual(lotto.ticket_cost(r), 4)
        self.assertEqual(lotto.totals([r])["spent"], 4)

    def test_plain_ticket_ignores_add_ons(self):
        rows = []
        lotto.add_ticket(rows, [1, 60, 61, 62, 63, 15], "", "tip", self.NOW)
        lotto.score_rows(rows, {"2026-10-10": drawn(self.RESULT, 5, self.DOUBLE_PLAY)})
        self.assertEqual((rows[0]["prize"], rows[0]["multiplier"], rows[0]["dp_prize"]), ("4", "", ""))
        self.assertEqual(lotto.ticket_cost(rows[0]), 2)

    def test_waits_for_double_play_numbers(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW, options=lotto.CLAUDE_OPTIONS)
        self.assertEqual(lotto.score_rows(rows, {"2026-10-10": drawn(self.RESULT, 2, "")}), [])
        self.assertEqual(rows[0]["result"], "")

    def test_a_double_play_win_counts_for_the_mood(self):
        r = self.claude_ticket([29, 34, 39, 62, 66, 14])  # $50,000 in Double Play
        self.assertEqual(lotto.mood([r], date(2026, 10, 12))["state"], "huge")

    def test_fetch_results_reads_multiplier_and_double_play(self):
        self.addCleanup(setattr, lotto, "get_json", lotto.get_json)
        lotto.get_json = lambda url: [{
            "draw_date": "2026-10-10T00:00:00.000", "winning_numbers": "01 04 19 33 51 15",
            "multiplier": "2", "double_play_winning_numbers": "01 29 34 39 62 14",
        }]
        self.assertEqual(lotto.fetch_results("2026-10-10"), {"2026-10-10": drawn(self.RESULT, 2, self.DOUBLE_PLAY)})


class Mood(unittest.TestCase):
    TODAY = date(2026, 12, 1)

    def ticket(self, draw_date, prize, source="claude"):
        return {"draw_date": draw_date, "source": source, "result": "01 02 03 04 05 | 06", "prize": prize}

    def upcoming(self, source):
        return {"draw_date": "2026-12-02", "source": source, "result": "", "prize": ""}

    def check(self, rows, state, days_since_win, tips_waiting=0, full=False):
        self.assertEqual(
            lotto.mood(rows, self.TODAY),
            {"state": state, "days_since_win": days_since_win, "tips_waiting": tips_waiting, "full": full},
        )

    def full_drawing(self):
        return [self.upcoming("tip") for _ in range(lotto.TIP_CAP)]

    def test_no_tickets_yet(self):
        self.check([], "hopeful", None)
        self.check([self.upcoming("claude")], "hopeful", None)

    def test_small_win_this_week_is_happy(self):
        self.check([self.ticket("2026-10-01", "0"), self.ticket("2026-11-28", "4")], "happy", 3)

    def test_big_win_this_week_is_a_party(self):
        self.check([self.ticket("2026-11-28", "100")], "party", 3)
        self.check([self.ticket("2026-11-24", "100")], "party", 7)  # still a party on day 7

    def test_bigger_wins_get_bigger_celebrations(self):
        self.check([self.ticket("2026-11-28", "50000")], "huge", 3)
        self.check([self.ticket("2026-11-28", "1000000")], "huge", 3)
        self.check([self.ticket("2026-11-28", "JACKPOT", source="tip")], "jackpot", 3)
        # The biggest win of the week sets the mood, whatever order they came in.
        self.check([self.ticket("2026-11-26", "50000"), self.ticket("2026-11-28", "100")], "huge", 3)
        self.check([self.ticket("2026-11-26", "JACKPOT"), self.ticket("2026-11-28", "50000")], "jackpot", 3)

    def test_a_full_drawing_of_donated_tickets_is_happy(self):
        self.check(self.full_drawing(), "happy", None, tips_waiting=lotto.TIP_CAP, full=True)
        # Even after a month of losses.
        losses = [self.ticket("2026-10-31", "0"), self.ticket("2026-11-30", "0")]
        self.check(losses + self.full_drawing(), "happy", None, tips_waiting=lotto.TIP_CAP, full=True)
        # One short of full is only hopeful.
        self.check(losses + self.full_drawing()[1:], "hopeful", None, tips_waiting=lotto.TIP_CAP - 1)

    def test_a_win_beats_a_full_drawing(self):
        self.check([self.ticket("2026-11-28", "100")] + self.full_drawing(), "party", 3, tips_waiting=lotto.TIP_CAP, full=True)

    def test_wins_fade_after_a_week(self):
        self.check([self.ticket("2026-11-23", "50000")], "hopeful", 8)

    def test_month_without_a_win_is_sad(self):
        self.check([self.ticket("2026-10-31", "7"), self.ticket("2026-11-30", "0")], "sad", 31)
        self.check([self.ticket("2026-10-31", "0"), self.ticket("2026-11-30", "0")], "sad", None)

    def test_two_months_without_a_win_is_desperate(self):
        self.check([self.ticket("2026-09-30", "0"), self.ticket("2026-11-30", "0")], "desperate", None)
        self.check([self.ticket("2026-09-30", "7"), self.ticket("2026-11-30", "0")], "desperate", 62)
        # A win 59 days ago is only sad.
        self.check([self.ticket("2026-10-03", "7"), self.ticket("2026-11-30", "0")], "sad", 59)

    def test_tip_ticket_gives_a_desperate_claude_hope(self):
        rows = [self.ticket("2026-09-30", "0"), self.ticket("2026-11-30", "0"), self.upcoming("tip")]
        self.check(rows, "hopeful", None, tips_waiting=1)

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


class FetchRetries(unittest.TestCase):
    def test_retries_then_gives_up(self):
        import urllib.error
        calls = []

        def failing_urlopen(*args, **kwargs):
            calls.append(1)
            raise urllib.error.URLError("bad certificate")

        self.addCleanup(setattr, lotto.urllib.request, "urlopen", lotto.urllib.request.urlopen)
        self.addCleanup(setattr, lotto, "sleep", lotto.sleep)
        lotto.urllib.request.urlopen = failing_urlopen
        lotto.sleep = lambda seconds: None
        with self.assertRaises(urllib.error.URLError):
            lotto.fetch_results("2026-10-01")
        self.assertEqual(len(calls), 4)


class Tips(unittest.TestCase):
    NOW = et(2026, 10, 12, 18)

    def setUp(self):
        # A cap of 100 keeps the numbers here small; the logic is the same at 500.
        self.addCleanup(setattr, lotto, "TIP_CAP", lotto.TIP_CAP)
        lotto.TIP_CAP = 100

    def fill(self, rows, slots, now=NOW, start=0):
        """Adds a pick for every slot, in batches like the routine."""
        picks = self.picks(len(slots), start)
        for i in range(0, len(slots), lotto.TIP_BATCH):
            lotto.add_tips(rows, picks[i : i + lotto.TIP_BATCH], slots[i : i + lotto.TIP_BATCH], now)

    def donations(self, *tickets):
        return [{"seq": i + 1, "received_at": "2026-10-12T12:00:00Z", "tickets": n} for i, n in enumerate(tickets)]

    def picks(self, count, start=0):
        # Distinct valid picks: vary the Powerball, then the last white ball.
        return [[1, 2, 3, 4, 30 + (start + i) // 26, 1 + (start + i) % 26] for i in range(count)]

    def test_slots_fill_oldest_first(self):
        rows = []
        draw, slots, waiting = lotto.tips_due(rows, self.donations(2, 1), self.NOW)
        self.assertEqual((draw, slots, waiting), ("2026-10-12", ["1.1", "1.2", "2.1"], 0))
        lotto.add_tips(rows, self.picks(3), slots, self.NOW)
        self.assertEqual([r["donation"] for r in rows], ["1.1", "1.2", "2.1"])
        self.assertTrue(all(r["source"] == "tip" for r in rows))
        self.assertEqual(lotto.tips_due(rows, self.donations(2, 1), self.NOW)[1], [])

    def test_cap_rolls_the_rest_to_the_next_drawing(self):
        rows = []
        donations = self.donations(60, 90)  # 150 tickets; the second donation splits across drawings
        _, slots, waiting = lotto.tips_due(rows, donations, self.NOW)
        self.assertEqual((len(slots), waiting), (100, 50))
        self.assertEqual((slots[0], slots[-1]), ("1.1", "2.40"))
        self.fill(rows, slots)

        # Same drawing: full.
        self.assertEqual(lotto.tips_due(rows, donations, self.NOW)[1:], ([], 50))
        # Next drawing: the other 50, picking up mid-donation.
        wed = et(2026, 10, 13, 18)
        draw, slots, waiting = lotto.tips_due(rows, donations[lotto.donation_after(rows) :], wed)
        self.assertEqual((draw, len(slots), slots[0], waiting), ("2026-10-14", 50, "2.41", 0))

    def test_donation_after_starts_at_the_newest_partial_donation(self):
        self.assertEqual(lotto.donation_after([]), 0)
        rows = []
        lotto.add_tips(rows, self.picks(2), ["4.1", "5.1"], self.NOW)
        self.assertEqual(lotto.donation_after(rows), 4)

    def test_claude_ticket_does_not_use_the_cap(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW)
        self.assertEqual(len(lotto.tips_due(rows, self.donations(150), self.NOW)[1]), 100)

    def test_fewer_picks_leave_the_rest_due(self):
        rows = []
        _, slots, _ = lotto.tips_due(rows, self.donations(5), self.NOW)
        lotto.add_tips(rows, self.picks(2), slots, self.NOW)
        self.assertEqual(lotto.tips_due(rows, self.donations(5), self.NOW)[1], ["1.3", "1.4", "1.5"])

    def test_rejects_too_many_picks(self):
        rows = []
        with self.assertRaises(ValueError):
            lotto.add_tips(rows, self.picks(3), ["1.1", "1.2"], self.NOW)
        self.assertEqual(rows, [])

    def test_rejects_a_batch_over_the_limit(self):
        rows = []
        slots = [f"1.{n}" for n in range(1, 52)]
        with self.assertRaises(ValueError):
            lotto.add_tips(rows, self.picks(51), slots, self.NOW)
        self.assertEqual(rows, [])

    def test_real_cap_is_500(self):
        self.addCleanup(setattr, lotto, "TIP_CAP", 100)
        lotto.TIP_CAP = 500
        self.assertEqual(lotto.tips_due([], self.donations(600), self.NOW)[1:][1], 100)

    def test_rejects_repeated_picks_in_a_drawing(self):
        rows = []
        lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", self.NOW)
        for picks in ([[5, 4, 3, 2, 1, 6]], [[7, 8, 9, 10, 11, 12], [11, 10, 9, 8, 7, 12]]):
            with self.subTest(picks=picks), self.assertRaises(ValueError):
                lotto.add_tips(rows, picks, ["1.1", "1.2"], self.NOW)
        self.assertEqual(len(rows), 1)

    def test_rejects_bad_numbers_before_adding_any(self):
        rows = []
        with self.assertRaises(ValueError):
            lotto.add_tips(rows, [[1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 99]], ["1.1", "1.2"], self.NOW)
        self.assertEqual(rows, [])

    def test_read_picks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "picks.txt"
            path.write_text("# tonight\n07 19 23 41 58 11\n\n03 15 27 33 66 | 09  # a comment\n")
            self.assertEqual(lotto.read_picks(path), [[7, 19, 23, 41, 58, 11], [3, 15, 27, 33, 66, 9]])

    def test_stats_keep_donated_tickets_compact(self):
        rows = []
        lotto.add_ticket(rows, [2, 11, 27, 44, 60, 8], "", "claude", et(2026, 10, 10, 18))
        self.fill(rows, [f"1.{n}" for n in range(1, 101)], et(2026, 10, 10, 18))
        rows[1]["pick"] = "01 04 19 33 51 | 15"  # make one donated ticket a jackpot
        lotto.score_rows(rows, {"2026-10-10": drawn("01 04 19 33 51 | 15")})
        lotto.add_ticket(rows, [3, 12, 28, 45, 61, 9], "", "claude", self.NOW)
        self.fill(rows, [f"2.{n}" for n in range(1, 101)])
        stats = lotto.build_stats(rows, self.NOW)

        # Scored: Claude's ticket and the latest drawing's winners, with the rest added up.
        winners = [r for r in rows if r["source"] == "tip" and r["result"] and r["prize"] != "0"]
        self.assertGreater(len(winners), 1)
        self.assertCountEqual(stats["recent"], winners + [rows[0]])
        summary = stats["drawings"][0]
        self.assertEqual((summary["draw_date"], summary["tip_tickets"], summary["tip_jackpots"]), ("2026-10-10", 100, 1))
        self.assertEqual(summary["tip_wins"], len(winners))
        # The whole drawing on the day: Claude's ticket plus the 100 donated, at $2 each.
        won = sum(int(r["prize"]) for r in rows if r["result"] and r["prize"] not in ("0", "JACKPOT"))
        self.assertEqual((summary["tickets"], summary["spent"], summary["won"]), (101, 202, won))
        self.assertEqual(summary["net"], won - 202)
        self.assertEqual(stats["best_win"], {"draw_date": "2026-10-10", "prize": "JACKPOT", "source": "tip"})

        # Waiting: Claude's ticket in full, donated ones as just their numbers.
        self.assertEqual([r["source"] for r in stats["upcoming"]], ["claude"])
        [group] = stats["upcoming_tips"]
        self.assertEqual((group["draw_date"], len(group["picks"])), ("2026-10-12", 100))
        self.assertEqual(stats["totals"]["tickets"], 101)

    def test_only_the_latest_drawing_lists_its_winners(self):
        rows = []
        for day, seq in ((10, 1), (12, 2)):
            self.fill(rows, [f"{seq}.{n}" for n in range(1, 27)], et(2026, 10, day, 18))
        lotto.score_rows(rows, {"2026-10-10": drawn("01 04 19 33 51 | 15"), "2026-10-12": drawn("01 04 19 33 51 | 15")})
        stats = lotto.build_stats(rows, et(2026, 10, 13, 12))
        self.assertTrue(stats["recent"])
        self.assertEqual({r["draw_date"] for r in stats["recent"]}, {"2026-10-12"})
        self.assertEqual(len(stats["drawings"]), 2)


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

    def test_latest_drawing_is_kept_until_scoring_brings_a_newer_one(self):
        self.addCleanup(setattr, lotto, "LEDGER", lotto.LEDGER)
        self.addCleanup(setattr, lotto, "STATS", lotto.STATS)
        with tempfile.TemporaryDirectory() as tmp:
            lotto.LEDGER = Path(tmp) / "ledger.csv"
            lotto.STATS = Path(tmp) / "stats.json"
            now = et(2026, 10, 12, 18)
            oct10 = {"draw_date": "2026-10-10", **drawn("01 04 19 33 51 | 15")}
            lotto.save([], now, oct10)
            # A pick doesn't fetch results, so it keeps the drawing already saved.
            rows = []
            lotto.add_ticket(rows, [1, 2, 3, 4, 5, 6], "", "claude", now)
            lotto.save(rows, now)
            self.assertEqual(json.loads(lotto.STATS.read_text())["latest_drawing"], oct10)

    def test_reads_a_ledger_from_before_the_donation_column(self):
        self.addCleanup(setattr, lotto, "LEDGER", lotto.LEDGER)
        with tempfile.TemporaryDirectory() as tmp:
            lotto.LEDGER = Path(tmp) / "ledger.csv"
            lotto.LEDGER.write_text(
                "draw_date,ticket,source,picked_at,pick,note,result,match,prize\n"
                "2026-10-12,1,claude,2026-10-12T18:00:00-04:00,01 02 03 04 05 | 06,,,,\n"
            )
            [row] = lotto.read_ledger()
            self.assertEqual((row["pick"], row["donation"]), ("01 02 03 04 05 | 06", ""))


if __name__ == "__main__":
    unittest.main()
