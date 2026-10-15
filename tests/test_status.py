import unittest

from onedesk import status
from onedesk.status import Kind, Status
from onedesk.tokens import MODES, load


class StatusTests(unittest.TestCase):
    def test_text_form(self):
        self.assertEqual(status.live("mini PC").text(), "● LIVE · mini PC")
        self.assertEqual(status.needs("Auth", "2d").text(), "⚠ AUTH · 2d")
        self.assertEqual(status.reconnecting().text(), "↻ RECONNECTING")
        self.assertEqual(status.error("Rec error").text(), "! REC ERROR")
        self.assertEqual(status.sharing(1).text(), "⇄ 1 VIEWER")
        self.assertEqual(status.sharing(0).kind, Kind.OFF)
        self.assertEqual(status.demo().text(), "DEMO DATA")

    def test_glyph_override_and_suppression(self):
        self.assertEqual(Status("Ready", Kind.OK).shown_glyph, "●")
        self.assertEqual(Status("Ready", Kind.OK, glyph="").shown_glyph, None)
        self.assertEqual(Status("Ready", "ok", glyph="*").shown_glyph, "*")
        self.assertIs(Status("Ready", "ok").kind, Kind.OK)
        with self.assertRaises(ValueError):
            Status("  ")
        with self.assertRaises(ValueError):
            Status("Ready", "great")

    def test_quiet_when_healthy(self):
        for mode in MODES:
            p = load().palette(mode)
            ok = status.tag_colors(Kind.OK, p)
            self.assertEqual((ok.background, ok.border, ok.text), (p.surface, p.rule_strong, p.ink))
            warn = status.tag_colors(Kind.WARN, p)
            self.assertEqual(warn.background, p.warn_tint)
            self.assertEqual(warn.border, p.mix("warn", "surface", 0.45))
            bad = status.tag_colors(Kind.BAD, p)
            self.assertEqual(bad.background, p.bad_tint)
            self.assertEqual(status.tag_colors(Kind.STALE, p).pattern, "hatch")
            self.assertEqual(status.tag_colors(Kind.DEMO, p).pattern, "stripes")
            self.assertEqual(status.tag_colors(Kind.HIT, p).text, p.up)

    def test_every_kind_has_colors(self):
        p = load().palette("light")
        for kind in Kind:
            with self.subTest(kind=kind):
                c = status.tag_colors(kind, p)
                self.assertTrue(all(value.startswith("#") for value in (c.text, c.glyph, c.background, c.border)))

    def test_worst(self):
        items = [status.live(), status.needs("Auth", "2d"), status.failed("Blocked", "1"), status.recording()]
        self.assertEqual(status.worst(items).word, "Blocked")
        self.assertIsNone(status.worst([]))
        self.assertTrue(status.failed("Blocked").needs_attention)
        self.assertFalse(status.live().needs_attention)


if __name__ == "__main__":
    unittest.main()
