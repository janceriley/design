import copy
import importlib.util
import inspect
import unittest

from onedesk import nicegui_theme
from onedesk.tokens import load

HAS_NICEGUI = importlib.util.find_spec("nicegui") is not None


class NiceGuiThemeTests(unittest.TestCase):
    def test_brand_colors(self):
        light, dark = nicegui_theme.brand_colors("light"), nicegui_theme.brand_colors("dark")
        self.assertEqual(light["primary"], load().palette("light").navy)
        self.assertEqual(dark["primary"], load().palette("dark").navy)
        # Quasar's dark surfaces come from the dark palette in both modes.
        self.assertEqual(light["dark_page"], load().palette("dark").canvas)
        self.assertEqual(light["dark"], dark["dark"])

    def test_stylesheet(self):
        sheet = nicegui_theme.stylesheet()
        self.assertIn("body.body--dark {", sheet)
        self.assertIn(f"--q-primary: {load().palette('dark').navy} !important;", sheet)
        self.assertIn("--q-dark-page:", sheet)
        self.assertIn(".q-btn, .q-tab { text-transform: none;", sheet)
        # Primary-button labels in dark mode get on_navy text on the label element itself.
        self.assertIn("body.body--dark .q-btn.bg-primary .q-btn__content", sheet)
        self.assertIn("box-shadow: none", sheet)
        self.assertIn("--ag-background-color: var(--od-surface);", sheet)
        self.assertEqual(sheet.count("{"), sheet.count("}"))

    def test_dark_setting(self):
        self.assertIs(nicegui_theme.dark_setting("light"), False)
        self.assertIs(nicegui_theme.dark_setting("dark"), True)
        self.assertIsNone(nicegui_theme.dark_setting("auto"))

    def test_figure_adds_template_and_config(self):
        fig = {"data": [], "layout": {}, "config": {"displayModeBar": False}}
        before = copy.deepcopy(fig)
        out = nicegui_theme.figure(fig, "dark", scrollZoom=True)
        self.assertEqual(fig, before)
        self.assertIn("template", out["layout"])
        self.assertFalse(out["config"]["displayModeBar"])
        self.assertTrue(out["config"]["scrollZoom"])
        self.assertFalse(out["config"]["displaylogo"])


@unittest.skipUnless(HAS_NICEGUI, "nicegui not installed")
class NiceGuiApiTests(unittest.TestCase):
    def test_brand_colors_match_app_colors_signature(self):
        from nicegui.app.app import App

        params = set(inspect.signature(App.colors).parameters) - {"self", "custom_colors"}
        self.assertEqual(set(nicegui_theme.brand_colors()), params)

    def test_html_element_accepts_a_tag(self):
        from nicegui.elements.html import Html

        self.assertIn("tag", inspect.signature(Html.__init__).parameters)


if __name__ == "__main__":
    unittest.main()
