"""LAN HTTP/WebSocket server for PhonePad."""
from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response

from .pad import BUTTON_BITS, VirtualGamepad

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = Path(getattr(sys, "_MEIPASS", ROOT)) / "frontend"
PORT = int(os.environ.get("PHONEPAD_PORT", "8765"))

app = FastAPI(title="PhonePad", docs_url=None, redoc_url=None)
pad = VirtualGamepad()
active_phone: WebSocket | None = None
connected = False
current_state: dict[str, Any] = {
    "buttons": [],
    "axes": {"lx": 128, "ly": 128, "rx": 128, "ry": 128},
    "lt": 0,
    "rt": 0,
}


def lan_ip() -> str:
    """Find a reachable-looking IPv4 address without sending network traffic."""
    candidates: list[str] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()
    try:
        candidates.extend(
            result[4][0]
            for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        )
    except OSError:
        pass
    for address in candidates:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.version == 4 and not parsed.is_loopback and not parsed.is_link_local:
            return address
    return "127.0.0.1"


def phone_url() -> str:
    return f"http://{lan_ip()}:{PORT}/phone"


def parse_packet(packet: bytes) -> dict[str, Any] | None:
    """Decode the compact 10-byte controller packet sent by the phone."""
    if len(packet) != 10 or packet[0] != 1:
        return None
    bits = packet[1] | (packet[2] << 8)
    axes = {"lx": packet[3], "ly": packet[4], "rx": packet[5], "ry": packet[6]}
    return {
        "buttons": [name for bit, name in BUTTON_BITS.items() if bits & (1 << bit)],
        "axes": axes,
        "lt": packet[7],
        "rt": packet[8],
        "sequence": packet[9],
    }


def public_state() -> dict[str, Any]:
    axes = current_state["axes"]
    return {
        "buttons": list(current_state["buttons"]),
        "axes": {key: round((value - 128) * 100 / (127 if value >= 128 else 128)) for key, value in axes.items()},
        "lt": round(current_state["lt"] * 100 / 255),
        "rt": round(current_state["rt"] * 100 / 255),
    }


@app.on_event("shutdown")
async def release_controller_on_shutdown() -> None:
    global connected, current_state
    connected = False
    current_state = {
        "buttons": [], "axes": {"lx": 128, "ly": 128, "rx": 128, "ry": 128}, "lt": 0, "rt": 0,
    }
    pad.release_all()


@app.get("/")
async def host_page() -> FileResponse:
    return FileResponse(FRONTEND / "host.html")


@app.get("/phone")
async def phone_page() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/status")
async def status() -> dict[str, Any]:
    return {
        "connected": connected,
        "pad_ready": pad.ready,
        "pad_error": pad.error,
        "phone_url": phone_url(),
        "state": public_state(),
    }


@app.get("/api/qr")
async def qr_code() -> Response:
    try:
        import qrcode
        from io import BytesIO

        image = qrcode.make(phone_url())
        stream = BytesIO()
        image.save(stream, format="PNG")
        return Response(stream.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"QR generation unavailable: {exc}") from exc


@app.websocket("/ws")
async def controller_socket(ws: WebSocket) -> None:
    global active_phone, connected, current_state
    await ws.accept()
    previous = active_phone
    if previous is not None and previous is not ws:
        try:
            await previous.close(code=4001, reason="A newer phone connected")
        except Exception:
            pass
    active_phone = ws
    connected = True
    pad.release_all()
    current_state = {
        "buttons": [], "axes": {"lx": 128, "ly": 128, "rx": 128, "ry": 128}, "lt": 0, "rt": 0,
    }
    await ws.send_json({"type": "ready", "pad_ready": pad.ready, "pad_error": pad.error})
    try:
        while True:
            packet = await asyncio.wait_for(ws.receive_bytes(), timeout=5.0)
            state = parse_packet(packet)
            if state is None:
                await ws.close(code=1003, reason="Invalid controller packet")
                break
            current_state = state
            pad.apply(state)
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        try:
            await ws.close(code=1001, reason="Controller heartbeat timed out")
        except Exception:
            pass
    except Exception:
        pass
    finally:
        if active_phone is ws:
            active_phone = None
            connected = False
            pad.release_all()
            current_state = {
                "buttons": [], "axes": {"lx": 128, "ly": 128, "rx": 128, "ry": 128}, "lt": 0, "rt": 0,
            }
