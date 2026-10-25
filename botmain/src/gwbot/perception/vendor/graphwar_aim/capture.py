"""Screen / window capture.

Uses ``PIL.ImageGrab`` (bundled with Pillow), so no extra dependency is
needed.  On Windows the module can also enumerate windows and grab the client
area of one of them (via ``ctypes``/user32) and enables DPI awareness so that
window coordinates match screenshot pixels at 125 %/150 % display scaling.
On macOS and Linux those helpers degrade gracefully: the window list is empty
and the app falls back to full-screen capture plus automatic plot detection.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

try:  # ImageGrab is unavailable on some headless Linux builds of Pillow
    from PIL import ImageGrab
except ImportError:  # pragma: no cover
    ImageGrab = None  # type: ignore[assignment]

IS_WINDOWS = sys.platform.startswith("win")


# --------------------------------------------------------------------------- #
# DPI awareness (Windows only) — without it GetWindowRect and ImageGrab use
# different units when the display is scaled, shifting every detection.
# --------------------------------------------------------------------------- #
def enable_dpi_awareness() -> None:
    if not IS_WINDOWS:
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


enable_dpi_awareness()


# --------------------------------------------------------------------------- #
# Basic capture
# --------------------------------------------------------------------------- #
def grab_screen(bbox: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """Screenshot (or region ``bbox=(l,t,r,b)``) as a BGR array for OpenCV."""
    if ImageGrab is None:
        raise RuntimeError("PIL.ImageGrab is not available on this platform")
    try:
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
    except TypeError:  # older Pillow without all_screens
        img = ImageGrab.grab(bbox=bbox)
    arr = np.array(img.convert("RGB"))
    return arr[:, :, ::-1].copy()  # RGB -> BGR


def imread_unicode(path: str) -> np.ndarray | None:
    """Read an image from any path (Cyrillic/spaces) — cv2.imread cannot."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# Window enumeration and capture (Windows)
# --------------------------------------------------------------------------- #
def list_windows() -> list[tuple[int, str]]:
    """Visible top-level windows with a title: ``[(hwnd, title), ...]``.

    Returns an empty list on non-Windows platforms.
    """
    if not IS_WINDOWS:
        return []
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    out: list[tuple[int, str]] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if not title:
            return True
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if rect.right - rect.left < 120 or rect.bottom - rect.top < 120:
                return True  # tray/helper windows
        out.append((int(hwnd), title))
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)
    return out


def find_hwnd(title_substring: str = "Graphwar") -> int | None:
    """Find a window, preferring an exact title match over a substring.

    The substring can match an editor tab or chat window whose title happens
    to contain the game's name. The game itself is titled exactly "Graphwar".
    """
    needle = title_substring.lower()
    fallback: int | None = None
    for hwnd, title in list_windows():
        if title.lower() == needle:
            return hwnd
        if fallback is None and needle in title.lower():
            fallback = hwnd
    return fallback


def _bring_to_front(hwnd: int) -> None:
    if not IS_WINDOWS:
        return
    import ctypes

    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:  # noqa: BLE001
        pass


def window_client_bbox(hwnd: int) -> tuple[int, int, int, int] | None:
    """Screen bbox of a window's CLIENT area (no title bar / borders)."""
    if not IS_WINDOWS:
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None
    pt = POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    return (pt.x, pt.y, pt.x + w, pt.y + h)


def grab_hwnd(hwnd: int) -> tuple[np.ndarray | None, tuple[int, int, int, int] | None]:
    """Capture the client area of a window."""
    _bring_to_front(hwnd)
    bbox = window_client_bbox(hwnd)
    if bbox is None:
        return None, None
    return grab_screen(bbox), bbox


def grab_game(title_substring: str = "Graphwar") -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
    """Capture the game window if found (Windows), otherwise the whole screen."""
    hwnd = find_hwnd(title_substring)
    if hwnd is not None:
        frame, bbox = grab_hwnd(hwnd)
        if frame is not None:
            return frame, bbox
    return grab_screen(None), None
