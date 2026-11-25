"""Translate the PhonePad button bits into the two virtual pad families.

Pure Python on purpose: no ViGEm dependency, so it can be unit-tested on any OS.

Xbox 360 (XINPUT_GAMEPAD)
    Our bits 0-10 are already the XINPUT bits, so the mask is copied across
    and the one non-XINPUT bit (TOUCHPAD, bit 11) is cleared.

DualShock 4
    Face buttons are relabelled (A=Cross, B=Circle, X=Square, Y=Triangle),
    the shoulder and stick clicks are renamed, and the PS and touchpad
    buttons live in the "special" byte.  The D-pad is a single 4-bit hat.
"""

from __future__ import annotations

from .protocol import Btn, PadState

# ---------------------------------------------------------------- Xbox 360
XUSB_CLEAR_MASK = 0xFFFF & ~int(Btn.TOUCHPAD)


def xbox_buttons(buttons: int) -> int:
    return buttons & XUSB_CLEAR_MASK


# ------------------------------------------------------------ DualShock 4
# DS4 wButtons bits (see DS4_BUTTONS in vgamepad)
DS4_SQUARE = 1 << 4
DS4_CROSS = 1 << 5
DS4_CIRCLE = 1 << 6
DS4_TRIANGLE = 1 << 7
DS4_SHOULDER_L1 = 1 << 8
DS4_SHOULDER_R1 = 1 << 9
DS4_SHARE = 1 << 12
DS4_OPTIONS = 1 << 13
DS4_THUMB_L3 = 1 << 14
DS4_THUMB_R3 = 1 << 15

# bSpecial bits (DS4_SPECIAL_BUTTONS)
DS4_SPECIAL_PS = 1 << 0
DS4_SPECIAL_TOUCHPAD = 1 << 1

_DS4_BUTTON_MAP = (
    (Btn.A, DS4_CROSS),
    (Btn.B, DS4_CIRCLE),
    (Btn.X, DS4_SQUARE),
    (Btn.Y, DS4_TRIANGLE),
    (Btn.LB, DS4_SHOULDER_L1),
    (Btn.RB, DS4_SHOULDER_R1),
    (Btn.BACK, DS4_SHARE),
    (Btn.START, DS4_OPTIONS),
    (Btn.L3, DS4_THUMB_L3),
    (Btn.R3, DS4_THUMB_R3),
)

# D-pad hat values (DS4_DPAD_DIRECTIONS): 0 = N, clockwise, 8 = released.
DPAD_NONE = 8
_HAT = {
    (True, False, False, False): 0,  # up
    (True, False, False, True): 1,  # up-right
    (False, False, False, True): 2,  # right
    (False, True, False, True): 3,  # down-right
    (False, True, False, False): 4,  # down
    (False, True, True, False): 5,  # down-left
    (False, False, True, False): 6,  # left
    (True, False, True, False): 7,  # up-left
}


def dpad_hat(buttons: int) -> int:
    up = bool(buttons & Btn.DPAD_UP)
    down = bool(buttons & Btn.DPAD_DOWN)
    left = bool(buttons & Btn.DPAD_LEFT)
    right = bool(buttons & Btn.DPAD_RIGHT)
    if (up and down) or (left and right):
        return DPAD_NONE  # opposite directions cancel out
    return _HAT.get((up, down, left, right), DPAD_NONE)


def ds4_buttons(buttons: int) -> int:
    out = 0
    for bit, ds4 in _DS4_BUTTON_MAP:
        if buttons & bit:
            out |= ds4
    return out


def ds4_special(buttons: int) -> int:
    out = 0
    if buttons & Btn.GUIDE:
        out |= DS4_SPECIAL_PS
    if buttons & Btn.TOUCHPAD:
        out |= DS4_SPECIAL_TOUCHPAD
    return out


def axis_to_u8(value: int, invert: bool = False) -> int:
    """Map signed 16-bit (-32768..32767) to DS4's unsigned 0..255 (128 = centre)."""
    v = 128 + (value >> 8)
    if invert:
        v = 128 - (value >> 8)
    return max(0, min(255, v))


def ds4_axes(state: PadState) -> tuple[int, int, int, int]:
    """DS4 HID stick bytes.  Y is inverted: 0 = up on the DS4 report."""
    return (
        axis_to_u8(state.lx),
        axis_to_u8(state.ly, invert=True),
        axis_to_u8(state.rx),
        axis_to_u8(state.ry, invert=True),
    )


def ds4_triggers(state: PadState) -> tuple[int, int]:
    return max(0, min(255, state.lt)), max(0, min(255, state.rt))

# Digital trigger bits that ViGEm's DS4 report expects next to the analog L2/R2.
DS4_TRIGGER_L2 = 1 << 10
DS4_TRIGGER_R2 = 1 << 11


def ds4_wbuttons(state: PadState) -> int:
    """Full DS4 ``wButtons`` word: digital buttons, L2/R2 digital bits, D-pad hat."""
    lt, rt = ds4_triggers(state)
    word = ds4_buttons(state.buttons) | dpad_hat(state.buttons)
    if lt > 0:
        word |= DS4_TRIGGER_L2
    if rt > 0:
        word |= DS4_TRIGGER_R2
    return word
