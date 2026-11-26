"""Driver-free keyboard and mouse output for Windows games.

The phone sends controller-shaped input over the LAN; this module maps it to
ordinary keyboard/mouse events using the Windows SendInput API. No virtual HID
or gamepad driver is installed or required. Games receive keyboard/mouse input,
not a virtual Xbox device.
"""
from __future__ import annotations

import ctypes
import os
import time
from typing import Any

BUTTON_BITS = {
    0: "A", 1: "B", 2: "X", 3: "Y",
    4: "LB", 5: "RB", 6: "BACK", 7: "START",
    8: "LS", 9: "RS", 10: "UP", 11: "DOWN",
    12: "LEFT", 13: "RIGHT", 14: "GUIDE",
}

# Default, broadly useful keyboard layout. The host dashboard shows the mapping.
BUTTON_KEYS = {
    "A": 0x20,       # Space
    "B": 0xA2,       # Left Ctrl
    "X": 0x45,       # E
    "Y": 0x51,       # Q
    "LB": 0xA0,      # Left Shift
    "RB": 0x52,      # R
    "BACK": 0x09,    # Tab
    "START": 0x1B,   # Escape
    "LS": 0xA4,      # Left Alt
    "RS": 0x46,      # F
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
}
STICK_KEYS = {"left": 0x41, "right": 0x44, "up": 0x57, "down": 0x53}  # A/D/W/S


class KeyboardMouseOutput:
    """Map controller state to standard Windows keyboard and mouse events."""

    def __init__(self) -> None:
        self.error: str | None = None
        self.ready = False
        self._held_keys: set[int] = set()
        self._held_mouse: set[str] = set()
        self._last_update = time.monotonic()
        self._fraction_x = 0.0
        self._fraction_y = 0.0
        self._user32: Any | None = None
        if os.name != "nt":
            self.error = "Keyboard/mouse injection is available on Windows only."
            return
        try:
            self._configure_send_input()
            self.ready = True
        except Exception as exc:
            self.error = f"Windows input initialization failed: {exc}"

    def _configure_send_input(self) -> None:
        from ctypes import wintypes

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t),
            ]

        class INPUTUNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _anonymous_ = ("union",)
            _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]

        self._input_type = INPUT
        self._key_input_type = KEYBDINPUT
        self._mouse_input_type = MOUSEINPUT
        self._user32 = ctypes.windll.user32
        self._user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self._user32.SendInput.restype = wintypes.UINT

    def _send_key(self, vk: int, down: bool) -> None:
        if not self._user32:
            return
        flags = 0 if down else 0x0002  # KEYEVENTF_KEYUP
        event = self._input_type(type=1, ki=self._key_input_type(wVk=vk, dwFlags=flags))
        self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(self._input_type))

    def _send_mouse(self, flags: int, dx: int = 0, dy: int = 0) -> None:
        if not self._user32:
            return
        event = self._input_type(type=0, mi=self._mouse_input_type(dx=dx, dy=dy, dwFlags=flags))
        self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(self._input_type))

    @staticmethod
    def _axis(value: int) -> float:
        result = (value - 128) / (127 if value >= 128 else 128)
        if abs(result) < 0.22:
            return 0.0
        return (abs(result) - 0.22) / 0.78 * (1 if result > 0 else -1)

    def _wanted_keys(self, state: dict[str, Any]) -> set[int]:
        wanted = {BUTTON_KEYS[name] for name in state["buttons"] if name in BUTTON_KEYS}
        axes = state["axes"]
        lx, ly = self._axis(axes["lx"]), self._axis(axes["ly"])
        if lx < 0: wanted.add(STICK_KEYS["left"])
        if lx > 0: wanted.add(STICK_KEYS["right"])
        if ly > 0: wanted.add(STICK_KEYS["up"])
        if ly < 0: wanted.add(STICK_KEYS["down"])
        return wanted

    def _sync_keys(self, wanted: set[int]) -> None:
        for key in self._held_keys - wanted:
            self._send_key(key, False)
        for key in wanted - self._held_keys:
            self._send_key(key, True)
        self._held_keys = wanted

    def _sync_mouse_buttons(self, state: dict[str, Any]) -> None:
        wanted: set[str] = set()
        if state["rt"] > 0:
            wanted.add("left")
        if state["lt"] > 0:
            wanted.add("right")
        flags = {
            "left": (0x0002, 0x0004),
            "right": (0x0008, 0x0010),
            "middle": (0x0020, 0x0040),
        }
        for name in self._held_mouse - wanted:
            self._send_mouse(flags[name][1])
        for name in wanted - self._held_mouse:
            self._send_mouse(flags[name][0])
        self._held_mouse = wanted

    def _move_mouse(self, state: dict[str, Any]) -> None:
        now = time.monotonic()
        elapsed = min(now - self._last_update, 0.35)
        self._last_update = now
        axes = state["axes"]
        # Right stick drives relative mouse movement at 520 px/sec at full deflection.
        self._fraction_x += self._axis(axes["rx"]) * 520 * elapsed
        self._fraction_y -= self._axis(axes["ry"]) * 520 * elapsed
        dx, dy = int(self._fraction_x), int(self._fraction_y)
        self._fraction_x -= dx
        self._fraction_y -= dy
        if dx or dy:
            self._send_mouse(0x0001, dx, dy)  # MOUSEEVENTF_MOVE, relative motion

    def apply(self, state: dict[str, Any]) -> None:
        if not self.ready:
            return
        self._sync_keys(self._wanted_keys(state))
        self._sync_mouse_buttons(state)
        self._move_mouse(state)

    def release_all(self) -> None:
        for key in self._held_keys:
            self._send_key(key, False)
        self._held_keys.clear()
        for name, up_flag in (("left", 0x0004), ("right", 0x0010), ("middle", 0x0040)):
            if name in self._held_mouse:
                self._send_mouse(up_flag)
        self._held_mouse.clear()
        self._fraction_x = self._fraction_y = 0.0
