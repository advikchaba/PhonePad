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

# Clear, familiar defaults for keyboard-and-mouse games (especially FPS games).
# Each face/shoulder/menu/stick-click/trigger can be changed in the desktop app.
DEFAULT_BUTTON_BINDINGS = {
    "A": "Space", "B": "Left Ctrl", "X": "E", "Y": "Q",
    "LB": "Left Shift", "RB": "R", "BACK": "Tab", "START": "Escape",
    "LS": "Left Alt", "RS": "F",
    "UP": "Up Arrow", "DOWN": "Down Arrow", "LEFT": "Left Arrow", "RIGHT": "Right Arrow",
    "LT": "Mouse Right", "RT": "Mouse Left", "GUIDE": "None",
}

KEY_CODES = {
    "Space": 0x20, "Left Ctrl": 0xA2, "Right Ctrl": 0xA3,
    "Left Shift": 0xA0, "Right Shift": 0xA1,
    "Left Alt": 0xA4, "Right Alt": 0xA5,
    "Tab": 0x09, "Escape": 0x1B, "Enter": 0x0D, "Backspace": 0x08,
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59, "Z": 0x5A,
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
    "Up Arrow": 0x26, "Down Arrow": 0x28, "Left Arrow": 0x25, "Right Arrow": 0x27,
}
MOUSE_FLAGS = {
    "Mouse Left": (0x0002, 0x0004),
    "Mouse Right": (0x0008, 0x0010),
    "Mouse Middle": (0x0020, 0x0040),
}
EXTENDED_KEYS = {KEY_CODES[name] for name in ("Right Ctrl", "Right Alt", "Up Arrow", "Down Arrow", "Left Arrow", "Right Arrow")}
BINDING_CHOICES = ("None", *KEY_CODES.keys(), *MOUSE_FLAGS.keys())
STICK_KEYS = {"left": KEY_CODES["A"], "right": KEY_CODES["D"], "up": KEY_CODES["W"], "down": KEY_CODES["S"]}


def keyboard_mouse_state(
    state: dict[str, Any], mapping: dict[str, str] | None = None,
) -> tuple[set[int], set[str]]:
    """Translate current controller state into held virtual keys and mouse buttons."""
    bindings = mapping or DEFAULT_BUTTON_BINDINGS
    buttons = set(state["buttons"])
    keys: set[int] = set()
    mouse: set[str] = set()

    def add_action(action: str | None) -> None:
        if action in KEY_CODES:
            keys.add(KEY_CODES[action])
        elif action in MOUSE_FLAGS:
            mouse.add(action)

    for name in buttons:
        add_action(bindings.get(name))
    axes = state["axes"]
    lx = (axes["lx"] - 128) / (127 if axes["lx"] >= 128 else 128)
    ly = (axes["ly"] - 128) / (127 if axes["ly"] >= 128 else 128)
    if lx < -0.22: keys.add(STICK_KEYS["left"])
    if lx > 0.22: keys.add(STICK_KEYS["right"])
    if ly > 0.22: keys.add(STICK_KEYS["up"])
    if ly < -0.22: keys.add(STICK_KEYS["down"])
    if state["lt"] > 0: add_action(bindings.get("LT"))
    if state["rt"] > 0: add_action(bindings.get("RT"))
    return keys, mouse


class KeyboardMouseOutput:
    """Map controller state to standard Windows keyboard and mouse events."""

    def __init__(self) -> None:
        self.error: str | None = None
        self.ready = False
        self.button_mapping = DEFAULT_BUTTON_BINDINGS.copy()
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

    def set_button_mapping(self, mapping: dict[str, str]) -> None:
        """Validate and apply a personalized controller-to-key mapping."""
        if not isinstance(mapping, dict):
            raise ValueError("Button mapping must be an object")
        updated = DEFAULT_BUTTON_BINDINGS.copy()
        for name in updated:
            action = mapping.get(name, updated[name])
            if action not in BINDING_CHOICES:
                raise ValueError(f"Unsupported mapping for {name}: {action}")
            updated[name] = action
        self.release_all()
        self.button_mapping = updated

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
        flags = (0x0001 if vk in EXTENDED_KEYS else 0) | (0 if down else 0x0002)  # EXTENDEDKEY / KEYUP
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

    def _wanted_inputs(self, state: dict[str, Any]) -> tuple[set[int], set[str]]:
        return keyboard_mouse_state(state, self.button_mapping)

    def _sync_keys(self, wanted: set[int]) -> None:
        for key in self._held_keys - wanted:
            self._send_key(key, False)
        for key in wanted - self._held_keys:
            self._send_key(key, True)
        self._held_keys = wanted

    def _sync_mouse(self, wanted: set[str]) -> None:
        for name in self._held_mouse - wanted:
            self._send_mouse(MOUSE_FLAGS[name][1])
        for name in wanted - self._held_mouse:
            self._send_mouse(MOUSE_FLAGS[name][0])
        self._held_mouse = wanted

    def _move_mouse(self, state: dict[str, Any]) -> None:
        now = time.monotonic()
        elapsed = min(now - self._last_update, 0.35)
        self._last_update = now
        axes = state["axes"]
        # The right stick drives relative mouse movement at 520 px/sec at full deflection.
        rx = self._axis(axes["rx"])
        ry = self._axis(axes["ry"])
        self._fraction_x += rx * 520 * elapsed
        self._fraction_y -= ry * 520 * elapsed
        dx, dy = int(self._fraction_x), int(self._fraction_y)
        self._fraction_x -= dx
        self._fraction_y -= dy
        if dx or dy:
            self._send_mouse(0x0001, dx, dy)  # MOUSEEVENTF_MOVE, relative motion

    def apply(self, state: dict[str, Any]) -> None:
        if not self.ready:
            return
        keys, mouse = self._wanted_inputs(state)
        self._sync_keys(keys)
        self._sync_mouse(mouse)
        self._move_mouse(state)

    def release_all(self) -> None:
        for key in self._held_keys:
            self._send_key(key, False)
        self._held_keys.clear()
        for name in self._held_mouse:
            self._send_mouse(MOUSE_FLAGS[name][1])
        self._held_mouse.clear()
        self._fraction_x = self._fraction_y = 0.0
