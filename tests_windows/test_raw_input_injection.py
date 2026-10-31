"""Windows-only hardware-path test: injects synthetic mouse movement with the OS and checks that
the Raw Input capture receives it. Run separately in CI (informational) because the build
server may not allow input injection."""
import ctypes
import sys
import time
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class RawInputInjection(unittest.TestCase):
    def test_injected_movement_is_captured(self):
        from aimlab.mouse.capture import create_capture
        cap = create_capture()
        cap.start()
        try:
            time.sleep(0.3)
            n, step = 200, 3
            for _ in range(n):
                ctypes.windll.user32.mouse_event(0x0001, step, 0, 0, 0)   # MOUSEEVENTF_MOVE
                time.sleep(0.002)
            time.sleep(0.3)
            samples = cap.drain()
        finally:
            cap.stop()
        print(f"\ninjected {n} moves x {step} counts; captured {len(samples)} reports, "
              f"sum dx = {sum(s.dx for s in samples)}")
        if not samples:
            self.skipTest("No raw input received - this machine may block synthetic input")
        self.assertEqual(sum(s.dx for s in samples), n * step)
        self.assertEqual(sum(s.dy for s in samples), 0)
        ts = [s.t_ns for s in samples]
        self.assertEqual(ts, sorted(ts))


if __name__ == "__main__":
    unittest.main()
