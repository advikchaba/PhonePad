import { useEffect, useRef, useState } from "react";
import { InputController } from "../lib/inputController";
import { BUTTON_BITS, ButtonId, KIND_NAMES, LABELS, PadKind } from "../lib/layout";
import { NEUTRAL, PadState } from "../lib/protocol";
import type { LinkStatus, PadLink } from "../lib/padLink";

interface Props {
  kind: PadKind;
  link: PadLink;
  status: LinkStatus;
  onKind(kind: PadKind): void;
  onExit(): void;
}

const STICK_TRAVEL = 66; // knob travel in % of the knob's own size

export function Controller({ kind, link, status, onKind, onExit }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<InputController | null>(null);
  const [view, setView] = useState<PadState>(NEUTRAL);
  const [rtt, setRtt] = useState<number | null>(null);

  // Touch handling: every changed state goes to the socket immediately; the
  // screen is only re-rendered once per animation frame.
  useEffect(() => {
    const ic = new InputController();
    inputRef.current = ic;
    let frame = 0;
    let latest = NEUTRAL;
    ic.onChange((s) => {
      link.send(s);
      latest = s;
      if (!frame) {
        frame = requestAnimationFrame(() => {
          frame = 0;
          setView(latest);
        });
      }
    });
    if (rootRef.current) ic.attach(rootRef.current);
    return () => {
      ic.detach();
      if (frame) cancelAnimationFrame(frame);
      inputRef.current = null;
    };
  }, [link]);

  // Let go of everything while the connection is down.
  useEffect(() => {
    if (status !== "open") inputRef.current?.reset();
  }, [status]);

  useEffect(() => {
    const t = window.setInterval(() => setRtt(link.rtt), 500);
    return () => window.clearInterval(t);
  }, [link]);

  const labels = LABELS[kind];
  const on = (id: ButtonId): boolean => {
    if (id === "LT") return view.lt > 0;
    if (id === "RT") return view.rt > 0;
    const bit = BUTTON_BITS[id];
    return bit !== undefined && (view.buttons & bit) !== 0;
  };
  const btn = (id: ButtonId, extra = "") => (
    <div
      className={`btn ${extra} ${on(id) ? "on" : ""}`}
      data-btn={id}
      aria-label={id}
    >
      {labels[id]}
    </div>
  );

  const lx = view.lx / 32767;
  const ly = view.ly / 32767;
  const rx = view.rx / 32767;
  const ry = view.ry / 32767;
  const dpad = view.buttons;
  const latency = rtt === null ? "–" : `${rtt} ms`;

  return (
    <div className="pad" data-kind={kind} ref={rootRef}>
      {/* LEFT: triggers and bumpers stacked in the corner, stick and D-pad below */}
      <div className="zone zone-left">
        <div className="shoulders">
          {btn("LT", "trigger")}
          {btn("LB", "bumper")}
        </div>
        <div className="row row-left">
          <div className={`stick ${lx || ly ? "active" : ""}`} data-stick="L" aria-label="Left stick">
            <div
              className="knob"
              style={{ transform: `translate(${lx * STICK_TRAVEL}%, ${-ly * STICK_TRAVEL}%)` }}
            />
          </div>
          <div className="dpad" data-dpad aria-label="D-pad">
            <span className={`arm up ${dpad & 1 ? "on" : ""}`} />
            <span className={`arm down ${dpad & 2 ? "on" : ""}`} />
            <span className={`arm left ${dpad & 4 ? "on" : ""}`} />
            <span className={`arm right ${dpad & 8 ? "on" : ""}`} />
            <span className="hub" />
          </div>
        </div>
      </div>

      {/* CENTRE: status, system buttons */}
      <div className="center">
        <div className="topbar" data-ui>
          <span className={`dot ${status}`} />
          <span className="latency">
            {status === "open" ? latency : status === "connecting" ? "Connecting…" : "Reconnecting…"}
          </span>
          <div className="seg">
            {(["xbox", "ps"] as PadKind[]).map((k) => (
              <button
                key={k}
                data-ui
                className={k === kind ? "active" : ""}
                onClick={() => onKind(k)}
                title={KIND_NAMES[k]}
              >
                {k === "xbox" ? "Xbox" : "PS"}
              </button>
            ))}
          </div>
          <button data-ui className="exit" onClick={onExit}>
            Exit
          </button>
        </div>
        <div className="sys">
          {btn("BACK", "pill")}
          {btn("GUIDE", "guide")}
          {btn("START", "pill")}
        </div>
        <div className="sys sys-stick">
          {btn("L3", "pill")}
          {kind === "ps" ? btn("TOUCHPAD", "pill wide") : null}
          {btn("R3", "pill")}
        </div>
      </div>

      {/* RIGHT: triggers and bumpers, face buttons with the right stick */}
      <div className="zone zone-right">
        <div className="shoulders">
          {btn("RT", "trigger")}
          {btn("RB", "bumper")}
        </div>
        <div className="row row-right">
          <div className="face" aria-label="Face buttons">
            <span className="cell c-top">{btn("Y", "face face-Y")}</span>
            <span className="cell c-left">{btn("X", "face face-X")}</span>
            <span className="cell c-right">{btn("B", "face face-B")}</span>
            <span className="cell c-bottom">{btn("A", "face face-A")}</span>
          </div>
          <div className={`stick ${rx || ry ? "active" : ""}`} data-stick="R" aria-label="Right stick">
            <div
              className="knob"
              style={{ transform: `translate(${rx * STICK_TRAVEL}%, ${-ry * STICK_TRAVEL}%)` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
