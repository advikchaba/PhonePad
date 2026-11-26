# PhonePad

Use your phone as a wireless **keyboard-and-mouse controller** for PC games. PhonePad runs a local Wi-Fi server in a native Windows desktop app. Its PC dashboard does not require an external browser runtime; your phone opens the controller in its built-in browser. No phone app, gamepad driver, account, or cloud service is required.

## Download and play

1. Download [PhonePad 1.04 for Windows](https://github.com/advikchaba/PhonePad/releases/download/1.04/PhonePad.exe).
2. Open `PhonePad.exe` on the PC. It starts as a desktop window without a command prompt.
3. If Windows Firewall asks, allow PhonePad on **private networks**.
4. Connect the phone and PC to the same trusted Wi-Fi network.
5. Scan the QR code in the desktop window with the phone camera, or open the displayed address in the phone's built-in browser.
6. Keep the PC window open, focus the game, and play. The desktop dashboard mirrors live phone input.

## Keyboard and mouse mapping

The PC receives normal Windows keyboard and mouse events—**not a virtual gamepad**. Defaults are:

| Phone control | PC input |
| --- | --- |
| Left stick | W / A / S / D |
| Right stick | Relative mouse movement |
| A / B / X / Y | Space / Left Ctrl / E / Q |
| LB / RB | Left Shift / R |
| LT / RT | Right-click / Left-click |
| View / Menu | Tab / Escape |
| D-pad | Arrow keys |

Use **Customize** in the desktop app to assign each face button, bumper, trigger, menu button, stick click, Guide button, and D-pad direction to a different key, mouse button, or `None`. The selection is saved in `%LOCALAPPDATA%\PhonePad\settings.json` on Windows and restored at the next launch. Left stick movement remains WASD and the right stick remains mouse movement.

This works with games that accept keyboard and mouse. It will not provide controller prompts or true gamepad APIs, and some games—especially games with strict anti-cheat or elevated privileges—may reject injected input. Keep the game window focused. You can run PhonePad as administrator only if the game itself is elevated.

## Network and privacy

The phone and PC must be on the same local network. PhonePad sends input directly over HTTP/WebSocket on that network; it has no authentication, so use a trusted private Wi-Fi network and do not expose it to the internet.

## Run from source / build

On Windows with Python 3.10 or newer:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe app.py
```

Run `build_exe.bat` to create a self-contained `dist\PhonePad.exe`. The Windows release workflow publishes builds on the [releases page](https://github.com/advikchaba/PhonePad/releases).

## Project files

| File | Purpose |
| --- | --- |
| `desktop_app.py` | Native Tk desktop dashboard and LAN server lifecycle |
| `backend/main.py` | HTTP endpoints, phone WebSocket, QR, and live state |
| `backend/pad.py` | Driver-free Windows keyboard/mouse event mapping |
| `frontend/host.html` | Desktop connection dashboard and live input mirror |
| `frontend/index.html` | Phone controller interface |
| `PhonePad.spec` | Windowed PyInstaller build |
| `CONTROLLER_DESIGN.md` | Ergonomic layout plan and validation checklist |
