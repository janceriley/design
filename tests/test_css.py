import unittest

from onedesk import css, status
from onedesk.status import Kind
from onedesk.tokens import load


class CssTests(unittest.TestCase):
    def test_every_token_becomes_a_variable(self):
        light, dark = css.variables("light"), css.variables("dark")
        for name in load().color_names:
            var = "--od-" + name.replace("_", "-")
            with self.subTest(var=var):
                self.assertEqual(light[var], load().palette("light")[name])
                self.assertEqual(dark[var], load().palette("dark")[name])
        self.assertEqual(light.keys(), dark.keys())
        self.assertEqual(light["--od-radius"], "3px")
        self.assertEqual(light["--od-series-1"], load().palette("light").count)
        self.assertIn('"Cascadia Mono"', light["--od-font-num"])

    def test_tag_variables_match_tag_colors(self):
        for mode in ("light", "dark"):
            v = css.variables(mode)
            c = status.tag_colors(Kind.WARN, load().palette(mode))
            self.assertEqual(v["--od-tag-warn-bg"], c.background)
            self.assertEqual(v["--od-tag-warn-border"], c.border)

    def test_stylesheet_carries_both_modes(self):
        sheet = css.stylesheet({"light": ":root", "dark": "body.body--dark"})
        self.assertIn(":root {", sheet)
        self.assertIn("body.body--dark {", sheet)
        self.assertIn("color-scheme: dark;", sheet)
        self.assertIn("--od-navy: #8fb3e8;", sheet)
        self.assertIn("--od-navy: #0d3b70;", sheet)
        for kind in Kind:
            self.assertIn(f".od-tag--{kind.value} ", sheet)
        self.assertEqual(sheet.count("{"), sheet.count("}"))

    def test_frame_classes(self):
        sheet = css.stylesheet()
        for cls in (".od-app-bar", ".od-strip", ".od-status-bar", ".od-mark", ".od-app-name", ".od-context",
                    ".od-note-warn", ".od-faint"):
            with self.subTest(cls=cls):
                self.assertIn(cls + " {", sheet)
        self.assertIn("min-height: var(--od-h-app-bar)", sheet)

    def test_important_and_partial_sheets(self):
        sheet = css.stylesheet({"dark": "body"}, important_selectors=("body",), base=False, components=False)
        self.assertIn("--od-navy: #8fb3e8 !important;", sheet)
        self.assertNotIn(".od-tag", sheet)

    def test_status_tag_html_is_escaped(self):
        html = css.status_tag_html(status.Status("<b>Live</b>", Kind.OK, detail="a & b"))
        self.assertIn("&lt;b&gt;Live&lt;/b&gt;", html)
        self.assertIn("a &amp; b", html)
        self.assertTrue(html.startswith('<span class="od-tag od-tag--ok">'))
        self.assertIn('aria-hidden="true"', html)
        no_glyph = css.status_tag_html(status.demo())
        self.assertNotIn("od-tag__glyph", no_glyph)


if __name__ == "__main__":
    unittest.main()
