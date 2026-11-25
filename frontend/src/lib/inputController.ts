// Turns raw pointer events into a PadState.
//
// Every finger (pointer) is tracked on its own, so multi-touch works: a stick
// and several buttons can be held at once.  A finger that slides from one
// button to another releases the first and presses the second.  Buttons are
// OR-ed together, so two fingers on the same button keep it pressed until both
// lift.

import { BTN, NEUTRAL, PadState, sameState } from "./protocol";
import { BUTTON_BITS, ButtonId } from "./layout";

type Held =
  | { kind: "btn"; id: ButtonId | null }
  | { kind: "stick"; stick: "L" | "R"; x: number; y: number; cx: number; cy: number; r: number }
  | { kind: "dpad"; bits: number; cx: number; cy: number; r: number };

const STICK_DEAD = 0.1; // fraction of the radius ignored around the centre
const DPAD_DEAD = 0.18;
const DPAD_EDGE = 0.38; // cos(67.5deg): where a direction counts as "held"

const TARGET_SELECTOR = "[data-btn],[data-stick],[data-dpad]";

export class InputController {
  private held = new Map<number, Held>();
  private state: PadState = NEUTRAL;
  private listener: ((s: PadState) => void) | null = null;
  private root: HTMLElement | null = null;

  private onDown = (e: PointerEvent) => this.pointerDown(e);
  private onMove = (e: PointerEvent) => this.pointerMove(e);
  private onUp = (e: PointerEvent) => this.pointerUp(e);
  private onContext = (e: Event) => e.preventDefault();
  private onBlur = () => this.reset();
  private onVisibility = () => {
    if (document.visibilityState !== "visible") this.reset();
  };

  onChange(fn: (s: PadState) => void): void {
    this.listener = fn;
  }

  get current(): PadState {
    return this.state;
  }

  attach(root: HTMLElement): void {
    this.detach();
    this.root = root;
    root.addEventListener("pointerdown", this.onDown);
    root.addEventListener("pointermove", this.onMove);
    root.addEventListener("pointerup", this.onUp);
    root.addEventListener("pointercancel", this.onUp);
    root.addEventListener("lostpointercapture", this.onUp);
    root.addEventListener("contextmenu", this.onContext);
    window.addEventListener("blur", this.onBlur);
    document.addEventListener("visibilitychange", this.onVisibility);
  }

  detach(): void {
    const root = this.root;
    if (root) {
      root.removeEventListener("pointerdown", this.onDown);
      root.removeEventListener("pointermove", this.onMove);
      root.removeEventListener("pointerup", this.onUp);
      root.removeEventListener("pointercancel", this.onUp);
      root.removeEventListener("lostpointercapture", this.onUp);
      root.removeEventListener("contextmenu", this.onContext);
    }
    window.removeEventListener("blur", this.onBlur);
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.root = null;
    this.reset();
  }

  /** Release everything (e.g. the app lost focus). */
  reset(): void {
    if (this.held.size === 0 && sameState(this.state, NEUTRAL)) return;
    this.held.clear();
    this.recompute();
  }

  // ------------------------------------------------------------ pointers
  private hitTarget(x: number, y: number): Element | null {
    const el = document.elementFromPoint(x, y);
    return el ? el.closest(TARGET_SELECTOR) : null;
  }

