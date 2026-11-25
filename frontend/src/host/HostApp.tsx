import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { BUTTON_BITS, ButtonId, KIND_NAMES, LABELS, PadKind } from "../lib/layout";
import { BTN, NEUTRAL, PadState } from "../lib/protocol";

interface PadInfo {
  kind: PadKind;
  simulated: boolean;
  error: string | null;
  driver_installed: boolean;
}

interface PhoneInfo {
  connected: boolean;
  ip: string | null;
  rtt: number | null;
  pps: number;
  since: number | null;
}

interface Snapshot {
  pad: PadInfo;
  phone: PhoneInfo;
  state: PadState;
}

interface Urls {
  host: string;
  phone: string;
  lan_ip: string;
  port: number;
}

const MIRROR_BUTTONS: ButtonId[] = ["LB", "RB", "LT", "RT", "Y", "X", "B", "A", "BACK", "GUIDE", "START", "L3", "R3"];

export function HostApp() {
  const [urls, setUrls] = useState<Urls | null>(null);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [live, setLive] = useState(false);
  const [qr, setQr] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  // Initial data + live updates over a WebSocket (reconnects by itself).
  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: number | undefined;
    let stopped = false;

    fetch("/api/status")
      .then((r) => r.json())
      .then((s) => {
        setUrls(s.urls);
        setSnap((prev) => prev ?? { pad: s.pad, phone: s.phone, state: NEUTRAL });
      })
      .catch(() => undefined);

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws/host`);
      ws.onopen = () => setLive(true);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "status") setSnap(msg);
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        setLive(false);
        if (!stopped) timer = window.setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
      ws?.close();
    };
  }, []);

  useEffect(() => {
    if (!urls) return;
    QRCode.toDataURL(urls.phone, { margin: 1, width: 280, errorCorrectionLevel: "M" })
      .then(setQr)
      .catch(() => setQr(""));
  }, [urls]);

  async function choose(kind: PadKind) {
    if (snap?.pad.kind === kind || busy) return;
    setBusy(true);
    try {
      await fetch("/api/pad", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind }),
      });
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!urls) return;
    try {
      await navigator.clipboard.writeText(urls.phone);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available */
    }
  }

  const pad = snap?.pad;
  const phone = snap?.phone;
  const kind: PadKind = pad?.kind ?? "xbox";
  const padName = KIND_NAMES[kind];

  return (
    <div className="host">
      <header className="host-head">
        <div className="brand">
          <span className="logo">🎮</span>
          <div>
            <h1>PhonePad</h1>
            <p>Your phone as a PC game controller</p>
          </div>
        </div>
        <div className="pills">
          {pad && (
            <span className={`pill ${pad.simulated ? "warn" : "good"}`}>
              {pad.simulated ? "Simulated – no virtual controller" : `Virtual ${padName} ready`}
            </span>
          )}
          <span className={`pill ${phone?.connected ? "good" : ""}`}>
            {phone?.connected
              ? `Phone connected${phone.rtt !== null ? ` · ${phone.rtt} ms` : ""}`
              : "Waiting for phone"}
          </span>
          {!live && <span className="pill warn">Dashboard offline – retrying</span>}
        </div>
      </header>

      {pad?.simulated && pad.error && (
        <div className="banner">
          <strong>No virtual controller:</strong> {pad.error}
          <br />
          Install the ViGEmBus driver on Windows (
          <a href="https://github.com/nefarius/ViGEmBus/releases" target="_blank" rel="noreferrer">
            github.com/nefarius/ViGEmBus
          </a>
          ), then restart PhonePad. Phone input is still received and shown below.
        </div>
      )}

      <main className="grid">
        <section className="card connect">
          <h2>1 · Connect your phone</h2>
          <div className="qr">{qr ? <img src={qr} alt="QR code for the phone controller" /> : <div className="qr-empty" />}</div>
          <div className="addr">
            <code>{urls?.phone ?? "…"}</code>
            <button className="ghost" onClick={copy} disabled={!urls}>
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <ol className="steps">
            <li>Put the phone and this PC on the <b>same WiFi</b>.</li>
            <li>Scan the QR code with the phone camera (or type the address).</li>
            <li>Choose a controller type and tap <b>Start controller</b>.</li>
          </ol>
        </section>

        <section className="card">
          <h2>2 · Controller type</h2>
          <div className="kind-buttons">
            {(["xbox", "ps"] as PadKind[]).map((k) => (
              <button
                key={k}
                className={`kind ${kind === k ? "active" : ""}`}
                onClick={() => choose(k)}
                disabled={busy}
              >
                <strong>{KIND_NAMES[k]}</strong>
                <span>{k === "xbox" ? "XInput · A B X Y" : "DualShock 4 · ✕ ○ □ △"}</span>
              </button>
            ))}
          </div>
          <p className="muted">
            Most PC games only read Xbox controllers, so use <b>Xbox 360</b> unless a game or emulator asks for
            PlayStation. You can also switch from the phone; the change applies immediately.
          </p>
        </section>

        <section className="card">
          <h2>3 · Check it works</h2>
          <ol className="steps">
            <li>
              Press <kbd>Win</kbd> + <kbd>R</kbd>, type <code>joy.cpl</code>, press Enter.
            </li>
            <li>
              You should see <b>{kind === "xbox" ? "Xbox 360 Controller for Windows" : "Wireless Controller"}</b>.
            </li>
            <li>Move the sticks on the phone. The test window should react.</li>
          </ol>
          <dl className="stats">
            <dt>Packets / s</dt>
            <dd>{phone?.connected ? phone.pps : "–"}</dd>
            <dt>Phone address</dt>
            <dd>{phone?.connected && phone.ip ? phone.ip : "–"}</dd>
            <dt>Round trip</dt>
            <dd>{phone?.connected && phone.rtt !== null ? `${phone.rtt} ms` : "–"}</dd>
          </dl>
        </section>

        <section className="card mirror-card">
          <h2>Live input</h2>
          <Mirror kind={kind} state={snap?.state ?? NEUTRAL} />
        </section>
      </main>
      <footer className="foot">Local network only. Nothing leaves your WiFi.</footer>
    </div>
  );
}

function Mirror({ kind, state }: { kind: PadKind; state: PadState }) {
  const pressed = (id: ButtonId) => {
    if (id === "LT") return state.lt > 0;
    if (id === "RT") return state.rt > 0;
    const bit = BUTTON_BITS[id];
    return bit !== undefined && (state.buttons & bit) !== 0;
  };
  const dpad = state.buttons;
  return (
    <div className="mirror">
      <div className="sticks">
        <Stick label="L" x={state.lx} y={state.ly} />
        <div className="dpad-mini">
          <span className={dpad & BTN.DPAD_UP ? "on" : ""} />
          <span className={dpad & BTN.DPAD_LEFT ? "on" : ""} />
          <span className={dpad & BTN.DPAD_RIGHT ? "on" : ""} />
          <span className={dpad & BTN.DPAD_DOWN ? "on" : ""} />
        </div>
        <Stick label="R" x={state.rx} y={state.ry} />
      </div>
      <div className="chips">
        {MIRROR_BUTTONS.map((id) => (
          <span key={id} className={`chip ${pressed(id) ? "on" : ""}`}>
            {LABELS[kind][id] || id}
          </span>
        ))}
      </div>
      <div className="triggers">
        <Bar label="LT" value={state.lt} />
        <Bar label="RT" value={state.rt} />
      </div>
    </div>
  );
}

function Stick({ label, x, y }: { label: string; x: number; y: number }) {
  const px = 50 + (x / 32767) * 42;
  const py = 50 - (y / 32767) * 42;
  return (
    <div className="stick-mini">
      <div className="ring">
        <div className="dot" style={{ left: `${px}%`, top: `${py}%` }} />
      </div>
      <span>{label}</span>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="bar">
      <span>{label}</span>
      <div>
        <i style={{ width: `${(value / 255) * 100}%` }} />
      </div>
    </div>
  );
}
