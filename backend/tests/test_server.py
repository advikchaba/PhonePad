"""Server tests: WebSocket protocol, REST pad switching, and phone takeover.

Uses the simulated pad (no ViGEm needed), so it runs on any OS.
Requires ``httpx`` (for FastAPI's TestClient).
"""

import json
import struct
import unittest

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - httpx / fastapi missing
    TestClient = None

from backend.protocol import Btn, PadState, encode_input

try:
    from backend import main as server
except ImportError:  # pragma: no cover - fastapi / uvicorn not installed
    server = None


@unittest.skipIf(TestClient is None or server is None, "fastapi / httpx not installed")
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.configure("xbox", "192.168.1.50", 8123)
        cls.client = TestClient(server.app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_status_and_urls(self):
        st = self.client.get("/api/status").json()
        self.assertEqual(st["pad"]["kind"], "xbox")
        self.assertEqual(st["urls"]["phone"], "http://192.168.1.50:8123/?mode=phone")
        self.assertFalse(st["phone"]["connected"])

    def test_phone_input_reaches_pad_and_pings_echo(self):
        with self.client.websocket_connect("/ws/phone") as ws:
            hello = json.loads(ws.receive_text())
            self.assertEqual(hello["type"], "hello")
            self.assertTrue(self.client.get("/api/status").json()["phone"]["connected"])

            ws.send_bytes(encode_input(PadState(buttons=int(Btn.A), lx=1000)))
            ws.send_bytes(struct.pack("!Bd", 2, 42.25))
            pong = ws.receive_bytes()
            self.assertEqual(pong, struct.pack("!Bd", 2, 42.25))
            self.assertEqual(server.hub.pad.last_state.buttons, int(Btn.A))
            self.assertEqual(server.hub.pad.last_state.lx, 1000)

            ws.send_bytes(b"\x01garbage")  # malformed input is ignored, not fatal
            ws.send_text(json.dumps({"type": "stats", "rtt": 3.5}))
            ws.send_bytes(struct.pack("!Bd", 2, 1.0))
            self.assertEqual(ws.receive_bytes(), struct.pack("!Bd", 2, 1.0))
            self.assertEqual(server.hub.phone_rtt, 3.5)

        # leaving releases everything
        self.assertTrue(server.hub.pad.last_state.is_neutral())
        self.assertIsNone(server.hub.phone)

    def test_pad_switch_over_rest_and_phone_message(self):
        r = self.client.post("/api/pad", json={"kind": "ps"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["pad"]["kind"], "ps")
        self.assertEqual(self.client.post("/api/pad", json={"kind": "nope"}).status_code, 400)

        with self.client.websocket_connect("/ws/phone") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "pad", "kind": "xbox"}))
            hello = json.loads(ws.receive_text())  # broadcast after the switch
            self.assertEqual(hello["pad"]["kind"], "xbox")
        self.assertEqual(server.hub.pad.kind, "xbox")

    def test_second_phone_replaces_first(self):
        with self.client.websocket_connect("/ws/phone") as first:
            first.receive_text()
            with self.client.websocket_connect("/ws/phone") as second:
                second.receive_text()
                closed = False
                try:
                    while True:
                        first.receive_text()
                except Exception:
                    closed = True
                self.assertTrue(closed)
                self.assertIs(server.hub.phone is not None, True)
                second.send_bytes(encode_input(PadState(buttons=int(Btn.B))))
                self.assertEqual(server.hub.pad.last_state.buttons, int(Btn.B))

    def test_host_dashboard_receives_status(self):
        with self.client.websocket_connect("/ws/host") as ws:
            snap = json.loads(ws.receive_text())
            self.assertEqual(snap["type"], "status")
            self.assertIn("state", snap)


if __name__ == "__main__":
    unittest.main()
