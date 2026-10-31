"""Windows Raw Input mouse capture using ctypes (no extra dependencies).

A hidden window runs in its own thread, registers for raw mouse input and records every
WM_INPUT report as Sample(timestamp, dx, dy). dx/dy are the mouse's own counts, before
Windows pointer acceleration or speed settings are applied.

Limits (also explained to the user in the app): the timestamp is taken when this program
processes the message, not inside the mouse; at very high polling rates (4000 Hz+) one
message per report may be too slow for Python and the measured rate can read low.
"""
import ctypes
import itertools
import logging
import threading
import time
from ctypes import wintypes as w

from .analysis import Sample
from .capture import CaptureError

log = logging.getLogger("aimlab.rawinput")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_CLOSE, WM_DESTROY, WM_INPUT = 0x0010, 0x0002, 0x00FF
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
MOUSE_MOVE_ABSOLUTE = 0x01

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", w.HINSTANCE), ("hIcon", w.HANDLE),
                ("hCursor", w.HANDLE), ("hbrBackground", w.HANDLE),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", w.USHORT), ("usUsage", w.USHORT),
                ("dwFlags", w.DWORD), ("hwndTarget", w.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", w.DWORD), ("dwSize", w.DWORD),
                ("hDevice", w.HANDLE), ("wParam", w.WPARAM)]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [("usFlags", w.USHORT), ("ulButtons", w.ULONG), ("ulRawButtons", w.ULONG),
                ("lLastX", w.LONG), ("lLastY", w.LONG), ("ulExtraInformation", w.ULONG)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", w.HWND), ("message", w.UINT), ("wParam", w.WPARAM),
                ("lParam", w.LPARAM), ("time", w.DWORD), ("pt", w.POINT)]


user32.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = w.ATOM
user32.UnregisterClassW.argtypes = [w.LPCWSTR, w.HINSTANCE]
user32.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU,
                                   w.HINSTANCE, w.LPVOID]
user32.CreateWindowExW.restype = w.HWND
user32.DestroyWindow.argtypes = [w.HWND]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), w.HWND, w.UINT, w.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), w.UINT, w.UINT]
user32.RegisterRawInputDevices.restype = w.BOOL
user32.GetRawInputData.argtypes = [ctypes.c_void_p, w.UINT, ctypes.c_void_p,
                                   ctypes.POINTER(w.UINT), w.UINT]
user32.GetRawInputData.restype = w.UINT
kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]
kernel32.GetModuleHandleW.restype = w.HMODULE

_counter = itertools.count()


class RawInputCapture:
    available = True

    def __init__(self):
        self._samples = []
        self._lock = threading.Lock()
        self._thread = None
        self._hwnd = None
        self._ready = threading.Event()
        self._error = None
        self._wndproc_ref = None
        self._class_name = f"AimLabRawInput{next(_counter)}"

    # ---- public API
    def start(self):
        if self._thread and self._thread.is_alive():
            raise CaptureError("Capture already running.")
        self._samples = []
        self._error = None
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="aimlab-rawinput", daemon=True)
        self._thread.start()
        if not self._ready.wait(3.0):
            raise CaptureError("Timed out starting raw input capture.")
        if self._error:
            raise CaptureError(self._error)

    def stop(self):
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._hwnd = None

    def drain(self):
        """Return all samples recorded so far and clear the buffer."""
        with self._lock:
            out, self._samples = self._samples, []
        return out

    # ---- internals
    def _on_input(self, lparam):
        t = time.perf_counter_ns()
        hdr = ctypes.sizeof(RAWINPUTHEADER)
        size = w.UINT(0)
        if user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), hdr) != 0:
            return
        if size.value < ctypes.sizeof(RAWINPUT):
            return
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), hdr) != size.value:
            return
        ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        if ri.header.dwType != RIM_TYPEMOUSE or ri.mouse.usFlags & MOUSE_MOVE_ABSOLUTE:
            return
        dx, dy = ri.mouse.lLastX, ri.mouse.lLastY
        if dx or dy:
            with self._lock:
                self._samples.append(Sample(t, dx, dy))

    def _run(self):
        def wndproc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_INPUT:
                    self._on_input(lparam)
                elif msg == WM_CLOSE:
                    user32.DestroyWindow(hwnd)
                    return 0
                elif msg == WM_DESTROY:
                    user32.PostQuitMessage(0)
                    return 0
            except Exception:
                log.exception("Error in raw input window procedure")
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(wndproc)      # keep alive for the whole thread
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = self._class_name
        registered = False
        try:
            if not user32.RegisterClassW(ctypes.byref(wc)):
                raise OSError(f"RegisterClassW failed ({ctypes.get_last_error()})")
            registered = True
            # A normal (never shown) window: message-only windows may not receive WM_INPUT.
            self._hwnd = user32.CreateWindowExW(0, self._class_name, "AimLabRawInput", 0,
                                                0, 0, 0, 0, None, None, hinst, None)
            if not self._hwnd:
                raise OSError(f"CreateWindowExW failed ({ctypes.get_last_error()})")
            rid = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, self._hwnd)   # generic desktop / mouse
            if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid)):
                raise OSError(f"RegisterRawInputDevices failed ({ctypes.get_last_error()})")
        except OSError as e:
            log.error("Raw input setup failed: %s", e)
            self._error = str(e)
            self._ready.set()
            if registered:
                user32.UnregisterClassW(self._class_name, hinst)
            return
        self._ready.set()
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnregisterClassW(self._class_name, hinst)
