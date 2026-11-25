"""Windows virtual Xbox controller output via ViGEmBus."""
from __future__ import annotations

import os
from typing import Any


BUTTON_BITS = {
    0: "A", 1: "B", 2: "X", 3: "Y",
    4: "LB", 5: "RB", 6: "BACK", 7: "START",
    8: "LS", 9: "RS", 10: "UP", 11: "DOWN",
    12: "LEFT", 13: "RIGHT", 14: "GUIDE",
}


def _stick_value(value: int) -> int:
    """Convert an unsigned byte centered at 128 to an XInput stick value."""
    offset = value - 128
    return max(-32768, min(32767, int(offset * (32767 / (127 if offset >= 0 else 128)))))


class VirtualGamepad:
    """Best-effort XInput pad; server/UI still runs when the driver is absent."""

    def __init__(self) -> None:
        self.pad: Any | None = None
        self.vg: Any | None = None
        self.error: str | None = None
        self._pressed: set[str] = set()
        if os.name != "nt":
            self.error = "Virtual Xbox output is available on Windows only."
            return
        try:
            import vgamepad as vg

            self.vg = vg
            self.pad = vg.VX360Gamepad()
        except Exception as exc:  # missing ViGEmBus is a runtime, not import, error
            self.error = f"Virtual gamepad unavailable: {exc}"

    @property
    def ready(self) -> bool:
        return self.pad is not None

    def apply(self, state: dict[str, Any]) -> None:
        if not self.pad or not self.vg:
            return
        buttons = self.vg.XUSB_BUTTON
        names = {
            "A": "XUSB_GAMEPAD_A", "B": "XUSB_GAMEPAD_B",
            "X": "XUSB_GAMEPAD_X", "Y": "XUSB_GAMEPAD_Y",
            "LB": "XUSB_GAMEPAD_LEFT_SHOULDER", "RB": "XUSB_GAMEPAD_RIGHT_SHOULDER",
            "BACK": "XUSB_GAMEPAD_BACK", "START": "XUSB_GAMEPAD_START",
            "LS": "XUSB_GAMEPAD_LEFT_THUMB", "RS": "XUSB_GAMEPAD_RIGHT_THUMB",
            "UP": "XUSB_GAMEPAD_DPAD_UP", "DOWN": "XUSB_GAMEPAD_DPAD_DOWN",
            "LEFT": "XUSB_GAMEPAD_DPAD_LEFT", "RIGHT": "XUSB_GAMEPAD_DPAD_RIGHT",
            "GUIDE": "XUSB_GAMEPAD_GUIDE",
        }
        pressed = set(state["buttons"])
        for name in self._pressed - pressed:
            self.pad.release_button(button=getattr(buttons, names[name]))
        for name in pressed - self._pressed:
            if name in names:
                self.pad.press_button(button=getattr(buttons, names[name]))
        self._pressed = pressed
        axes = state["axes"]
        self.pad.left_joystick(
            x_value=_stick_value(axes["lx"]),
            y_value=_stick_value(axes["ly"]),
        )
        self.pad.right_joystick(
            x_value=_stick_value(axes["rx"]),
            y_value=_stick_value(axes["ry"]),
        )
        self.pad.left_trigger(value=state["lt"])
        self.pad.right_trigger(value=state["rt"])
        self.pad.update()

    def release_all(self) -> None:
        if not self.pad or not self.vg:
            return
        buttons = self.vg.XUSB_BUTTON
        names = {
            "A": "XUSB_GAMEPAD_A", "B": "XUSB_GAMEPAD_B",
            "X": "XUSB_GAMEPAD_X", "Y": "XUSB_GAMEPAD_Y",
            "LB": "XUSB_GAMEPAD_LEFT_SHOULDER", "RB": "XUSB_GAMEPAD_RIGHT_SHOULDER",
            "BACK": "XUSB_GAMEPAD_BACK", "START": "XUSB_GAMEPAD_START",
            "LS": "XUSB_GAMEPAD_LEFT_THUMB", "RS": "XUSB_GAMEPAD_RIGHT_THUMB",
            "UP": "XUSB_GAMEPAD_DPAD_UP", "DOWN": "XUSB_GAMEPAD_DPAD_DOWN",
            "LEFT": "XUSB_GAMEPAD_DPAD_LEFT", "RIGHT": "XUSB_GAMEPAD_DPAD_RIGHT",
            "GUIDE": "XUSB_GAMEPAD_GUIDE",
        }
        for name in self._pressed:
            self.pad.release_button(button=getattr(buttons, names[name]))
        self._pressed.clear()
        self.pad.left_joystick(x_value=0, y_value=0)
        self.pad.right_joystick(x_value=0, y_value=0)
        self.pad.left_trigger(value=0)
        self.pad.right_trigger(value=0)
        self.pad.update()
