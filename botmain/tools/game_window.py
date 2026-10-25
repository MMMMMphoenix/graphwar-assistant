"""Drive the Java game window for testing (click, type, screenshot, geometry).

This is a test harness, not part of the assistant. The assistant never clicks
or types on its own: it only reads the screen and, by default, hands the
recommendation to a human. This tool exists so that a match can be set up
reproducibly while perception and calibration are being developed.

Why the click code looks unusual
--------------------------------
The Java frame is DPI-unaware while this process is DPI-aware. Windows
virtualises screen coordinates for the unaware window, so a real cursor click
at client position (x, y) does not arrive at AWT as (x, y) and the click lands
somewhere else. AWT hit-tests on the coordinates carried by the window
message, so posting WM_LBUTTONDOWN/WM_LBUTTONUP with CLIENT coordinates is
exact and does not depend on the cursor, focus, or display scaling.

Usage (run from botmain):

    py -3 tools/game_window.py info
    py -3 tools/game_window.py shot debug/menu
    py -3 tools/game_window.py click 395 440
    py -3 tools/game_window.py postclick 315 500
    py -3 tools/game_window.py type botroom
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import cv2
import win32api

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gwbot.perception import window_capture as wc  # noqa: E402

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_SHIFT = 0x10
VK = {c: 0x41 + i for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
VK.update({str(d): 0x30 + d for d in range(10)})

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202


def find_game_window() -> int:
    hwnd = wc.find_window("Graphwar")
    if hwnd is None:
        raise SystemExit("Graphwar window not found; start it with game/run.sh")
    return hwnd


def focus(hwnd: int) -> None:
    """Bring the window to the foreground, working around foreground lock."""
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    cur_thread = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(fg_thread, cur_thread, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        user32.AttachThreadInput(fg_thread, cur_thread, False)
    time.sleep(0.4)


def client_origin(hwnd: int) -> tuple[int, int]:
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return int(pt.x), int(pt.y)


def click(hwnd: int, x: int, y: int) -> None:
    """Real cursor click at physical client coordinates."""
    focus(hwnd)
    ox, oy = client_origin(hwnd)
    user32.SetCursorPos(ox + x, oy + y)
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    time.sleep(0.5)


def post_click(hwnd: int, x: int, y: int) -> None:
    """Click by posting client coordinates straight to the window.

    Preferred for the Java frame: immune to DPI virtualisation, focus, and the
    cursor being somewhere else.
    """
    lparam = (y << 16) | (x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam)  # MK_LBUTTON
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
    time.sleep(0.5)


def type_text(text: str) -> None:
    for ch in text:
        low = ch.lower()
        if low not in VK:
            raise SystemExit(f"unsupported character: {ch!r}")
        if ch.isupper():
            win32api.keybd_event(VK_SHIFT, 0, 0, 0)
            time.sleep(0.02)
        win32api.keybd_event(VK[low], 0, 0, 0)
        time.sleep(0.02)
        win32api.keybd_event(VK[low], 0, 2, 0)
        if ch.isupper():
            time.sleep(0.02)
            win32api.keybd_event(VK_SHIFT, 0, 2, 0)
        time.sleep(0.05)


def save(tag: str) -> Path:
    img = wc.grab_client_bgr(find_game_window())
    path = ROOT / "debug" / f"{tag}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)
    print(path, img.shape)
    return path


def info() -> None:
    hwnd = find_game_window()
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    ox, oy = client_origin(hwnd)
    img = wc.grab_client_bgr(hwnd)
    print(
        f"hwnd={hwnd} client={rect.right - rect.left}x{rect.bottom - rect.top} "
        f"origin=({ox},{oy}) capture={img.shape[1]}x{img.shape[0]}"
    )


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    cmd = argv[1]
    hwnd = find_game_window()

    if cmd == "info":
        info()
    elif cmd == "shot":
        save(argv[2])
    elif cmd == "click":
        click(hwnd, int(argv[2]), int(argv[3]))
    elif cmd == "postclick":
        post_click(hwnd, int(argv[2]), int(argv[3]))
    elif cmd == "type":
        focus(hwnd)
        type_text(argv[2])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv)
