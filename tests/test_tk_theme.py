import tkinter as tk
import tkinter.font as tkfont
import unittest
from tkinter import ttk

from onedesk import status
from onedesk import tk_theme
from onedesk.tokens import load


def _make_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display
        raise unittest.SkipTest(f"Tk unavailable: {exc}")
    root.withdraw()
    return root


def _hex(widget, value):
    r, g, b = widget.winfo_rgb(value)
    return f"#{r >> 8:02x}{g >> 8:02x}{b >> 8:02x}"


class TkThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = _make_root()
        cls.theme = tk_theme.apply(cls.root, mode="light", title_bar=False)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.theme.set_mode("light")

    def lookup(self, style, option):
        return _hex(self.root, self.theme.style.lookup(style, option))

    def test_uses_clam_and_palette(self):
        p = self.theme.palette
        self.assertEqual(self.theme.style.theme_use(), "clam")
        self.assertEqual(self.lookup("TButton", "background"), p.surface)
        self.assertEqual(self.lookup("Primary.TButton", "background"), p.navy)
        self.assertEqual(self.lookup("Primary.TButton", "foreground"), p.on_navy)
        self.assertEqual(self.lookup("Raised.TLabel", "background"), p.raised)
        self.assertEqual(self.lookup("Caps.Raised.TLabel", "background"), p.raised)
        self.assertEqual(self.lookup("Caps.Raised.TLabel", "foreground"), p.muted)
        self.assertEqual(self.theme.style.lookup("Caps.Raised.TLabel", "font"), "OneDeskLabel")
        self.assertEqual(self.lookup("Treeview", "fieldbackground"), p.surface)
        self.assertEqual(self.theme.style.lookup("Treeview", "font"), "OneDeskNum")
        self.assertEqual(self.lookup("Treeview.Heading", "background"), p.raised)
        self.assertEqual(_hex(self.root, self.root.cget("background")), p.canvas)

    def test_named_fonts_use_installed_families(self):
        installed = tk_theme.available_families(self.root)
        names = tkfont.names(self.root)
        for role, (name, _spec, size_role) in tk_theme.FONTS.items():
            with self.subTest(role=role):
                self.assertIn(name, names)
                family, _weight = self.theme.families[role]
                self.assertIn(family.lower(), installed)
                self.assertEqual(self.theme.fonts[role].actual("size"), load().type_size(size_role).pt)
        default_family = tkfont.nametofont("TkDefaultFont", root=self.root).actual("family")
        self.assertEqual(default_family, self.theme.families["ui"][0])

    def test_font_fallback(self):
        spec = load().font("num")
        fake = {"consolas": "Consolas"}
        self.assertEqual(tk_theme.resolve_font(self.root, spec, fake), ("Consolas", "normal"))
        family, _ = tk_theme.resolve_font(self.root, spec, {})
        self.assertTrue(family)

    def test_row_height_follows_the_number_face(self):
        line = self.theme.fonts["num"].metrics("linespace")
        self.assertEqual(self.theme.row_height("table"), line + 10)
        self.assertEqual(self.theme.row_height("matrix"), line + 8)

    def test_option_database_defaults_for_new_classic_widgets(self):
        p = self.theme.palette
        label = tk.Label(self.root, text="x")
        canvas = tk.Canvas(self.root)
        try:
            self.assertEqual(_hex(label, label.cget("background")), p.canvas)
            self.assertEqual(_hex(label, label.cget("foreground")), p.ink)
            self.assertEqual(_hex(canvas, canvas.cget("background")), p.surface)
        finally:
            label.destroy()
            canvas.destroy()

    def test_set_mode_restyles_recolors_and_notifies(self):
        light = self.theme.palette
        dark = load().palette("dark")
        frame = tk.Frame(self.root, background=light.surface)
        label = tk.Label(frame, background=light.raised, foreground=light.ink)
        odd = tk.Label(frame, background="#123456")  # not a token: left alone
        canvas = tk.Canvas(frame, background=light.surface)
        rect = canvas.create_rectangle(0, 0, 10, 10, fill=light.up_tint, outline=light.rule)
        calls = []
        self.theme.on_mode_change(lambda theme: calls.append(theme.mode))
        try:
            self.assertTrue(self.theme.set_mode("dark"))
            self.assertFalse(self.theme.set_mode("dark"))
            self.assertEqual(calls, ["dark"])
            self.assertEqual(self.lookup("Primary.TButton", "background"), dark.navy)
            self.assertEqual(_hex(frame, frame.cget("background")), dark.surface)
            self.assertEqual(_hex(label, label.cget("background")), dark.raised)
            self.assertEqual(_hex(label, label.cget("foreground")), dark.ink)
            self.assertEqual(_hex(odd, odd.cget("background")), "#123456")
            self.assertEqual(_hex(canvas, canvas.itemcget(rect, "fill")), dark.up_tint)
            self.assertEqual(_hex(canvas, canvas.itemcget(rect, "outline")), dark.rule)
            self.assertEqual(self.theme.toggle(), "light")
            self.assertEqual(_hex(label, label.cget("background")), light.raised)
        finally:
            frame.destroy()

    def test_color_map_prefers_the_first_token(self):
        mapping = tk_theme.color_map(load().palette("light"), load().palette("dark"))
        self.assertEqual(mapping["#17212f"], load().palette("dark").ink)  # ink, not stripe_2
        self.assertEqual(mapping["#ffffff"], load().palette("dark").surface)

    def test_hatch_and_stripes_stay_inside_the_box(self):
        canvas = tk.Canvas(self.root, width=200, height=100)
        try:
            ids = tk_theme.draw_hatch(canvas, 10, 20, 110, 60, color="#c3cad3", spacing=6)
            self.assertGreater(len(ids), 10)
            for item in ids:
                x0, y0, x1, y1 = canvas.coords(item)
                for x, y in ((x0, y0), (x1, y1)):
                    self.assertTrue(10 - 1e-6 <= x <= 110 + 1e-6 and 20 - 1e-6 <= y <= 60 + 1e-6)
            stripes = tk_theme.draw_stripes(canvas, 0, 0, 120, 8, colors=("#e8a317", "#17212f"), band=7)
            self.assertGreater(len(stripes), 5)
            for item in stripes:
                coords = canvas.coords(item)
                xs, ys = coords[0::2], coords[1::2]
                self.assertTrue(min(xs) >= -1e-6 and max(xs) <= 120 + 1e-6)
                self.assertTrue(min(ys) >= -1e-6 and max(ys) <= 8 + 1e-6)
        finally:
            canvas.destroy()

    def test_status_tag_follows_the_mode(self):
        tag = self.theme.tag(self.root, status.needs("Auth", "2d"))
        try:
            light = self.theme.palette
            self.assertEqual(_hex(tag, tag.cget("background")), light.warn_tint)
            self.assertEqual(tag._word.cget("text"), "AUTH")
            self.theme.set_mode("dark")
            self.assertEqual(_hex(tag, tag.cget("background")), load().palette("dark").warn_tint)
            tag.set(status.demo())
            self.assertEqual(_hex(tag, tag.cget("background")), load().palette("dark").stripe)
            tag.set(status.live("mini PC"))
            self.assertEqual(tag._glyph.cget("text"), "●")
            self.assertEqual(tag._detail.cget("text"), "mini PC")
        finally:
            tag.destroy()
        self.theme.set_mode("light")  # destroyed tags drop out of the listener list quietly

    def test_title_bar_call_is_safe(self):
        self.assertIsInstance(tk_theme.set_dark_title_bar(self.root, True), bool)


if __name__ == "__main__":
    unittest.main()
