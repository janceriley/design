import importlib.util
import os
import re
import tempfile
import unittest
from pathlib import Path

HAS_PYSIDE6 = importlib.util.find_spec("PySide6") is not None

if HAS_PYSIDE6:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QPalette
    from PySide6.QtWidgets import QApplication, QTableWidget

    from onedesk import qt_theme, status
    from onedesk.tokens import load


@unittest.skipUnless(HAS_PYSIDE6, "needs PySide6 (run with Equity_Recorder's venv)")
class QtThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.theme = qt_theme.apply(self.app, "light")

    def test_palette_roles_are_tokens(self):
        R = QPalette.ColorRole
        for mode in ("light", "dark"):
            with self.subTest(mode=mode):
                p = load().palette(mode)
                palette = qt_theme.qpalette(p)
                for role, token in ((R.Window, p.canvas), (R.Base, p.surface), (R.AlternateBase, p.raised),
                                    (R.Text, p.ink), (R.Highlight, p.navy_tint), (R.HighlightedText, p.ink),
                                    (R.ToolTipBase, p.ink), (R.PlaceholderText, p.faint), (R.Link, p.navy)):
                    self.assertEqual(palette.color(role).name(), token)
                self.assertEqual(palette.color(QPalette.ColorGroup.Disabled, R.Text).name(), p.faint)

    def test_stylesheet_uses_only_token_colors_and_flat_corners(self):
        for mode in ("light", "dark"):
            with self.subTest(mode=mode):
                p = load().palette(mode)
                sheet = qt_theme.stylesheet(p)
                colors = set(re.findall(r"#[0-9a-fA-F]{6}", sheet))
                self.assertLessEqual(colors, set(p.as_dict().values()))
                self.assertIn("border-radius: 3px", sheet)
                self.assertNotIn("shadow", sheet)
                self.assertIn('QPushButton[onedesk="primary"]', sheet)
                self.assertEqual(sheet.count("{"), sheet.count("}"))

    def test_arrow_images_style_spin_and_combo_boxes(self):
        p = load().palette("light")
        with tempfile.TemporaryDirectory() as folder:
            arrows = qt_theme.arrow_images(p, Path(folder))
            self.assertEqual(set(arrows), {"up", "down", "up_off", "down_off"})
            for path in arrows.values():
                self.assertTrue(Path(path).is_file())
                self.assertTrue(Path(path.replace(".png", "@2x.png")).is_file())
            sheet = qt_theme.stylesheet(p, arrows=arrows)
            self.assertIn(f'image: url("{arrows["down"]}")', sheet)
            self.assertIn("QSpinBox::up-arrow", sheet)
        # Without arrow images, spin boxes keep the style's own frame and arrows.
        self.assertNotIn("QSpinBox", qt_theme.stylesheet(p))

    def test_fonts_follow_the_type_roles(self):
        tokens = load()
        label = self.theme.font("label")
        self.assertEqual(label.capitalization(), QFont.Capitalization.AllUppercase)
        self.assertEqual(label.weight(), QFont.Weight.DemiBold)
        self.assertEqual(label.stretch(), 87)
        self.assertAlmostEqual(label.letterSpacing(), 108.0)
        self.assertEqual(label.pointSizeF(), tokens.type_size("caption").pt)
        self.assertEqual(self.theme.font("num").pointSizeF(), tokens.type_size("body").pt)
        self.assertEqual(self.theme.font("title").weight(), QFont.Weight.DemiBold)
        self.assertEqual(self.app.font().pointSizeF(), tokens.type_size("body").pt)

    def test_resolve_family_takes_the_first_installed_face(self):
        spec = load().font("num")
        self.assertEqual(qt_theme.resolve_family(spec, {"consolas": "Consolas"}), "Consolas")
        both = {"cascadia mono": "Cascadia Mono", "consolas": "Consolas"}
        self.assertEqual(qt_theme.resolve_family(spec, both), "Cascadia Mono")
        self.assertEqual(qt_theme.resolve_family(spec, {}), QApplication.font().family())

    def test_tags_show_glyph_caps_word_and_plain_detail(self):
        item = status.needs("Auth", "2d")
        label = self.theme.tag(item)
        self.assertIn(status.ATTENTION, label.text())
        self.assertIn("AUTH", label.text())
        self.assertIn("2d", label.text())  # details keep their case
        self.assertIn(load().palette("light").warn_tint, label.styleSheet())
        self.assertEqual(label.font().capitalization(), QFont.Capitalization.MixedCase)
        self.assertEqual(label.accessibleName(), item.text())

    def test_set_mode_restyles_palette_and_tags_then_calls_listeners(self):
        seen = []
        label = self.theme.tag(status.live("paper"))
        self.theme.on_mode_change(lambda t: seen.append(t.mode))
        self.assertTrue(self.theme.set_mode("dark"))
        dark = load().palette("dark")
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Window).name(), dark.canvas)
        self.assertIn(dark.surface, label.styleSheet())
        self.assertEqual(seen, ["dark"])
        self.assertFalse(self.theme.set_mode("dark"))
        self.assertEqual(self.theme.toggle(), "light")

    def test_style_table_sets_number_face_and_caps_heads(self):
        table = QTableWidget(1, 2)
        table.setHorizontalHeaderLabels(["Bid", "Ask"])
        self.theme.style_table(table)
        self.assertEqual(table.font().family(), self.theme.font("num").family())
        self.assertEqual(table.horizontalHeaderItem(0).font().capitalization(), QFont.Capitalization.AllUppercase)
        self.assertEqual(self.theme.header_font().capitalization(), QFont.Capitalization.AllUppercase)

    def test_hatch_brush_tiles_diagonal_lines(self):
        brush = self.theme.hatch_brush(6)
        self.assertEqual(brush.style(), Qt.BrushStyle.TexturePattern)
        self.assertEqual(brush.texture().width(), 6)

    def test_current_is_the_last_applied_theme(self):
        self.assertIs(qt_theme.current(), self.theme)
        self.assertEqual(self.theme.color("up").name(), load().palette("light").up)
        self.assertEqual(self.theme.mix("ink", "surface", 1.0).name(), load().palette("light").ink)


if __name__ == "__main__":
    unittest.main()
