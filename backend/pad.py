"""Virtual gamepad engines.

On Windows the ``vgamepad`` package talks to the ViGEmBus driver, which creates
a real XInput (Xbox 360) or DirectInput/HID (DualShock 4) device that every
game sees.  Anywhere else - or when the driver is missing - PhonePad falls back
to a simulated pad, so the server still runs and the dashboard still works.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Callable

from . import mapping
from .protocol import NEUTRAL, PadState

log = logging.getLogger("phonepad.pad")

KINDS = ("xbox", "ps")
RumbleCallback = Callable[[int, int], None]


def driver_installed() -> bool:
    """True when the ViGEmBus driver service is registered (Windows only)."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\ViGEmBus",
        ):
            return True
    except OSError:
        return False


class XboxEngine:
    """Xbox 360 pad (XInput).  Games see 'Xbox 360 Controller for Windows'."""

    kind = "xbox"

    def __init__(self, on_rumble: RumbleCallback) -> None:
        import vgamepad as vg

        self._pad = vg.VX360Gamepad()
        self._on_rumble = on_rumble
        self._pad.register_notification(self._notify)
        self._pad.reset()
        self._pad.update()

    def _notify(self, client, target, large, small, led, user) -> None:  # ViGEm thread
        self._on_rumble(int(large), int(small))

    def apply(self, s: PadState) -> None:
        r = self._pad.report
        r.wButtons = mapping.xbox_buttons(s.buttons)
        r.sThumbLX = s.lx
        r.sThumbLY = s.ly
        r.sThumbRX = s.rx
        r.sThumbRY = s.ry
        r.bLeftTrigger = s.lt
        r.bRightTrigger = s.rt
        self._pad.update()

    def close(self) -> None:
        try:
            self._pad.unregister_notification()
        except Exception:
            pass
        self._pad = None


class Ds4Engine:
    """DualShock 4 pad.  Games see 'Wireless Controller'."""

    kind = "ps"

    def __init__(self, on_rumble: RumbleCallback) -> None:
        import vgamepad as vg

        self._pad = vg.VDS4Gamepad()
        self._on_rumble = on_rumble
        self._pad.register_notification(self._notify)
        self._pad.reset()
        self._pad.update()

    def _notify(self, client, target, large, small, lightbar, user) -> None:  # ViGEm thread
        self._on_rumble(int(large), int(small))

    def apply(self, s: PadState) -> None:
        r = self._pad.report
        r.bThumbLX, r.bThumbLY, r.bThumbRX, r.bThumbRY = mapping.ds4_axes(s)
        r.wButtons = mapping.ds4_wbuttons(s)
        r.bSpecial = mapping.ds4_special(s.buttons)
        r.bTriggerL, r.bTriggerR = mapping.ds4_triggers(s)
        self._pad.update()

    def close(self) -> None:
        try:
            self._pad.unregister_notification()
        except Exception:
            pass
        self._pad = None


class SimulatedEngine:
    """Stand-in used when no virtual device can be created."""

    def __init__(self, kind: str) -> None:
        self.kind = kind

    def apply(self, s: PadState) -> None:
        pass

    def close(self) -> None:
        pass


def _describe(exc: BaseException) -> str:
    if isinstance(exc, ImportError):
        return "The vgamepad package is not installed on this system."
    if isinstance(exc, OSError):
        return (
            "Could not create the virtual controller. Check that the ViGEmBus "
            f"driver is installed and running ({exc})."
        )
    return f"Could not create the virtual controller: {type(exc).__name__}: {exc}"


class PadManager:
    """Owns the one virtual pad and can hot-swap between Xbox and PS."""

    def __init__(self, on_rumble: RumbleCallback, kind: str = "xbox") -> None:
        self._on_rumble = on_rumble
        self._lock = threading.Lock()
        self._engine = None
        self._kind = "xbox"
        self.simulated = False
        self.error: str | None = None
        self.last_state: PadState = NEUTRAL
        self._open(kind if kind in KINDS else "xbox")

    @property
    def kind(self) -> str:
        return self._kind

    def _open(self, kind: str) -> None:
        try:
            if kind == "xbox":
                engine = XboxEngine(self._on_rumble)
            else:
                engine = Ds4Engine(self._on_rumble)
            self.simulated = False
            self.error = None
        except Exception as exc:  # no vgamepad, no driver, wrong OS, ...
            log.warning("Virtual pad unavailable, running simulated: %s", exc)
            engine = SimulatedEngine(kind)
            self.simulated = True
            self.error = _describe(exc)
        self._engine = engine
        self._kind = kind
        self.last_state = NEUTRAL

    def switch(self, kind: str) -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown pad type: {kind}")
        with self._lock:
            if self._engine is not None:
                self._engine.close()
            self._open(kind)

    def apply(self, state: PadState) -> None:
        if state == self.last_state:
            return  # nothing changed - don't spam the driver
        with self._lock:
            self.last_state = state
            try:
                self._engine.apply(state)
            except Exception as exc:
                log.error("Failed to update virtual pad: %s", exc)
                self.error = _describe(exc)

    def reset(self) -> None:
        """Release everything (used when the phone disconnects or goes silent)."""
        self.apply(NEUTRAL)

    def status(self) -> dict:
        return {
            "kind": self._kind,
            "simulated": self.simulated,
            "error": self.error,
            "driver_installed": driver_installed(),
        }

    def close(self) -> None:
        with self._lock:
            if self._engine is not None:
                self._engine.close()
                self._engine = None
