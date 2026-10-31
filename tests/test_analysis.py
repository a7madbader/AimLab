import unittest

from aimlab.mouse.analysis import (Sample, analyze_acceleration, analyze_dpi, analyze_movement,
                                   analyze_polling, swipe_from_samples)
from tests.synth import steady_stream, swipe


class PollingTests(unittest.TestCase):
    def test_1000hz_and_500hz(self):
        r = analyze_polling(steady_stream(1000, 5, jitter_ms=0.05))
        self.assertTrue(r.ok)
        self.assertAlmostEqual(r.hz, 1000, delta=15)
        self.assertEqual(r.nearest_common_hz, 1000)
        r = analyze_polling(steady_stream(500, 5))
        self.assertAlmostEqual(r.hz, 500, delta=5)
        self.assertEqual(r.nearest_common_hz, 500)

    def test_pauses_are_ignored(self):
        a = steady_stream(1000, 2)
        gap = a[-1].t_ns + 500_000_000          # half-second pause
        b = [Sample(gap + s.t_ns, s.dx, s.dy) for s in steady_stream(1000, 2)]
        r = analyze_polling(a + b)
        self.assertTrue(r.ok)
        self.assertAlmostEqual(r.hz, 1000, delta=15)

    def test_bursty_delivery_does_not_inflate_rate(self):
        # reports are 1 ms apart in reality but delivered in bursts of 10 (same timestamp spacing 10us)
        out, t = [], 0
        for burst in range(300):
            t += 10_000_000
            for i in range(10):
                out.append(Sample(t + i * 10_000, 2, 0))
        r = analyze_polling(out)
        self.assertTrue(r.ok)
        self.assertAlmostEqual(r.hz, 1000, delta=60)

    def test_insufficient_data_refused(self):
        r = analyze_polling(steady_stream(1000, 0.05))
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "insufficient")
        self.assertFalse(analyze_polling([]).ok)

    def test_zero_movement_events_ignored(self):
        self.assertFalse(analyze_polling(steady_stream(1000, 1, dx_per_report=0)).ok)


class DpiTests(unittest.TestCase):
    def test_800_dpi_over_20cm(self):
        counts = round(800 * 20 / 2.54)
        r = analyze_dpi(swipe(counts, 1.0), 20)
        self.assertTrue(r.ok)
        self.assertAlmostEqual(r.dpi, 800, delta=1)
        self.assertEqual(r.nearest_common, 800)

    def test_sideways_drift_does_not_inflate(self):
        counts = round(800 * 20 / 2.54)
        r = analyze_dpi(swipe(counts, 1.0, wobble_counts=300), 20)
        self.assertAlmostEqual(r.dpi, 800, delta=5)

    def test_no_movement_refused(self):
        r = analyze_dpi([], 20)
        self.assertFalse(r.ok)
        with self.assertRaises(ValueError):
            analyze_dpi(swipe(1000, 1), 0)


class AccelerationTests(unittest.TestCase):
    def _swipes(self, counts_by_speed):
        out = []
        for label, (counts, dur) in counts_by_speed.items():
            out.append(swipe_from_samples(label, swipe(counts, dur)))
        return out

    def test_no_acceleration(self):
        r = analyze_acceleration(self._swipes({"slow": (6300, 1.5), "medium": (6290, 0.6), "fast": (6330, 0.2)}))
        self.assertEqual(r.status, "none")
        self.assertGreater(r.speed_ratio, 3)

    def test_clear_acceleration(self):
        r = analyze_acceleration(self._swipes({"slow": (6300, 1.5), "medium": (6900, 0.6), "fast": (7800, 0.2)}))
        self.assertEqual(r.status, "likely")
        self.assertGreater(r.deviation_pct, 15)

    def test_possible_acceleration(self):
        r = analyze_acceleration(self._swipes({"slow": (6300, 1.5), "fast": (6900, 0.2)}))
        self.assertEqual(r.status, "possible")

    def test_similar_speeds_inconclusive(self):
        r = analyze_acceleration(self._swipes({"slow": (6300, 0.6), "fast": (7800, 0.4)}))
        self.assertEqual(r.status, "inconclusive")

    def test_too_few_swipes_inconclusive(self):
        self.assertEqual(analyze_acceleration([]).status, "inconclusive")


class MovementTests(unittest.TestCase):
    def test_perfect_steady_swipe(self):
        m = analyze_movement(swipe(6000, 1.0))
        self.assertTrue(m.ok)
        self.assertGreater(m.straightness_pct, 99)
        self.assertLess(m.wobble_pct, 1)
        self.assertLess(m.speed_cv_pct, 10)

    def test_wobbly_swipe_scores_worse(self):
        steady = analyze_movement(swipe(6000, 1.0))
        wobbly = analyze_movement(swipe(6000, 1.0, wobble_counts=600))
        self.assertGreater(wobbly.wobble_pct, steady.wobble_pct + 3)
        self.assertLess(wobbly.straightness_pct, steady.straightness_pct)

    def test_uneven_speed_scores_worse(self):
        steady = analyze_movement(swipe(6000, 1.0))
        uneven = analyze_movement(swipe(6000, 1.0, speed_profile=lambda p: 0.2 + (p > 0.5) * 2))
        self.assertGreater(uneven.speed_cv_pct, steady.speed_cv_pct + 20)

    def test_insufficient(self):
        self.assertFalse(analyze_movement([]).ok)
        self.assertFalse(analyze_movement(swipe(30, 0.05)).ok)


if __name__ == "__main__":
    unittest.main()


class PointerSettingsTests(unittest.TestCase):
    def test_parse(self):
        from aimlab.mouse.pointer_settings import get_pointer_settings, parse_pointer_settings
        on = parse_pointer_settings([6, 10, 1], 10)
        off = parse_pointer_settings([0, 0, 0], 12)
        self.assertTrue(on.enhance_precision)
        self.assertFalse(off.enhance_precision)
        self.assertEqual(off.speed, 12)
        import sys
        if sys.platform != "win32":
            self.assertIsNone(get_pointer_settings())

    def test_capture_unavailable_off_windows(self):
        import sys
        from aimlab.mouse.capture import CaptureError, create_capture
        if sys.platform != "win32":
            cap = create_capture()
            self.assertFalse(cap.available)
            with self.assertRaises(CaptureError):
                cap.start()
