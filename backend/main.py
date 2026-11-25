"""PhonePad server.

* ``/``                  desktop dashboard (React, served from ``backend/static``)
* ``/?mode=phone``       touch controller for the phone (same build)
* ``/ws/phone``          binary input stream from the phone (see ``protocol.py``)
* ``/ws/host``           JSON status stream for the dashboard, 10 Hz
* ``/api/status``        GET  - addresses, pad state, phone state
* ``/api/pad``           POST - ``{"kind": "xbox" | "ps"}`` hot-swaps the virtual pad

Run with ``python -m backend.main``.  Environment variables:
``PHONEPAD_PAD`` (xbox|ps), ``PHONEPAD_PORT`` (default 8000),
``PHONEPAD_NO_BROWSER`` (do not open the dashboard automatically).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .pad import KINDS, PadManager
from .protocol import (
    MSG_INPUT,
    MSG_PING,
    encode_rumble,
    parse_input,
)

log = logging.getLogger("phonepad")

DEFAULT_PORT = 8000
PHONE_SILENCE_TIMEOUT = 2.0  # seconds without any packet before inputs are released


def _static_dir() -> Path:
    here = Path(__file__).resolve().parent / "static"
    if here.is_dir():
        return here
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ".")) / "backend" / "static"
    return here


STATIC_DIR = _static_dir()


class Hub:
    """Shared state: the pad, the one connected phone and the dashboards."""

    def __init__(self, pad_kind: str, lan_ip: str, port: int) -> None:
        self.lan_ip = lan_ip
        self.port = port
        self.loop: asyncio.AbstractEventLoop | None = None
        self.phone: WebSocket | None = None
        self.phone_ip: str | None = None
        self.phone_since: float = 0.0
        self.phone_rtt: float | None = None
        self.last_seen: float = 0.0
        self.hosts: set[WebSocket] = set()
        self.packets = 0
        self.pps = 0
        self._window_start = time.monotonic()
        self._window_count = 0
        self._last_rumble: tuple[int, int] = (0, 0)
        self.pad = PadManager(self._on_rumble_thread, pad_kind)

    # ------------------------------------------------------------ helpers
    @property
    def phone_url(self) -> str:
        return f"http://{self.lan_ip}:{self.port}/?mode=phone"

    def status(self) -> dict:
        return {
            "pad": self.pad.status(),
            "phone": {
                "connected": self.phone is not None,
                "ip": self.phone_ip,
                "rtt": self.phone_rtt,
                "pps": self.pps,
                "since": self.phone_since or None,
            },
            "urls": {
                "host": f"http://127.0.0.1:{self.port}/",
                "phone": self.phone_url,
                "lan_ip": self.lan_ip,
                "port": self.port,
            },
            "version": 2,
        }

    def snapshot(self) -> dict:
        return {
            "type": "status",
            "pad": self.pad.status(),
            "phone": self.status()["phone"],
            "state": asdict(self.pad.last_state),
        }

    # ------------------------------------------------------------- rumble
    def _on_rumble_thread(self, large: int, small: int) -> None:
        """Called from the ViGEm notification thread."""
        if self.loop is not None and (large, small) != self._last_rumble:
            self._last_rumble = (large, small)
            self.loop.call_soon_threadsafe(asyncio.ensure_future, self._send_rumble(large, small))

    async def _send_rumble(self, large: int, small: int) -> None:
        ws = self.phone
        if ws is None:
            return
        try:
            await ws.send_bytes(encode_rumble(large, small))
        except Exception:
            pass

    # --------------------------------------------------------- phone life
    async def attach_phone(self, ws: WebSocket, ip: str | None) -> None:
        old = self.phone
        self.phone = ws
        self.phone_ip = ip
        self.phone_since = time.time()
        self.phone_rtt = None
        self.last_seen = time.monotonic()
        self.pad.reset()
        if old is not None:
            log.info("A new phone took over the controller from the previous one")
            try:
                await old.close(code=4000, reason="Replaced by another phone")
            except Exception:
                pass
        await self.broadcast_hosts()

    async def detach_phone(self, ws: WebSocket) -> None:
        if self.phone is ws:  # ignore if this socket was already replaced
            self.phone = None
            self.phone_ip = None
            self.phone_since = 0.0
            self.phone_rtt = None
            self.pad.reset()
            log.info("Phone disconnected - all inputs released")
            await self.broadcast_hosts()

    async def on_binary(self, ws: WebSocket, data: bytes) -> None:
        kind = data[0] if data else -1
        if kind == MSG_INPUT:
            state = parse_input(data)
            if state is None:
                return
            self.packets += 1
            self._window_count += 1
            self.pad.apply(state)
        elif kind == MSG_PING:
            await ws.send_bytes(data)  # echo unchanged; the phone measures the round trip

    async def on_text(self, ws: WebSocket, text: str) -> None:
        try:
            msg = json.loads(text)
        except ValueError:
            return
        mtype = msg.get("type")
        if mtype == "pad":
            kind = msg.get("kind")
            if kind in KINDS:
                await self.switch_pad(kind)
        elif mtype == "stats":
            rtt = msg.get("rtt")
            if isinstance(rtt, (int, float)) and 0 <= rtt < 60_000:
                self.phone_rtt = round(float(rtt), 1)

    async def switch_pad(self, kind: str) -> None:
        if kind == self.pad.kind:
            return
        log.info("Switching virtual controller to %s", "Xbox 360" if kind == "xbox" else "DualShock 4")
        await asyncio.to_thread(self.pad.switch, kind)
        await self.broadcast_hosts()
        if self.phone is not None:
            try:
                await self.phone.send_text(json.dumps({"type": "hello", **self.status()}))
            except Exception:
                pass

    # ------------------------------------------------------------ hosts
    async def broadcast_hosts(self) -> None:
        payload = json.dumps(self.snapshot())
        for ws in list(self.hosts):
            try:
                await ws.send_text(payload)
            except Exception:
                self.hosts.discard(ws)

    async def watchdog(self) -> None:
        """Release inputs when the phone goes silent; keep the packets/s counter."""
        while True:
            await asyncio.sleep(0.1)
            now = time.monotonic()
            if now - self._window_start >= 1.0:
                self.pps = self._window_count
                self._window_count = 0
                self._window_start = now
            if self.phone is not None and now - self.last_seen > PHONE_SILENCE_TIMEOUT:
                if not self.pad.last_state.is_neutral():
                    log.warning("Phone went silent - releasing all inputs")
                    self.pad.reset()
            if self.hosts:
                await self.broadcast_hosts()


hub: Hub | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert hub is not None, "configure() must run before the server starts"
    hub.loop = asyncio.get_running_loop()
    task = asyncio.create_task(hub.watchdog())
    try:
        yield
    finally:
        task.cancel()
        hub.pad.close()


app = FastAPI(title="PhonePad", lifespan=lifespan)


def configure(pad_kind: str, lan_ip: str, port: int) -> Hub:
    global hub
    hub = Hub(pad_kind, lan_ip, port)
    return hub


# ----------------------------------------------------------------- REST
@app.get("/api/status")
def api_status() -> dict:
    return hub.status()


@app.post("/api/pad")
async def api_pad(body: dict = Body(...)) -> dict:
    kind = body.get("kind")
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail="kind must be 'xbox' or 'ps'")
    await hub.switch_pad(kind)
    return hub.status()


# ------------------------------------------------------------ WebSockets
@app.websocket("/ws/phone")
async def ws_phone(ws: WebSocket) -> None:
    await ws.accept()
    ip = ws.client.host if ws.client else None
    log.info("Phone connected from %s", ip)
    await hub.attach_phone(ws, ip)
    try:
        await ws.send_text(json.dumps({"type": "hello", **hub.status()}))
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect" or hub.phone is not ws:
                break  # closed, or replaced by a newer phone
            hub.last_seen = time.monotonic()
            if msg.get("bytes") is not None:
                await hub.on_binary(ws, msg["bytes"])
            elif msg.get("text") is not None:
                await hub.on_text(ws, msg["text"])
    except WebSocketDisconnect:
        pass
    except RuntimeError:  # socket closed underneath us
        pass
    finally:
        await hub.detach_phone(ws)


@app.websocket("/ws/host")
async def ws_host(ws: WebSocket) -> None:
    await ws.accept()
    hub.hosts.add(ws)
    try:
        await ws.send_text(json.dumps(hub.snapshot()))
        while True:
            await ws.receive()  # returns on disconnect; the dashboard sends nothing
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.hosts.discard(ws)


# ------------------------------------------------------------ web app
if (STATIC_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
else:

    @app.get("/", response_class=HTMLResponse)
    def _not_built() -> str:
        return (
            "<h1>PhonePad</h1><p>The web app has not been built yet. "
            "Run <code>setup.bat</code> (or <code>npm run build</code> in <code>frontend/</code>).</p>"
        )


# ------------------------------------------------------------- launcher
def lan_ip() -> str:
    """The address other devices on the WiFi use to reach this PC."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # no packet is sent; this only picks the route
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Same flag uvicorn uses: ignore sockets left in TIME_WAIT by a previous run.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found between {preferred} and {preferred + 19}")


