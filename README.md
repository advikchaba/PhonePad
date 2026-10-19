# PhonePad

Your phone becomes a **real controller** for your PC over local WiFi.

No app to install, no cables, no Bluetooth pairing: you scan a QR code, tilt the phone sideways, and Windows sees a real gamepad that your games already support.

* **React** front end (touch controller + desktop dashboard), served by the PC
* **Python / FastAPI** back end with a binary WebSocket protocol
* **ViGEmBus** virtual gamepad driver, so games get a genuine XInput or DS4 device
* Everything stays on your LAN - no cloud, no accounts, no telemetry

---

## Quick start - portable exe (nothing to install)

Copy **`dist\PhonePad.exe`** to the PC and double-click it. That single file
contains Python, the server and the built web app.

1. If ViGEmBus is not installed yet, PhonePad offers to install the bundled
   copy. Answer **Y** and accept the Windows admin prompt.
2. The dashboard opens in your browser. Scan the QR code with your phone.
3. If Windows asks about network access, allow **private networks**.

If SmartScreen says "Windows protected your PC", choose **More info → Run
anyway** - the exe is unsigned. Some antivirus tools flag PyInstaller
executables; that is a false positive.

Rebuild the exe after changing the code with **`build_exe.bat`**.

---

## Requirements

| What | Why |
| --- | --- |
| Windows 10 / 11 | The virtual pad driver is Windows only |
| [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) | Creates the virtual Xbox / PlayStation controller (the exe offers to install it) |
| Python 3.10+ | Runs the server from source - not needed with `PhonePad.exe` |
| Node.js 18+ | Only to build the web app from source |
| Phone + WiFi router | Phone and PC must be on the **same** network |

The phone can be any modern iPhone or Android device - it just needs a browser (Safari, Chrome, Edge, Firefox).

---

## Run from source (optional)

Only needed if you want to run the Python code directly instead of the exe.

Double-click **`setup.bat`**.

It will:

1. create a Python virtual environment in `.venv`
2. install the Python packages (`fastapi`, `uvicorn`, `vgamepad`)
3. install and build the React app into `backend\static`

<details>
<summary>Manual setup instead of the script</summary>

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm.cmd install
npm.cmd run build
cd ..
```
</details>

The build output is copied to `backend\static`, so after this step you never need Node again unless you change the front end.

---

## Play

Double-click **`PhonePad.exe`** (or **`start.bat`** when running from source).

The server prints something like:

```
  On this PC    : http://127.0.0.1:8000
  On your phone : http://192.168.1.7:8000/?mode=phone
```

Your browser opens the **desktop dashboard** automatically.

1. **Scan the QR code** with your phone camera (or type the shown address into the phone browser).
2. Pick **Xbox** or **PlayStation**. Xbox is the safest choice for games.
3. Tap **Start controller** and hold the phone **sideways**.
4. Play. The dashboard shows a live mirror of the pad, packets per second and round-trip latency.

To stop, close the black server window (or press `Ctrl+C` in it).

Want to start straight into PlayStation mode? Run `start.bat ps` instead (`start.bat xbox` for Xbox). You can still switch while playing.

> **Firewall:** the first time, Windows may ask whether Python (or `PhonePad.exe`) can use the network. Allow it on **private networks**. If the phone cannot connect, press **Fix** next to "Firewall may block your phone" on the dashboard and accept the admin prompt (it adds an allow rule for the program that runs the server).

---

## The controller

The layout is designed for thumbs, not for copying a plastic shell pixel for pixel:

* **Triggers** (`LT/RT` or `L2/R2`) sit **above** the bumpers (`LB/RB` or `L1/R1`) in the top corners, like on a real pad.
* **Face buttons** are labelled `A B X Y` in Xbox mode and `✕ ○ □ △` in PlayStation mode.
* **Sticks** are true analog, with a dead zone and a smooth outer range.
* The **d-pad** reads the angle of your thumb, so diagonal directions work and sliding between directions feels natural.
* Touch and slide across buttons: press one, drag to another, release. Multi-touch is fully supported (sticks + buttons at once).

### Settings (gear icon, bottom right)

| Setting | What it does |
| --- | --- |
| **Controller** | Switch between Xbox 360 and DualShock 4 on the fly |
| **Layout** | `Comfort` (default), `Classic` (left stick high, d-pad low), `Shooter` (big right stick, buttons out of the thumb zone) |
| **Vibration** | Passes game rumble to the phone (Android; iOS Safari has no vibration API) |
| **Analog triggers** | Ramps the triggers instead of snapping them to 0/255 - better for racing games |
| **Fullscreen / Reconnect** | Re-enter immersive mode, or rebuild the WebSocket connection |

The phone keeps the screen awake and asks for landscape orientation while the controller is open.

---

## Xbox vs PlayStation

| | Xbox 360 (XInput) | DualShock 4 (DirectInput/HID) |
| --- | --- | --- |
| Game support | Almost everything on Windows | Only games/emulators that support DS4 or DirectInput |
| Button prompts | `A B X Y` | `✕ ○ □ △` |
| Extras | - | Touchpad click, PS button |
| Best for | Steam, Epic, Game Pass, most AAA games | Emulators (RPCS3, yuzu, DuckStation), PS Remote Play style setups |

**Use Xbox mode unless you specifically want PlayStation prompts.** Games that only speak XInput (most of them) will not see a DualShock 4 at all. If you want PS prompts in a Steam game, keep PhonePad in Xbox mode and let Steam Input translate.

Switching pad type recreates the virtual device. Some games only look for controllers at launch - if a game stops responding after a switch, restart the game.

---

## Checking that Windows sees the pad

1. Press `Win + R`, type `joy.cpl`, press Enter.
2. You should see **Xbox 360 Controller for Windows** (or **Wireless Controller** for DS4).
3. Open **Properties** and move sticks / press buttons on the phone - the test window reacts.

If `joy.cpl` is empty, the driver or the virtual device is not working; see below.

---

## Troubleshooting

**The phone shows "Reconnecting..." forever**
* Phone and PC must be on the same WiFi. Guest networks and "client isolation" block device-to-device traffic.
* A VPN on the phone or PC can hijack local traffic - turn it off.
* Allow Python through Windows Firewall, or press **Fix** on the dashboard.
* Try the IP address shown on the dashboard manually (`http://192.168.x.x:8000/?mode=phone`).