  private pointerDown(e: PointerEvent): void {
    const target = e.target instanceof Element ? e.target : null;
    if (target?.closest("[data-ui]")) return; // toolbar buttons handle their own clicks
    const el = this.hitTarget(e.clientX, e.clientY);
    if (!el) return;
    e.preventDefault();

    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const r = rect.width / 2;

    if (el.hasAttribute("data-stick")) {
      const stick = el.getAttribute("data-stick") === "R" ? "R" : "L";
      // One finger per stick: a second finger on it is ignored.
      for (const h of this.held.values()) {
        if (h.kind === "stick" && h.stick === stick) return;
      }
      const h: Held = { kind: "stick", stick, x: 0, y: 0, cx, cy, r };
      this.held.set(e.pointerId, h);
      this.moveStick(h, e.clientX, e.clientY);
    } else if (el.hasAttribute("data-dpad")) {
      const h: Held = { kind: "dpad", bits: 0, cx, cy, r };
      this.held.set(e.pointerId, h);
      this.moveDpad(h, e.clientX, e.clientY);
    } else {
      const id = (el.getAttribute("data-btn") as ButtonId | null) ?? null;
      this.held.set(e.pointerId, { kind: "btn", id });
    }
    try {
      (e.target as Element).setPointerCapture?.(e.pointerId);
    } catch {
      /* not all targets support capture; movement still reaches the root */
    }
    this.recompute();
  }

  private pointerMove(e: PointerEvent): void {
    const h = this.held.get(e.pointerId);
    if (!h) return;
    if (h.kind === "stick") {
      this.moveStick(h, e.clientX, e.clientY);
    } else if (h.kind === "dpad") {
      this.moveDpad(h, e.clientX, e.clientY);
    } else {
      // Slide: follow the finger onto whichever button is now underneath it.
      const el = this.hitTarget(e.clientX, e.clientY);
      const id = el && el.hasAttribute("data-btn") ? (el.getAttribute("data-btn") as ButtonId) : null;
      if (id === h.id) return;
      h.id = id;
    }
    this.recompute();
  }

  private pointerUp(e: PointerEvent): void {
    if (!this.held.delete(e.pointerId)) return;
    this.recompute();
  }

  // ---------------------------------------------------------- analog math
  private moveStick(h: Extract<Held, { kind: "stick" }>, px: number, py: number): void {
    let dx = (px - h.cx) / h.r;
    let dy = -(py - h.cy) / h.r; // screen Y grows downwards; the pad's Y grows upwards
    let mag = Math.hypot(dx, dy);
    if (mag > 1) {
      dx /= mag;
      dy /= mag;
      mag = 1;
    }
    if (mag < STICK_DEAD) {
      h.x = 0;
      h.y = 0;
      return;
    }
    const scale = (mag - STICK_DEAD) / (1 - STICK_DEAD) / mag;
    h.x = Math.round(dx * scale * 32767);
    h.y = Math.round(dy * scale * 32767);
  }

  private moveDpad(h: Extract<Held, { kind: "dpad" }>, px: number, py: number): void {
    const dx = (px - h.cx) / h.r;
    const dy = -(py - h.cy) / h.r;
    const mag = Math.hypot(dx, dy);
    let bits = 0;
    if (mag >= DPAD_DEAD) {
      const sx = dx / mag;
      const sy = dy / mag;
      if (sy > DPAD_EDGE) bits |= BTN.DPAD_UP;
      if (sy < -DPAD_EDGE) bits |= BTN.DPAD_DOWN;
      if (sx < -DPAD_EDGE) bits |= BTN.DPAD_LEFT;
      if (sx > DPAD_EDGE) bits |= BTN.DPAD_RIGHT;
    }
    h.bits = bits;
  }

  // ---------------------------------------------------------- state
  private recompute(): void {
    let buttons = 0;
    let lt = 0;
    let rt = 0;
    let lx = 0;
    let ly = 0;
    let rx = 0;
    let ry = 0;
    for (const h of this.held.values()) {
      if (h.kind === "btn") {
        if (h.id === "LT") lt = 255;
        else if (h.id === "RT") rt = 255;
        else if (h.id) buttons |= BUTTON_BITS[h.id] ?? 0;
      } else if (h.kind === "dpad") {
        buttons |= h.bits;
      } else if (h.stick === "L") {
        lx = h.x;
        ly = h.y;
      } else {
        rx = h.x;
        ry = h.y;
      }
    }
    const next: PadState = { buttons, lx, ly, rx, ry, lt, rt };
    if (sameState(next, this.state)) return;
    this.state = next;
    this.listener?.(next);
  }
}