def _banner(h: Hub) -> None:
    pad_name = "Xbox 360" if h.pad.kind == "xbox" else "DualShock 4 (PlayStation)"
    line = "=" * 64
    print(line)
    print("  PhonePad is running")
    print(line)
    print(f"  On this PC    : http://127.0.0.1:{h.port}")
    print(f"  On your phone : {h.phone_url}")
    print(f"  Controller    : {pad_name}")
    st = h.pad.status()
    if h.pad.simulated:
        print(f"  Virtual pad   : SIMULATED - {st['error']}")
    else:
        print("  Virtual pad   : ready")
    print(line)
    print("  Scan the QR code on the dashboard with your phone camera.")
    print("  Press Ctrl+C to stop.")
    print(line)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    kind = os.environ.get("PHONEPAD_PAD", "xbox").strip().lower()
    if kind not in KINDS:
        kind = "xbox"
    preferred = int(os.environ.get("PHONEPAD_PORT", DEFAULT_PORT))
    port = pick_port(preferred)
    h = configure(kind, lan_ip(), port)
    _banner(h)
    if not os.environ.get("PHONEPAD_NO_BROWSER"):
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}/")).start()

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
        access_log=False,
        ws_ping_interval=10,
        ws_ping_timeout=20,
    )


if __name__ == "__main__":
    main()
