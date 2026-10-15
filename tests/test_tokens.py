import json
import unittest

from onedesk import color
from onedesk.tokens import MODES, TokenError, Tokens, load, resolve_mode


class TokenFileTests(unittest.TestCase):
    def setUp(self):
        self.t = load()

    def test_every_color_has_both_modes_and_a_use(self):
        for name in self.t.color_names:
            with self.subTest(name=name):
                spec = self.t.describe(name)
                self.assertTrue(color.is_hex(spec["light"]))
                self.assertTrue(color.is_hex(spec["dark"]))
                self.assertTrue(spec["use"].strip())

    def test_both_palettes_have_the_same_tokens(self):
        light, dark = self.t.palette("light"), self.t.palette("dark")
        self.assertEqual(list(light), list(dark))
        self.assertEqual(tuple(light), self.t.color_names)

    def test_access_by_key_and_attribute(self):
        p = self.t.palette("light")
        self.assertEqual(p.navy, "#0d3b70")
        self.assertEqual(p["navy"], p.navy)
        self.assertEqual(self.t.palette("dark").navy, "#8fb3e8")
        with self.assertRaises(AttributeError):
            p.not_a_token
        with self.assertRaises(KeyError):
            p["not_a_token"]

    def test_every_token_is_in_a_group(self):
        grouped = [n for g in ("chrome", "accent", "data", "status") for n in self.t.group(g)]
        self.assertCountEqual(grouped, self.t.color_names)

    def test_decided_values_from_the_design_page(self):
        light = self.t.palette("light")
        self.assertEqual((light.canvas, light.surface, light.ink, light.up, light.down),
                         ("#f2f4f7", "#ffffff", "#17212f", "#157a3a", "#b42318"))

    def test_bad_files_are_rejected(self):
        good = json.loads(self.t.as_json())
        broken = json.loads(json.dumps(good))
        broken["color"]["navy"]["dark"] = "blue"
        with self.assertRaises(TokenError):
            Tokens(broken)
        broken = json.loads(json.dumps(good))
        broken["color"]["navy"]["use"] = " "
        with self.assertRaises(TokenError):
            Tokens(broken)
        broken = json.loads(json.dumps(good))
        broken["series"]["sequential"]["light"] = broken["series"]["sequential"]["light"][:9]
        with self.assertRaises(TokenError):
            Tokens(broken)
        broken = json.loads(json.dumps(good))
        broken["font"]["num"]["tk"][0]["weight"] = "heavy"
        with self.assertRaises(TokenError):
            Tokens(broken)

    def test_resolve_mode(self):
        self.assertEqual(resolve_mode("light"), "light")
        self.assertEqual(resolve_mode("dark"), "dark")
        self.assertIn(resolve_mode("auto"), MODES)
        self.assertIn(resolve_mode(None), MODES)
        with self.assertRaises(TokenError):
            resolve_mode("dim")

    def test_categorical_series(self):
        for mode in MODES:
            slots = self.t.categorical(mode)
            self.assertEqual(len(slots), 5)
            # The single-series color (count) is chart slot 1 in both modes.
            self.assertEqual(slots[0], self.t.palette(mode).count)
        self.assertEqual(self.t.categorical_limits, {"adjacent": 5, "all_pairs": 3})

    def test_categorical_slots_avoid_the_reserved_hues(self):
        # Green and red mean money direction and violet means model output; series must not impersonate them.
        for mode in MODES:
            p = self.t.palette(mode)
            for slot in self.t.categorical(mode)[1:]:
                for reserved in (p.up, p.down, p.model):
                    with self.subTest(mode=mode, slot=slot, reserved=reserved):
                        self.assertGreater(color.delta_e(slot, reserved), 7.0)

    def test_sequential_runs_light_to_dark_then_flips(self):
        light = self.t.sequential("light")
        self.assertEqual(len(light), 10)
        lum = [color.luminance(c) for c in light]
        self.assertEqual(lum, sorted(lum, reverse=True))
        self.assertEqual(self.t.sequential("dark"), tuple(reversed(light)))

    def test_diverging_runs_loss_to_gain(self):
        for mode in MODES:
            p = self.t.palette(mode)
            scale = self.t.diverging(mode, steps=10)
            self.assertEqual((len(scale), scale[0], scale[-1]), (10, p.down, p.up))
            odd = self.t.diverging(mode, steps=11)
            self.assertEqual(odd[5], self.t.diverging_mid(mode))
        with self.assertRaises(ValueError):
            self.t.diverging("light", steps=2)

    def test_fonts(self):
        self.assertEqual(set(self.t.font_roles), {"ui", "ui_strong", "display", "label", "num", "num_strong"})
        ui = self.t.font("ui").css_stack()
        self.assertTrue(ui.startswith('"Segoe UI Variable Text"'))
        self.assertIn("system-ui", ui)
        self.assertTrue(self.t.font("label").css_stack().startswith("Bahnschrift,"))
        self.assertTrue(self.t.font("num").css_stack().startswith('"Cascadia Mono"'))
        self.assertEqual(self.t.font("label").stretch, "87.5%")

    def test_type_scale_increases(self):
        roles = ("caption", "body", "control", "title", "heading", "readout")
        px = [self.t.type_size(r).px for r in roles]
        pt = [self.t.type_size(r).pt for r in roles]
        self.assertEqual(px, sorted(px))
        self.assertEqual(pt, sorted(pt))

    def test_sizes_and_glyphs(self):
        self.assertEqual(self.t.space, (4, 8, 12, 16, 24))
        self.assertEqual((self.t.radius("tk"), self.t.radius("web")), (0, 3))
        self.assertEqual(self.t.height("app_bar"), 40)
        self.assertEqual(self.t.glyph("attention"), "⚠")
        with self.assertRaises(TokenError):
            self.t.glyph("sparkle")


