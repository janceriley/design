import datetime as dt
import math
import unittest
from decimal import Decimal

from onedesk import fmt

M = fmt.MINUS


class NumberTests(unittest.TestCase):
    def test_missing_values_are_a_dash_never_zero(self):
        for value in (None, float("nan"), math.nan):
            with self.subTest(value=value):
                for fn in (fmt.money, fmt.pnl, fmt.fee, fmt.price, fmt.strike, fmt.width, fmt.count, fmt.percent):
                    self.assertEqual(fn(value), "—")

    def test_money(self):
        self.assertEqual(fmt.money(1234.5), "$1,234.50")
        self.assertEqual(fmt.money(-1234.5), f"{M}$1,234.50")
        self.assertEqual(fmt.money(1234.5, signed=True), "+$1,234.50")
        self.assertEqual(fmt.money(0), "$0.00")
        self.assertEqual(fmt.money(-0.004), "$0.00")  # never "-$0.00"
        self.assertEqual(fmt.money(Decimal("12.345"), decimals=1), "$12.3")
        self.assertEqual(fmt.money(2, decimals=0), "$2")

    def test_pnl_is_always_signed(self):
        self.assertEqual(fmt.pnl(412.5), "+$412.50")
        self.assertEqual(fmt.pnl(-20.6), f"{M}$20.60")
        self.assertEqual(fmt.pnl(0), "$0.00")

    def test_fees_are_always_negative(self):
        self.assertEqual(fmt.fee(86.4), f"{M}$86.40")
        self.assertEqual(fmt.fee(-86.4), f"{M}$86.40")
        self.assertEqual(fmt.fee(0), "$0.00")

    def test_price(self):
        self.assertEqual(fmt.price(0.42), "0.42")
        self.assertEqual(fmt.price(1.6), "1.60")
        self.assertEqual(fmt.price(0.42, compact=True), ".42")
        self.assertEqual(fmt.price(-0.42, compact=True), f"{M}.42")
        self.assertEqual(fmt.price(1.6, compact=True), "1.60")
        self.assertEqual(fmt.price(0.12, signed=True), "+0.12")
        self.assertEqual(fmt.price(0.12345, decimals=4), "0.1235")

    def test_strikes_pairs_and_widths(self):
        self.assertEqual(fmt.strike(590), "590")
        self.assertEqual(fmt.strike(592.5), "592.5")
        self.assertEqual(fmt.strike(77.25), "77.25")
        self.assertEqual(fmt.strike(80.0), "80")
        self.assertEqual(fmt.pair(76, 79), "76/79")
        self.assertEqual(fmt.width(1), "W1.00")
        self.assertEqual(fmt.width(2.5), "W2.50")

    def test_counts_and_plurals(self):
        self.assertEqual(fmt.count(12345), "12,345")
        self.assertEqual(fmt.count(2412800.0), "2,412,800")
        self.assertEqual(fmt.count(-3), f"{M}3")
        self.assertEqual(fmt.plural(1, "file"), "1 file")
        self.assertEqual(fmt.plural(21, "file"), "21 files")
        self.assertEqual(fmt.plural(2, "day", "days"), "2 days")
        self.assertEqual(fmt.plural(3, "methodology", "methodologies"), "3 methodologies")

    def test_percent(self):
        self.assertEqual(fmt.percent(17.3), "17.3%")
        self.assertEqual(fmt.percent(0.173, ratio=True), "17.3%")
        self.assertEqual(fmt.percent(1.2, signed=True), "+1.2%")
        self.assertEqual(fmt.percent(-1.2), f"{M}1.2%")
        self.assertEqual(fmt.percent(59.5, decimals=0), "60%")

    def test_rejects_non_numbers(self):
        for value in ("12", True, [1]):
            with self.subTest(value=value), self.assertRaises(TypeError):
                fmt.money(value)


class DateTimeTests(unittest.TestCase):
    def test_dates(self):
        d = dt.date(2026, 10, 13)
        self.assertEqual(fmt.session_date(d), "Tue Oct 13 '26")
        self.assertEqual(fmt.session_date(dt.datetime(2026, 7, 8, 9, 30)), "Wed Jul 8 '26")
        self.assertEqual(fmt.expiry(dt.date(2026, 10, 17)), "Oct 17 '26")
        self.assertEqual(fmt.iso_date(d), "2026-10-13")
        self.assertEqual(fmt.session_date(None), "—")
        with self.assertRaises(TypeError):
            fmt.expiry("2026-10-17")

    def test_times_are_never_converted(self):
        t = dt.datetime(2026, 10, 14, 12, 42, 10, 250000)
        self.assertEqual(fmt.time_of_day(t), "12:42:10")
        self.assertEqual(fmt.time_of_day(t, zone="ET"), "12:42:10 ET")    # the Matrix
        self.assertEqual(fmt.time_of_day(t, centiseconds=True), "12:42:10.25")  # Playback, unlabeled
        self.assertEqual(fmt.time_of_day(dt.time(9, 30), seconds=False), "09:30")
        aware = dt.datetime(2026, 10, 14, 11, 42, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
        self.assertEqual(fmt.time_of_day(aware, seconds=False), "11:42")

    def test_clock(self):
        self.assertEqual(fmt.clock(dt.time(16, 0), zone="ET"), "4:00 PM ET")
        self.assertEqual(fmt.clock(dt.time(9, 30)), "9:30 AM")
        self.assertEqual(fmt.clock(dt.time(12, 5)), "12:05 PM")
        self.assertEqual(fmt.clock(dt.time(0, 0)), "12:00 AM")

    def test_durations(self):
        self.assertEqual(fmt.duration(45), "45s")
        self.assertEqual(fmt.duration(187), "3m 07s")
        self.assertEqual(fmt.duration(3900), "1h 05m")
        self.assertEqual(fmt.duration(-1), "—")
        self.assertEqual(fmt.elapsed(1.8412), "1.84 s")


class TextTests(unittest.TestCase):
    def test_join_skips_empty_parts(self):
        self.assertEqual(fmt.join("USO", None, "", "Oct 17 '26"), "USO · Oct 17 '26")

    def test_ellipsize(self):
        # The cut drops trailing spaces so the ellipsis sits against the last word.
        self.assertEqual(fmt.ellipsize("Statements through Tue Oct 13", 12), "Statements…")
        self.assertEqual(fmt.ellipsize("Statements through Tue Oct 13", 15), "Statements thr…")
        self.assertEqual(fmt.ellipsize("short", 12), "short")

    def test_caps(self):
        self.assertEqual(fmt.caps("Exit buy"), "EXIT BUY")


if __name__ == "__main__":
    unittest.main()
