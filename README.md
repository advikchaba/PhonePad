# PhonePad

PhonePad is being rebuilt as a **desktop application**, not a command-window launcher. The Windows build opens a native window containing the controller interface. You launch `PhonePad.exe` directly; no startup `.bat` file or visible command prompt is used.

> **Current build scope:** this checkout has the desktop shell and an interactive controller UI prototype. The original gamepad/WebSocket backend is not present, so button presses are visual only and are not sent to games yet.

## Build the Windows app

On Windows 10/11 with Python 3.10 or newer:

1. Double-click `build_exe.bat` (or `setup.bat`, which forwards to the same build).
2. Wait for PyInstaller to finish. The executable is created at `dist\PhonePad.exe`.
3. Double-click `dist\PhonePad.exe` to open PhonePad as a desktop application.

The build helper installs dependencies into `.venv`. It is only needed to build the executable; it is not the app launcher. The desktop window uses the Microsoft Edge WebView2 runtime available on most Windows 10/11 PCs. If WebView2 is unavailable, PhonePad shows a native fallback window with an option to open the interface in your browser.

## Run from source

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe app.py
```

`pythonw.exe` runs the native GUI without opening a console. For frontend-only work, you can also serve the UI with `python -m http.server 4173 --directory frontend` and open `http://localhost:4173`.

## Controller UI

- The controller is drawn as a familiar physical gamepad, rather than a grid of floating controls.
- Xbox and PlayStation modes update face-button legends and shoulder labels.
- Shoulder buttons are inset from the screen edges, with hit regions larger than their visual button faces.
- Buttons show held state; sticks can be dragged and report live axis values.
- Multi-touch, keyboard activation, visible focus, and reduced-motion preferences are supported.

See [`CONTROLLER_DESIGN.md`](CONTROLLER_DESIGN.md) for the ergonomic design plan and a checklist for testing with real users and devices. The UI lives in [`frontend/index.html`](frontend/index.html); the native desktop shell is in [`desktop_app.py`](desktop_app.py).

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Desktop application entry point |
| `desktop_app.py` | Native window, local UI server, and browser fallback |
| `frontend/index.html` | Standalone interactive controller UI prototype |
| `PhonePad.spec` | Windowed PyInstaller configuration (`console=False`) |
| `build_exe.bat` | Builds `dist\PhonePad.exe`; does not launch it |
| `CONTROLLER_DESIGN.md` | Ergonomics plan and validation checklist |
