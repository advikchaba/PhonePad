// Button ids used by the touch layout, the labels per controller type, and the
// bit each digital button sends.  LT / RT are analog triggers sent as 0 or 255.

import { BTN } from "./protocol";

export type PadKind = "xbox" | "ps";

export type ButtonId =
  | "A" | "B" | "X" | "Y"
  | "LB" | "RB" | "LT" | "RT"
  | "BACK" | "START" | "GUIDE"
  | "L3" | "R3" | "TOUCHPAD";

export const BUTTON_BITS: Partial<Record<ButtonId, number>> = {
  A: BTN.A,
  B: BTN.B,
  X: BTN.X,
  Y: BTN.Y,
  LB: BTN.LB,
  RB: BTN.RB,
  BACK: BTN.BACK,
  START: BTN.START,
  GUIDE: BTN.GUIDE,
  L3: BTN.L3,
  R3: BTN.R3,
  TOUCHPAD: BTN.TOUCHPAD,
};

export const LABELS: Record<PadKind, Record<ButtonId, string>> = {
  xbox: {
    A: "A", B: "B", X: "X", Y: "Y",
    LB: "LB", RB: "RB", LT: "LT", RT: "RT",
    BACK: "Back", START: "Start", GUIDE: "Xbox", L3: "L3", R3: "R3", TOUCHPAD: "",
  },
  ps: {
    A: "✕", B: "○", X: "□", Y: "△",
    LB: "L1", RB: "R1", LT: "L2", RT: "R2",
    BACK: "Share", START: "Options", GUIDE: "PS", L3: "L3", R3: "R3", TOUCHPAD: "Touchpad",
  },
};

export const KIND_NAMES: Record<PadKind, string> = {
  xbox: "Xbox 360",
  ps: "DualShock 4",
};
