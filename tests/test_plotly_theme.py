import copy
import importlib.util
import json
import unittest

from onedesk import plotly_theme
from onedesk.tokens import MODES, load

HAS_PLOTLY = importlib.util.find_spec("plotly") is not None


class TemplateTests(unittest.TestCase):
    def test_template_is_plain_json(self):
        for mode in MODES:
            json.dumps(plotly_theme.template(mode))

    def test_template_uses_the_tokens(self):
        for mode in MODES:
            p = load().palette(mode)
            layout = plotly_theme.template(mode)["layout"]
            self.assertEqual(layout["colorway"], list(load().categorical(mode)))
            self.assertEqual(layout["yaxis"]["gridcolor"], p.rule)
            self.assertEqual(layout["font"]["color"], p.ink)
            self.assertTrue(layout["xaxis"]["tickfont"]["family"].startswith('"Cascadia Mono"'))
            self.assertTrue(layout["font"]["family"].startswith('"Segoe UI Variable Text"'))
            self.assertEqual(layout["hoverlabel"]["bgcolor"], p.surface)
            self.assertEqual(layout["paper_bgcolor"], "rgba(0,0,0,0)")
        self.assertEqual(plotly_theme.template("light", transparent=False)["layout"]["plot_bgcolor"], "#ffffff")

    def test_scales(self):
        p = load().palette("light")
        div = plotly_theme.diverging_scale("light")
        self.assertEqual((div[0], div[-1]), ([0.0, p.down], [1.0, p.up]))
        self.assertEqual(div[5][1], load().diverging_mid("light"))
        seq = plotly_theme.sequential_scale("dark")
        self.assertEqual(len(seq), 10)

    def test_roles(self):
        r = plotly_theme.roles("light")
        p = load().palette("light")
        self.assertEqual((r["fair_value"], r["buy"], r["sell"], r["playhead"], r["mid"]),
                         (p.model, p.up, p.down, p.navy, p.ink))

    def test_config(self):
        cfg = plotly_theme.config()
        self.assertFalse(cfg["displaylogo"])
        self.assertEqual(plotly_theme.config(displayModeBar=False)["displayModeBar"], False)

    def test_apply_copies_dict_figures(self):
        fig = {"data": [{"type": "scatter", "x": [1, 2], "y": [3, 4]}], "layout": {"title": {"text": "Snapshot"}}}
        before = copy.deepcopy(fig)
        out = plotly_theme.apply(fig, "dark")
        self.assertEqual(fig, before)
        self.assertEqual(out["layout"]["template"]["layout"]["font"]["color"], load().palette("dark").ink)
        self.assertEqual(out["layout"]["title"]["text"], "Snapshot")

    def test_empty_figure(self):
        fig = plotly_theme.empty_figure("Open Parquet data to begin.", "Use Open or Market library.")
        self.assertEqual(fig["data"], [])
        self.assertEqual(len(fig["layout"]["annotations"]), 2)
        self.assertFalse(fig["layout"]["xaxis"]["visible"])


@unittest.skipUnless(HAS_PLOTLY, "plotly not installed")
class PlotlyValidationTests(unittest.TestCase):
    def test_plotly_accepts_every_property(self):
        import plotly.graph_objects as go

        for mode in MODES:
            go.layout.Template(plotly_theme.template(mode))  # raises on any unknown property
            fig = go.Figure(go.Bar(x=["a", "b"], y=[1, -1]))
            plotly_theme.apply(fig, mode)
            go.Figure(plotly_theme.empty_figure("No data", "hint", mode))

    def test_register_sets_the_default(self):
        import plotly.io as pio

        previous = pio.templates.default
        try:
            name = plotly_theme.register("dark")
            self.assertEqual(name, "onedesk_dark")
            self.assertEqual(pio.templates.default, "onedesk_dark")
            self.assertIn("onedesk_light", pio.templates)
        finally:
            pio.templates.default = previous


if __name__ == "__main__":
    unittest.main()
