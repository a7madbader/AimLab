"""Mouse capture front door. The real Windows implementation lives in windows_raw_input.py
and is only imported on Windows, so the rest of the program (and the tests) work anywhere."""
import sys


class CaptureError(Exception):
    pass


class UnavailableCapture:
    """Used on non-Windows systems: always reports that capture is not possible."""
    available = False

    def start(self):
        raise CaptureError("Raw mouse capture is only available on Windows.")

    def stop(self):
        pass

    def drain(self):
        return []


def create_capture():
    if sys.platform == "win32":
        from .windows_raw_input import RawInputCapture
        return RawInputCapture()
    return UnavailableCapture()
