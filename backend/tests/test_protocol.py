import struct
import unittest

from backend import mapping
from backend.protocol import (
    INPUT_SIZE,
    MSG_INPUT,
    NEUTRAL,
    Btn,
    PadState,
    encode_input,
    encode_rumble,
    parse_input,
)


class ProtocolTests(unittest.TestCase):
    def test_input_packet_is_13_bytes(self):
        self.assertEqual(INPUT_SIZE, 13)

    def test_round_trip(self):
        s = PadState(int(Btn.A | Btn.LB | Btn.DPAD_UP), -32768, 32767, -1, 1, 0, 255)
        self.assertEqual(parse_input(encode_input(s)), s)

    def test_encode_clamps_out_of_range(self):
        s = PadState(lx=99999, ly=-99999, lt=300, rt=-4)
        out = parse_input(encode_input(s))
        self.assertEqual((out.lx, out.ly, out.lt, out.rt), (32767, -32768, 255, 0))

    def test_malformed_packets_rejected(self):
        self.assertIsNone(parse_input(b""))
        self.assertIsNone(parse_input(b"\x01" * 5))
        good = encode_input(NEUTRAL)
        self.assertIsNone(parse_input(bytes([MSG_INPUT + 1]) + good[1:]))

    def test_rumble_packet(self):
        self.assertEqual(encode_rumble(300, 7), struct.pack("!BBB", 3, 255, 7))

    def test_button_bits_match_xinput_layout(self):
        # Bits 0-10 must line up with XINPUT_GAMEPAD so the Xbox pad copies them.
        self.assertEqual(int(Btn.DPAD_UP), 0x0001)
        self.assertEqual(int(Btn.GUIDE), 0x0400)
        self.assertEqual(int(Btn.A), 0x1000)
        self.assertEqual(int(Btn.Y), 0x8000)


class MappingTests(unittest.TestCase):
    def test_xbox_clears_touchpad_bit_only(self):
        all_bits = 0xFFFF
        self.assertEqual(mapping.xbox_buttons(all_bits), 0xFFFF & ~0x0800)
        self.assertEqual(mapping.xbox_buttons(int(Btn.A)), 0x1000)

    def test_ds4_face_buttons(self):
        self.assertEqual(mapping.ds4_buttons(int(Btn.A)), mapping.DS4_CROSS)
        self.assertEqual(mapping.ds4_buttons(int(Btn.B)), mapping.DS4_CIRCLE)
        self.assertEqual(mapping.ds4_buttons(int(Btn.X)), mapping.DS4_SQUARE)
        self.assertEqual(mapping.ds4_buttons(int(Btn.Y)), mapping.DS4_TRIANGLE)

    def test_ds4_shoulders_sticks_and_specials(self):
        word = mapping.ds4_buttons(int(Btn.LB | Btn.RB | Btn.BACK | Btn.START | Btn.L3 | Btn.R3))
        self.assertEqual(word, 0x0100 | 0x0200 | 0x1000 | 0x2000 | 0x4000 | 0x8000)
        self.assertEqual(mapping.ds4_special(int(Btn.GUIDE)), mapping.DS4_SPECIAL_PS)
        self.assertEqual(mapping.ds4_special(int(Btn.TOUCHPAD)), mapping.DS4_SPECIAL_TOUCHPAD)

    def test_dpad_hat_directions(self):
        up, down, left, right = (int(Btn.DPAD_UP), int(Btn.DPAD_DOWN),
                                 int(Btn.DPAD_LEFT), int(Btn.DPAD_RIGHT))
        self.assertEqual(mapping.dpad_hat(0), mapping.DPAD_NONE)
        self.assertEqual(mapping.dpad_hat(up), 0)
        self.assertEqual(mapping.dpad_hat(up | right), 1)
        self.assertEqual(mapping.dpad_hat(right), 2)
        self.assertEqual(mapping.dpad_hat(down | right), 3)
        self.assertEqual(mapping.dpad_hat(down), 4)
        self.assertEqual(mapping.dpad_hat(down | left), 5)
        self.assertEqual(mapping.dpad_hat(left), 6)
        self.assertEqual(mapping.dpad_hat(up | left), 7)
        self.assertEqual(mapping.dpad_hat(up | down), mapping.DPAD_NONE)
        self.assertEqual(mapping.dpad_hat(left | right), mapping.DPAD_NONE)

    def test_ds4_stick_axes(self):
        self.assertEqual(mapping.axis_to_u8(0), 128)
        self.assertEqual(mapping.axis_to_u8(-32768), 0)
        self.assertEqual(mapping.axis_to_u8(32767), 255)
        # Y is inverted on DS4: pushing up (+Y) gives a low byte.
        up = mapping.ds4_axes(PadState(ly=32767))
        self.assertLess(up[1], 128)
        down = mapping.ds4_axes(PadState(ly=-32768))
        self.assertGreater(down[1], 128)

    def test_ds4_trigger_digital_bits(self):
        word = mapping.ds4_wbuttons(PadState(lt=255, rt=0))
        self.assertTrue(word & mapping.DS4_TRIGGER_L2)
        self.assertFalse(word & mapping.DS4_TRIGGER_R2)


if __name__ == "__main__":
    unittest.main()