class ContrastTests(unittest.TestCase):
    """Text and marks stay readable in both modes (WCAG 2.x ratios)."""

    TEXT = [  # (foreground, background, minimum) for text: 4.5:1, body ink 7:1
        ("ink", "canvas", 7.0), ("ink", "surface", 7.0), ("ink", "raised", 7.0), ("ink", "sunken", 7.0),
        ("ink_2", "surface", 4.5), ("ink_2", "canvas", 4.5), ("ink_2", "itm", 4.5),
        ("muted", "surface", 4.5), ("muted", "raised", 4.5), ("muted", "canvas", 4.5),
        ("up", "surface", 4.5), ("down", "surface", 4.5), ("model", "surface", 4.5),
        ("quote", "surface", 4.5), ("navy", "surface", 4.5), ("warn", "surface", 4.5),
        ("on_navy", "navy", 4.5), ("on_navy", "navy_hover", 4.5),
        ("ink", "warn_tint", 4.5), ("ink", "bad_tint", 4.5), ("ink", "navy_tint", 4.5),
        ("up", "up_tint", 4.5), ("ink", "up_tint", 4.5), ("ink", "down_tint", 4.5),
    ]
    GRAPHIC = [  # glyphs and marks: 3:1
        ("ok", "surface"), ("warn", "surface"), ("bad", "surface"), ("off", "surface"), ("rec", "surface"),
        ("count", "surface"), ("focus", "surface"), ("navy", "canvas"), ("quote_2", "surface"),
    ]

    def test_text_pairs(self):
        for mode in MODES:
            p = load().palette(mode)
            for fg, bg, minimum in self.TEXT:
                with self.subTest(mode=mode, fg=fg, bg=bg):
                    self.assertGreaterEqual(color.contrast(p[fg], p[bg]), minimum)

    def test_graphic_pairs(self):
        for mode in MODES:
            p = load().palette(mode)
            for fg, bg in self.GRAPHIC:
                with self.subTest(mode=mode, fg=fg, bg=bg):
                    self.assertGreaterEqual(color.contrast(p[fg], p[bg]), 3.0)

    def test_chart_slots_on_the_dark_surface(self):
        surface = load().palette("dark").surface
        for slot in load().categorical("dark"):
            with self.subTest(slot=slot):
                self.assertGreaterEqual(color.contrast(slot, surface), 3.0)


class SeparationTests(unittest.TestCase):
    """Colors with different meanings stay apart (OKLab Delta E x100, normal vision)."""

    PAIRS = [("up", "down", 15.0), ("count", "model", 12.0), ("navy", "quote", 8.0),
             ("model", "navy", 9.0), ("up", "warn", 15.0)]

    def test_meaningful_pairs(self):
        for mode in MODES:
            p = load().palette(mode)
            for a, b, minimum in self.PAIRS:
                with self.subTest(mode=mode, a=a, b=b):
                    self.assertGreaterEqual(color.delta_e(p[a], p[b]), minimum)


if __name__ == "__main__":
    unittest.main()
