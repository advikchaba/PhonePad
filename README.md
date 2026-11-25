# PhonePad

Turn an Android or iPhone browser into a touch controller for Windows games. PhonePad runs a small LAN server on the PC, sends phone controls over WebSocket, and presents them to Windows as a virtual Xbox 360 controller.

## Install and play

1. Download the latest Windows build: [PhonePad.exe](https://github.com/advikchaba/PhonePad/releases/download/desktop-preview/PhonePad.exe).
2. Install the bundled **ViGEmBus** driver when PhonePad offers. Approve the Windows administrator prompt. This one-time driver lets games see the virtual controller.
3. Start PhonePad on the PC. If Windows Firewall asks, allow it on **private networks**.
4. Connect the phone and PC to the **same trusted Wi-Fi network**.
5. Scan the QR code shown in the PhonePad desktop window, or open the displayed address on your phone.
6. Hold the phone in landscape and play. The PC window mirrors the phone's buttons, sticks, and triggers.

If the driver prompt was skipped, install ViGEmBus from [its official releases](https://github.com/nefarius/ViGEmBus/releases), then restart PhonePad. The desktop window reports whether the phone and virtual pad are ready.

## Controls and connection

The phone page presents a familiar Xbox-style controller, with a PlayStation legend option. Touch and hold buttons; drag on the sticks for analog movement; multi-touch supports simultaneous controls. Bumpers are inset from the screen edges with forgiving hit areas. Disconnecting the phone releases all virtual controls so inputs cannot remain stuck.

PhonePad uses HTTP and a binary WebSocket on the local network. Keep both devices on a private, trusted Wi-Fi network; the controller server has no authentication and is not intended to be exposed to the internet. Only one phone controls the virtual pad at a time.

## Run from source

On Windows with Python 3.10 or newer:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe app.py
```

To build a fresh windowed executable, run `build_exe.bat`. It creates `dist\PhonePad.exe`; launch that executable directly—there is no startup batch file or command window. The build workflow also publishes the Windows download on the [releases page](https://github.com/advikchaba/PhonePad/releases).

## Project files

| File | Purpose |
| --- | --- |
| `desktop_app.py` | Windowed desktop host and LAN server lifecycle |
| `backend/main.py` | HTTP endpoints, phone WebSocket, QR, and live state |
| `backend/pad.py` | ViGEmBus / XInput virtual gamepad output |
| `frontend/host.html` | Desktop connection dashboard and live input mirror |
| `frontend/index.html` | Phone controller interface |
| `PhonePad.spec` | Windowed PyInstaller build |
| `CONTROLLER_DESIGN.md` | Ergonomic layout plan and validation checklist |
