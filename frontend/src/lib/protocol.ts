// Binary wire protocol - mirrors backend/protocol.py.  Keep the two in sync.

export const MSG = { INPUT: 1, PING: 2, RUMBLE: 3 } as const;

// Digital button bits (same layout as the Btn enum in the backend).
export const BTN = {
  DPAD_UP: 1 << 0,
  DPAD_DOWN: 1 << 1,
  DPAD_LEFT: 1 << 2,
  DPAD_RIGHT: 1 << 3,
  START: 1 << 4,
  BACK: 1 << 5,
  L3: 1 << 6,
  R3: 1 << 7,
  LB: 1 << 8,
  RB: 1 << 9,
  GUIDE: 1 << 10,
  TOUCHPAD: 1 << 11,
  A: 1 << 12,
  B: 1 << 13,
  X: 1 << 14,
  Y: 1 << 15,
} as const;

export interface PadState {
  buttons: number;
  lx: number; // -32768..32767, +Y is up
  ly: number;
  rx: number;
  ry: number;
  lt: number; // 0..255
  rt: number;
}

export const NEUTRAL: PadState = { buttons: 0, lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0 };

export function sameState(a: PadState, b: PadState): boolean {
  return (
    a.buttons === b.buttons &&
    a.lx === b.lx &&
    a.ly === b.ly &&
    a.rx === b.rx &&
    a.ry === b.ry &&
    a.lt === b.lt &&
    a.rt === b.rt
  );
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, Math.round(v)));

/** 13-byte INPUT packet: type, buttons, LX, LY, RX, RY, LT, RT. */
export function encodeInput(s: PadState): ArrayBuffer {
  const buf = new ArrayBuffer(13);
  const v = new DataView(buf);
  v.setUint8(0, MSG.INPUT);
  v.setUint16(1, s.buttons & 0xffff, false);
  v.setInt16(3, clamp(s.lx, -32768, 32767), false);
  v.setInt16(5, clamp(s.ly, -32768, 32767), false);
  v.setInt16(7, clamp(s.rx, -32768, 32767), false);
  v.setInt16(9, clamp(s.ry, -32768, 32767), false);
  v.setUint8(11, clamp(s.lt, 0, 255));
  v.setUint8(12, clamp(s.rt, 0, 255));
  return buf;
}

/** 9-byte PING packet carrying the client timestamp in ms. */
export function encodePing(nowMs: number): ArrayBuffer {
  const buf = new ArrayBuffer(9);
  const v = new DataView(buf);
  v.setUint8(0, MSG.PING);
  v.setFloat64(1, nowMs, false);
  return buf;
}

/** Reads the timestamp back out of a PONG. Returns null when malformed. */
export function decodePong(buf: ArrayBuffer): number | null {
  if (buf.byteLength !== 9 || new DataView(buf).getUint8(0) !== MSG.PING) return null;
  return new DataView(buf).getFloat64(1, false);
}

export function decodeRumble(buf: ArrayBuffer): { large: number; small: number } | null {
  if (buf.byteLength !== 3 || new DataView(buf).getUint8(0) !== MSG.RUMBLE) return null;
  const v = new DataView(buf);
  return { large: v.getUint8(1), small: v.getUint8(2) };
}
