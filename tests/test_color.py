import unittest

from onedesk import color


class ColorMathTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(color.normalize("#ABC"), "#aabbcc")
        self.assertEqual(color.normalize("#0D3B70"), "#0d3b70")
        for bad in ("0d3b70", "#12345", "navy", "", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                color.normalize(bad)

    def test_rgb_round_trip(self):
        for value in ("#000000", "#ffffff", "#0d3b70", "#c39af5"):
            self.assertEqual(color.to_hex(color.to_rgb(value)), value)

    def test_mix_matches_css_color_mix(self):
        self.assertEqual(color.mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(color.mix("#a15c07", "#ffffff", 1.0), "#a15c07")
        self.assertEqual(color.mix("#a15c07", "#ffffff", 0.0), "#ffffff")
        with self.assertRaises(ValueError):
            color.mix("#000000", "#ffffff", 1.5)

    def test_contrast(self):
        self.assertAlmostEqual(color.contrast("#000000", "#ffffff"), 21.0, places=6)
        self.assertAlmostEqual(color.contrast("#777777", "#777777"), 1.0, places=6)
        self.assertEqual(color.contrast("#0d3b70", "#ffffff"), color.contrast("#ffffff", "#0d3b70"))

    def test_rgba(self):
        self.assertEqual(color.rgba("#6a4bb5", 0.12), "rgba(106,75,181,0.12)")

    def test_oklab_round_trip_and_mixing(self):
        for value in ("#157a3a", "#b42318", "#2a78d6", "#eef1f4"):
            self.assertLess(color.delta_e(color.from_oklab(color.to_oklab(value)), value), 0.5)
        self.assertEqual(color.mix_oklab("#157a3a", "#eef1f4", 1.0), "#157a3a")
        self.assertEqual(color.mix_oklab("#157a3a", "#eef1f4", 0.0), "#eef1f4")
        self.assertEqual(color.delta_e("#123456", "#123456"), 0.0)


if __name__ == "__main__":
    unittest.main()