**SmartScreen / antivirus flags `PhonePad.exe`**
* The exe is unsigned: choose **More info → Run anyway**.
* If antivirus quarantined it, restore the file and add an exclusion.
* You can always build it yourself with `build_exe.bat` - the source is included.

**No controller in `joy.cpl` / the game**
* Is ViGEmBus installed? Reboot after installing it, then restart `start.bat`.
* The dashboard shows **Virtual controller ready** when the device exists.
* Some launchers cache the controller list: start PhonePad *before* the game, or restart the game.

**The game ignores the pad in PlayStation mode**
* Switch to **Xbox** and press **Reconnect** on the phone. Most Windows games are XInput only.

**"Rotate your phone" is stuck on screen**
* The phone must be in landscape. If your browser refuses to rotate, turn off the phone's orientation lock.
* iPhone Safari cannot force fullscreen/orientation; rotating the device manually works.

**Input lags or stutters**
* Use the **5 GHz** WiFi band and stay near the router.
* Keep the browser tab in the foreground - background tabs are throttled by the phone.
* Disable battery saver for the browser.
* Close other heavy downloads on the same network. Typical loopback latency is 2-5 ms; WiFi adds 3-15 ms.

**The virtual pad suddenly stops mid-game**
* The phone screen locked or the tab was backgrounded → unlock and reopen the tab; the controller reconnects automatically.
* Another phone connected: only one phone controls the pad at a time, the newest wins.

**Port 8000 is already in use**
* The server automatically picks the next free port and prints the new address/QR code.

**`vgamepad` fails to install**
* It needs a 64-bit Python. Install 64-bit Python 3.12 and re-run `setup.bat`.

---

## Project layout

```
backend/
  main.py         FastAPI app: API, WebSockets, static files, banner
  pad.py          ViGEmBus engine (Xbox 360 / DS4), rumble, hot-swap
  protocol.py     binary input packets + state JSON
  static/         built React app (generated)
frontend/
  src/host/       desktop dashboard, QR code, live mirror
  src/phone/      start screen, touch controller, settings sheet
  src/lib/        WebSocket hook, packet builder
app.py            launcher: driver check, then starts the server
PhonePad.spec     PyInstaller recipe
setup.bat         one-time install + build (source)
start.bat         run the server (source)
build_exe.bat     build dist\PhonePad.exe
dist/             packaged executable (generated)
```

### Protocol (for the curious)

The phone sends a 10-byte binary packet per update instead of JSON:

| Bytes | Content |
| --- | --- |
| 0 | message type (`1` input, `2` ping) |
| 1-2 | 16 button bits (A, B, X, Y, LB, RB, Back, Start, LS, RS, D-pad, Guide, touchpad) |
| 3-6 | left stick X / Y, right stick X / Y (`0..255`, `128` = center) |
| 7-8 | left trigger, right trigger (`0..255`) |
| 9 | rolling sequence number |

The phone sends at up to 120 Hz (animation frames + immediate sends on press/release); the server writes the state to the virtual pad every 4 ms and streams the live state to the desktop dashboard at 30 Hz.

---

## Notes

* Only one phone drives the pad at a time; the most recent connection takes over and the older one is disconnected.
* Nothing leaves your network. The server binds to all interfaces so the phone can reach it, and there is no authentication - use it on networks you trust.
* Rumble is read from the virtual pad and forwarded to the phone (Android only).
* PhonePad is a personal project, not affiliated with Microsoft, Sony or the ViGEmBus authors.
