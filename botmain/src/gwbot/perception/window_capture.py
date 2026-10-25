"""Off-screen capture of a Windows game window.

Adapted from GraphBot's ``core/game_capture.py`` and ``core/window_capture.py``.
GraphBot is MIT licensed, Copyright (c) 2024 KroSheChKa. See
``THIRD_PARTY_NOTICES.txt``.

Why this exists: ``PIL.ImageGrab`` captures desktop pixels and may require the
game window to be visible or focused. ``PrintWindow`` renders the client area
off-screen, so the assistant can sample the board without stealing focus and
without accidentally reading another window that happens to be on top.

The module degrades gracefully when pywin32 is unavailable. Callers should
fall back to the vendored graphwar-aim screen grabber in that case.
"""

from __future__ import annotations

import ctypes

import cv2
import numpy as np

try:
    import win32gui
    import win32ui

    HAS_WIN32 = True
except ImportError:  # pragma: no cover - exercised only on non-Windows/minimal installs
    HAS_WIN32 = False

PW_CLIENTONLY = 0x00000001


def _enable_dpi_awareness() -> None:
    """Keep Win32 coordinates in the same pixel space as the capture."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


_enable_dpi_awareness()


def find_window(title_substring: str = "Graphwar") -> int | None:
    """Find the best visible top-level window matching *title_substring*.

    Several windows can contain the substring: an editor tab, a chat window, or
    a hidden launcher. Returning the first EnumWindows hit is wrong. Prefer an
    exact title match, then a window with a non-empty client area, then a
    non-minimised window. The Java game window is titled exactly "Graphwar";
    the launcher frame has a zero-sized client area.
    """
    if not HAS_WIN32:
        return None

    from ctypes import wintypes

    user32 = ctypes.windll.user32
    needle = title_substring.lower()
    found: list[tuple[int, int]] = []  # (score, hwnd)
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if needle not in title.lower():
            return True

        score = 100 if title.lower() == needle else 0
        rect = wintypes.RECT()
        if user32.GetClientRect(hwnd, ctypes.byref(rect)):
            if rect.right - rect.left > 0 and rect.bottom - rect.top > 0:
                score += 50
        if not user32.IsIconic(hwnd):
            score += 20
        found.append((score, int(hwnd)))
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    if not found:
        return None
    return max(found)[1]


def _print_window(hwnd: int, device_context) -> bool:
    """Call PrintWindow from user32 (not exported by every pywin32 build)."""
    user32 = ctypes.windll.user32
    user32.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    user32.PrintWindow.restype = ctypes.c_bool
    return bool(user32.PrintWindow(hwnd, device_context, PW_CLIENTONLY))


def grab_client_bgr(hwnd: int) -> np.ndarray:
    """Render a window's client area off-screen and return a BGR array."""
    if not HAS_WIN32:
        raise RuntimeError("pywin32 is not available")

    _, _, width, height = win32gui.GetClientRect(hwnd)
    if width < 1 or height < 1:
        raise RuntimeError("Game window has no drawable client area")

    window_dc_handle = None
    window_dc = None
    memory_dc = None
    bitmap = None
    previous_bitmap = None
    try:
        window_dc_handle = win32gui.GetWindowDC(hwnd)
        window_dc = win32ui.CreateDCFromHandle(window_dc_handle)
        memory_dc = window_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(window_dc, width, height)
        previous_bitmap = memory_dc.SelectObject(bitmap)

        if not _print_window(hwnd, memory_dc.GetSafeHdc()):
            raise RuntimeError("Windows could not render the game window off-screen")

        bgra = np.frombuffer(bitmap.GetBitmapBits(True), dtype=np.uint8)
        bgra = bgra.reshape((height, width, 4))
        return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
    finally:
        if memory_dc is not None and previous_bitmap is not None:
            memory_dc.SelectObject(previous_bitmap)
        if bitmap is not None:
            win32gui.DeleteObject(bitmap.GetHandle())
        if memory_dc is not None:
            memory_dc.DeleteDC()
        if window_dc is not None:
            window_dc.DeleteDC()
        if window_dc_handle is not None:
            win32gui.ReleaseDC(hwnd, window_dc_handle)


def grab_game_client(title_substring: str = "Graphwar") -> tuple[np.ndarray | None, int | None]:
    """Capture the game's client area, or return ``(None, None)`` if not found."""
    hwnd = find_window(title_substring)
    if hwnd is None:
        return None, None
    return grab_client_bgr(hwnd), hwnd
