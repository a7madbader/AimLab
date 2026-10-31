import unittest

from aimlab.mouse import calculations as c


class CalcTests(unittest.TestCase):
    def test_known_cm360_values(self):
        # Widely published reference values
        self.assertAlmostEqual(c.cm_per_360(800, 1.0, c.GAME_YAW["cs2"]), 51.95, delta=0.05)
        self.assertAlmostEqual(c.cm_per_360(800, 0.35, c.GAME_YAW["valorant"]), 46.65, delta=0.1)

    def test_roundtrip(self):
        s = c.sensitivity_for_cm360(1600, 30.0, c.GAME_YAW["apex"])
        self.assertAlmostEqual(c.cm_per_360(1600, s, c.GAME_YAW["apex"]), 30.0, places=6)

    def test_doubling_dpi_halves_distance(self):
        a = c.cm_per_360(800, 1.0, 0.022)
        b = c.cm_per_360(1600, 1.0, 0.022)
        self.assertAlmostEqual(a / b, 2.0, places=9)

    def test_edpi_and_pad(self):
        self.assertEqual(c.edpi(800, 0.5), 400)
        self.assertAlmostEqual(c.degrees_on_pad(45, 36, 0.8), 360.0)
        self.assertAlmostEqual(c.pad_needed_cm(40, 180), 20.0)

    def test_dpi_from_counts(self):
        self.assertAlmostEqual(c.dpi_from_counts(800 * 20 / 2.54, 20), 800, places=6)

    def test_invalid_inputs_rejected(self):
        for bad in ((0, 1, 0.022), (800, 0, 0.022), (800, 1, 0), (-5, 1, 0.022)):
            with self.assertRaises(ValueError):
                c.cm_per_360(*bad)
        with self.assertRaises(ValueError):
            c.dpi_from_counts(100, 0)

    def test_nearest(self):
        self.assertEqual(c.nearest(812, c.COMMON_DPI), 800)


if __name__ == "__main__":
    unittest.main()
