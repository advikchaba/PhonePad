"""Binary wire protocol between the phone and the PC.

Every message starts with a one-byte type.  Input is sent as a full state
snapshot each time something changes, so a dropped or coalesced packet never
leaves the pad in a wrong state.  All integers are big-endian.

Phone -> PC
    1  INPUT  ``!BHhhhhBB``  type, buttons, LX, LY, RX, RY, LT, RT   (13 bytes)
    2  PING   ``!Bd``        type, client timestamp in ms            (9 bytes)
    text     JSON control messages (``pad``, ``stats``)

PC -> phone
    2  PONG   the PING packet echoed back unchanged
    3  RUMBLE ``!BBB``       type, large motor, small motor (0..255)
    text     JSON status messages (``hello``)

Stick axes are signed 16-bit with +Y meaning *up* (the XInput convention).
Triggers are 0..255.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntFlag

MSG_INPUT = 1
MSG_PING = 2
MSG_RUMBLE = 3

INPUT_FMT = "!BHhhhhBB"
INPUT_SIZE = struct.calcsize(INPUT_FMT)  # 13
PING_FMT = "!Bd"
PING_SIZE = struct.calcsize(PING_FMT)  # 9
RUMBLE_FMT = "!BBB"


class Btn(IntFlag):
    """Digital button bits.  Bits 0-10 match the XINPUT_GAMEPAD layout."""

    DPAD_UP = 1 << 0
    DPAD_DOWN = 1 << 1
    DPAD_LEFT = 1 << 2
    DPAD_RIGHT = 1 << 3
    START = 1 << 4
    BACK = 1 << 5
    L3 = 1 << 6
    R3 = 1 << 7
    LB = 1 << 8
    RB = 1 << 9
    GUIDE = 1 << 10  # Xbox button / PS button
    TOUCHPAD = 1 << 11  # PlayStation touchpad click (ignored in Xbox mode)
    A = 1 << 12  # Xbox A  / PS Cross
    B = 1 << 13  # Xbox B  / PS Circle
    X = 1 << 14  # Xbox X  / PS Square
    Y = 1 << 15  # Xbox Y  / PS Triangle


@dataclass(frozen=True)
class PadState:
    """One complete snapshot of the virtual gamepad."""

    buttons: int = 0
    lx: int = 0
    ly: int = 0
    rx: int = 0
    ry: int = 0
    lt: int = 0
    rt: int = 0

    def is_neutral(self) -> bool:
        return self == NEUTRAL


NEUTRAL = PadState()


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def parse_input(data: bytes) -> PadState | None:
    """Decode an INPUT packet.  Returns ``None`` for anything malformed."""
    if len(data) != INPUT_SIZE or data[0] != MSG_INPUT:
        return None
    _, buttons, lx, ly, rx, ry, lt, rt = struct.unpack(INPUT_FMT, data)
    return PadState(buttons, lx, ly, rx, ry, lt, rt)


def encode_input(state: PadState) -> bytes:
    """Encode a PadState as an INPUT packet (used by tests and tools)."""
    return struct.pack(
        INPUT_FMT,
        MSG_INPUT,
        state.buttons & 0xFFFF,
        _clamp(state.lx, -32768, 32767),
        _clamp(state.ly, -32768, 32767),
        _clamp(state.rx, -32768, 32767),
        _clamp(state.ry, -32768, 32767),
        _clamp(state.lt, 0, 255),
        _clamp(state.rt, 0, 255),
    )


def encode_rumble(large: int, small: int) -> bytes:
    return struct.pack(RUMBLE_FMT, MSG_RUMBLE, _clamp(large, 0, 255), _clamp(small, 0, 255))
