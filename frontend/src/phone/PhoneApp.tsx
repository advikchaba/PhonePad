import { useEffect, useMemo, useRef, useState } from "react";
import { Controller } from "./Controller";
import { HelloInfo, LinkStatus, PadLink, phoneSocketUrl } from "../lib/padLink";
import { KIND_NAMES, PadKind } from "../lib/layout";

const KIND_KEY = "phonepad.kind";

function savedKind(): PadKind {
  try {
    return localStorage.getItem(KIND_KEY) === "ps" ? "ps" : "xbox";
  } catch {
    return "xbox";
  }
}

function vibrate(large: number, small: number): void {
  const strength = Math.max(large, small);
  if (!navigator.vibrate) return;
  // The Vibration API has no strength control, so map the rumble to a duration.
  navigator.vibrate(strength > 0 ? 30 + Math.round((strength / 255) * 90) : 0);
}

export function PhoneApp() {
  const [status, setStatus] = useState<LinkStatus>("connecting");
  const [kind, setKind] = useState<PadKind>(savedKind);
  const [hello, setHello] = useState<HelloInfo | null>(null);
  const [playing, setPlaying] = useState(false);
  const kindRef = useRef(kind);
  const needPref = useRef(true);
  const wakeLock = useRef<WakeLockSentinel | null>(null);

  const link = useMemo<PadLink>(
    () =>
      new PadLink(phoneSocketUrl(), {
        onStatus: setStatus,
        onOpen: () => {
          needPref.current = true;
        },
        onHello: (h) => {
          setHello(h);
          if (needPref.current) {
            // First hello of a connection: apply the phone's saved choice.
            needPref.current = false;
            if (h.pad.kind !== kindRef.current) {
              link.setPad(kindRef.current);
            }
          } else if (h.pad.kind !== kindRef.current) {
            // Changed from the dashboard: follow the PC.
            kindRef.current = h.pad.kind;
            setKind(h.pad.kind);
          }
        },
        onRumble: vibrate,
      }),
    [],
  );

  useEffect(() => {
    link.start();
    return () => link.stop();
  }, [link]);

  // Browsers drop the wake lock and freeze timers when the page is hidden:
  // reconnect as soon as the page is visible again.
  const playingRef = useRef(playing);
  playingRef.current = playing;
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      link.wake();
      if (playingRef.current) void requestWakeLock(wakeLock);
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [link]);

  function chooseKind(k: PadKind) {
    kindRef.current = k;
    setKind(k);
    try {
      localStorage.setItem(KIND_KEY, k);
    } catch {
      /* private mode */
    }
    link.setPad(k);
  }

  async function start() {
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen?.();
    } catch {
      /* fullscreen is optional (iPhone Safari does not support it) */
    }
    try {
      await (screen.orientation as ScreenOrientation & { lock?: (o: string) => Promise<void> })?.lock?.(
        "landscape",
      );
    } catch {
      /* orientation lock is optional */
    }
    await requestWakeLock(wakeLock);
    setPlaying(true);
  }

  function exit() {
    setPlaying(false);
    void wakeLock.current?.release().catch(() => undefined);
    wakeLock.current = null;
    if (document.fullscreenElement) void document.exitFullscreen?.().catch(() => undefined);
  }

  if (playing) {
    return <Controller kind={kind} link={link} status={status} onKind={chooseKind} onExit={exit} />;
  }

  const connected = status === "open";
  return (
    <div className="start">
      <div className="start-card">
        <h1>PhonePad</h1>
        <p className="lead">Use this phone as a game controller for your PC.</p>

        <div className={`conn ${status}`}>
          <span className="dot" />
          {connected
            ? "Connected to your PC"
            : status === "connecting"
              ? "Connecting to your PC…"
              : "Not connected – retrying…"}
        </div>

        {hello?.pad.simulated && (
          <div className="notice">
            No virtual controller on this PC: {hello.pad.error} Inputs will still show on the PC dashboard.
          </div>
        )}

        <div className="choose-label">Controller type</div>
        <div className="kind-picker">
          {(["xbox", "ps"] as PadKind[]).map((k) => (
            <button key={k} className={k === kind ? "active" : ""} onClick={() => chooseKind(k)}>
              <strong>{KIND_NAMES[k]}</strong>
              <span>{k === "xbox" ? "Works with almost every PC game" : "For emulators and DS4-aware games"}</span>
            </button>
          ))}
        </div>

        <button className="primary" onClick={start}>
          Start controller
        </button>
        <p className="hint">Hold the phone sideways. Keep this page open while you play.</p>
      </div>
    </div>
  );
}

async function requestWakeLock(ref: { current: WakeLockSentinel | null }) {
  try {
    ref.current = (await navigator.wakeLock?.request("screen")) ?? null;
  } catch {
    /* wake lock is optional */
  }
}
