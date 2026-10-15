import importlib.util
import tempfile
import unittest
from pathlib import Path

from onedesk import streamlit_theme
from onedesk.tokens import load

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None

def _streamlit_version():
    if importlib.util.find_spec("streamlit") is None:
        return None
    from importlib.metadata import version

    parts = version("streamlit").split(".")
    return tuple(int(p) for p in parts[:2] if p.isdigit())


# The adapter targets Streamlit 1.60 (Order Parser's version); older releases lack some theme options.
STREAMLIT_VERSION = _streamlit_version()
HAS_TARGET_STREAMLIT = STREAMLIT_VERSION is not None and STREAMLIT_VERSION >= (1, 60)


@unittest.skipIf(tomllib is None, "tomllib needs Python 3.11+")
class ConfigTests(unittest.TestCase):
    def test_two_mode_config_parses(self):
        data = tomllib.loads(streamlit_theme.config_toml())
        theme = data["theme"]
        self.assertNotIn("base", theme)
        self.assertEqual(theme["light"]["primaryColor"], load().palette("light").navy)
        self.assertEqual(theme["dark"]["primaryColor"], load().palette("dark").navy)
        self.assertEqual(theme["dark"]["sidebar"]["backgroundColor"], load().palette("dark").raised)
        self.assertEqual(len(theme["chartSequentialColors"]), 10)
        self.assertEqual(len(theme["chartDivergingColors"]), 10)
        self.assertEqual(theme["chartCategoricalColors"], list(load().categorical("light")))
        self.assertEqual(theme["baseRadius"], "3px")
        self.assertTrue(theme["font"].startswith("Segoe UI Variable Text, "))
        self.assertTrue(theme["codeFont"].startswith("Cascadia Mono, "))

    def test_single_mode_config(self):
        data = tomllib.loads(streamlit_theme.config_toml(("light",)))
        self.assertEqual(data["theme"]["base"], "light")
        self.assertEqual(data["theme"]["backgroundColor"], load().palette("light").canvas)
        self.assertNotIn("light", data["theme"])

    def test_write_config_with_extra_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = streamlit_theme.write_config(Path(tmp) / ".streamlit" / "config.toml",
                                                extra={"server": {"headless": True}})
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["server"]["headless"])
            self.assertIn("light", data["theme"])

    def test_stylesheet_has_no_page_rules(self):
        sheet = streamlit_theme.stylesheet("dark")
        self.assertIn(":root {", sheet)
        self.assertIn("--od-canvas: #0c1218;", sheet)
        self.assertNotIn("body {", sheet)

    def test_primary_buttons_get_readable_text(self):
        self.assertIn('button[kind^="primary"]', streamlit_theme.stylesheet("dark"))
        self.assertIn("var(--od-on-navy)", streamlit_theme.streamlit_rules())

    def test_current_mode_outside_streamlit(self):
        self.assertEqual(streamlit_theme.current_mode("dark"), "dark")


@unittest.skipUnless(HAS_TARGET_STREAMLIT, f"needs Streamlit 1.60+ (found {STREAMLIT_VERSION})")
class StreamlitOptionTests(unittest.TestCase):
    def test_every_key_is_a_real_streamlit_option(self):
        from streamlit import config as st_config

        known = set(st_config._config_options_template)
        for modes in (("light", "dark"), ("light",), ("dark",)):
            emitted = {f"{table}.{key}" for table, options in streamlit_theme.config(modes).items() for key in options}
            with self.subTest(modes=modes):
                self.assertEqual(sorted(emitted - known), [])


if __name__ == "__main__":
    unittest.main()
