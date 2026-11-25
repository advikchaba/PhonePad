// WebSocket link between the phone and the PC.
//
// * Sends the newest PadState immediately.  If the socket is congested
//   (bufferedAmount > 0) only the latest state is kept and sent once the
//   socket drains, so stale stick positions never queue up.
// * Measures round-trip time with a PING every 500 ms.
// * Reconnects automatically with a short backoff.

import { decodePong, decodeRumble, encodeInput, encodePing, PadState } from "./protocol";
import type { PadKind } from "./layout";

export interface HelloInfo {
  type: "hello";
  pad: { kind: PadKind; simulated: boolean; error: string | null };
  phone: { connected: boolean };
  urls: { host: string; phone: string };
}

export type LinkStatus = "connecting" | "open" | "closed";

interface LinkEvents {
  onStatus(status: LinkStatus): void;
  onOpen(): void;
  onHello(hello: HelloInfo): void;
  onRumble(large: number, small: number): void;
}

const PING_INTERVAL_MS = 500;
const STATS_INTERVAL_MS = 2000;
const PONG_TIMEOUT_MS = 4000;

export class PadLink {
  private ws: WebSocket | null = null;
  private status: LinkStatus = "closed";
  private stopped = true;
  private retryMs = 250;
  private retryTimer: number | undefined;
  private pingTimer: number | undefined;
  private statsTimer: number | undefined;
  private flushTimer: number | undefined;
  private unsent: PadState | null = null;
  private lastPongAt = 0;
  private rttSamples: number[] = [];

  constructor(private readonly url: string, private readonly events: LinkEvents) {}

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    this.clearTimers();
    this.ws?.close();
    this.ws = null;
    this.setStatus("closed");
  }

  /** Call when the page becomes visible again: reconnect straight away. */
  wake(): void {
    if (this.stopped) return;
    if (this.status !== "open") {
      this.clearRetry();
      this.retryMs = 250;
      const old = this.ws;
      this.ws = null;
      old?.close();
      this.connect();
    }
  }

  get open(): boolean {
    return this.status === "open";
  }

  /** Average round-trip time in ms over the last few pings (null before the first pong). */
  get rtt(): number | null {
    if (this.rttSamples.length === 0) return null;
    const sum = this.rttSamples.reduce((a, b) => a + b, 0);
    return Math.round(sum / this.rttSamples.length);
  }

  /** Send the newest pad state.  Safe to call on every change. */
  send(state: PadState): void {
    this.unsent = state;
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (ws.bufferedAmount === 0) this.flush();
    else this.scheduleFlush();
  }

  setPad(kind: PadKind): void {
    this.sendText({ type: "pad", kind });
  }

  // ------------------------------------------------------------ internals
  private connect(): void {
    this.clearRetry();
    this.setStatus("connecting");
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.url);
    } catch {
      this.scheduleRetry();
      return;
    }
    ws.binaryType = "arraybuffer";
    this.ws = ws;

    ws.onopen = () => {
      this.retryMs = 250;
      this.lastPongAt = performance.now();
      this.unsent = null;
      this.setStatus("open");
      this.events.onOpen();
      this.pingTimer = window.setInterval(() => this.tick(), PING_INTERVAL_MS);
      this.statsTimer = window.setInterval(() => this.sendStats(), STATS_INTERVAL_MS);
    };

    ws.onmessage = (ev: MessageEvent) => {
      if (ev.data instanceof ArrayBuffer) {
        const pong = decodePong(ev.data);
        if (pong !== null) {
          const rtt = performance.now() - pong;
          this.lastPongAt = performance.now();
          this.rttSamples.push(rtt);
          if (this.rttSamples.length > 8) this.rttSamples.shift();
          return;
        }
        const rumble = decodeRumble(ev.data);
        if (rumble) this.events.onRumble(rumble.large, rumble.small);
        return;
      }
      try {
        const msg = JSON.parse(ev.data as string);
        if (msg?.type === "hello") this.events.onHello(msg as HelloInfo);
      } catch {
        /* ignore malformed text */
      }
    };

    ws.onclose = () => {
      if (this.ws !== ws) return; // a stale socket that was already replaced
      this.ws = null;
      this.clearLiveTimers();
      this.unsent = null;
      this.rttSamples = [];
      if (this.stopped) {
        this.setStatus("closed");
        return;
      }
      this.setStatus("closed");
      this.scheduleRetry();
    };
  }

  private tick(): void {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (performance.now() - this.lastPongAt > PONG_TIMEOUT_MS) {
      // The connection is silently dead (e.g. the phone slept or the WiFi dropped).
      ws.close();
      return;
    }
    ws.send(encodePing(performance.now()));
  }

  private sendStats(): void {
    if (this.rtt !== null) this.sendText({ type: "stats", rtt: this.rtt });
  }

  private sendText(obj: unknown): void {
    const ws = this.ws;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  private flush(): void {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN || !this.unsent) return;
    ws.send(encodeInput(this.unsent));
    this.unsent = null;
  }

  private scheduleFlush(): void {
    if (this.flushTimer !== undefined) return;
    this.flushTimer = window.setTimeout(() => {
      this.flushTimer = undefined;
      const ws = this.ws;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (ws.bufferedAmount > 0) this.scheduleFlush();
      else this.flush();
    }, 2);
  }

  private scheduleRetry(): void {
    if (this.stopped || this.retryTimer !== undefined) return;
    this.retryTimer = window.setTimeout(() => {
      this.retryTimer = undefined;
      if (!this.stopped) this.connect();
    }, this.retryMs);
    this.retryMs = Math.min(this.retryMs * 2, 2000);
  }

  private setStatus(status: LinkStatus): void {
    if (this.status === status) return;
    this.status = status;
    this.events.onStatus(status);
  }

  private clearRetry(): void {
    if (this.retryTimer !== undefined) window.clearTimeout(this.retryTimer);
    this.retryTimer = undefined;
  }

  private clearLiveTimers(): void {
    if (this.pingTimer !== undefined) window.clearInterval(this.pingTimer);
    if (this.statsTimer !== undefined) window.clearInterval(this.statsTimer);
    if (this.flushTimer !== undefined) window.clearTimeout(this.flushTimer);
    this.pingTimer = this.statsTimer = this.flushTimer = undefined;
  }

  private clearTimers(): void {
    this.clearRetry();
    this.clearLiveTimers();
  }
}

/** The WebSocket address of the server this page was loaded from. */
export function phoneSocketUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/phone`;
}
