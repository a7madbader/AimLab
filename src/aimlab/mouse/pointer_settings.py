"""Reads the Windows pointer settings (Enhance Pointer Precision, pointer speed)."""
import ctypes
import sys
from dataclasses import dataclass

SPI_GETMOUSE = 0x0003
SPI_GETMOUSESPEED = 0x0070


@dataclass
class PointerSettings:
    enhance_precision: bool     # "Enhance pointer precision" = Windows mouse acceleration
    speed: int                  # 1..20, 10 = neutral (1:1)


def parse_pointer_settings(mouse_params, speed) -> PointerSettings:
    """mouse_params = [threshold1, threshold2, acceleration] from SPI_GETMOUSE."""
    return PointerSettings(enhance_precision=mouse_params[2] != 0, speed=int(speed))


def get_pointer_settings():
    """Returns PointerSettings, or None when not on Windows or the query fails."""
    if sys.platform != "win32":
        return None
    user32 = ctypes.windll.user32
    params = (ctypes.c_int * 3)()
    speed = ctypes.c_int()
    if not user32.SystemParametersInfoW(SPI_GETMOUSE, 0, params, 0):
        return None
    if not user32.SystemParametersInfoW(SPI_GETMOUSESPEED, 0, ctypes.byref(speed), 0):
        return None
    return parse_pointer_settings(list(params), speed.value)
