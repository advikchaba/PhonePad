"""Windowed desktop host for the PhonePad LAN controller server."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


PORT = int(os.environ.get("PHONEPAD_PORT", "8765"))


def maybe_install_driver(gamepad_module: object) -> None:
    """Offer the bundled ViGEmBus installer when no virtual pad is available."""
    if os.name != "nt" or gamepad_module.pad.ready:
        return
    from tkinter import Tk, messagebox

    root = Tk()
    root.withdraw()
    try:
        from importlib.util import find_spec

        spec = find_spec("vgamepad")
        package_dir = Path(spec.origin).resolve().parent if spec and spec.origin else None
        architecture = "x64" if platform.architecture()[0] == "64bit" else "x86"
        msi = package_dir / "win" / "vigem" / "install" / architecture / f"ViGEmBusSetup_{architecture}.msi" if package_dir else None
    except Exception:
        msi = None
    if msi is None or not msi.is_file():
        messagebox.showinfo(
            "Gamepad driver needed",
            "PhonePad needs the ViGEmBus driver before games can see the virtual controller. "
            "Install it from https://github.com/nefarius/ViGEmBus/releases, then restart PhonePad.",
            parent=root,
        )
        root.destroy()
        return
    if not messagebox.askyesno(
        "Install virtual gamepad driver?",
        "PhonePad needs the ViGEmBus driver so Windows games can see your phone as an Xbox controller.\n\n"
        "Install it now? Windows will ask for administrator approval. This is a one-time install.",
        parent=root,
    ):
        root.destroy()
        return
    escaped_msi = str(msi).replace("'", "''")
    script = (
        "$msi = '" + escaped_msi + "'; "
        "$args = '/i \"' + $msi + '\" /passive /norestart'; "
        "$p = Start-Process -FilePath 'msiexec.exe' -ArgumentList $args -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode in (0, 3010):
            from backend.pad import VirtualGamepad

            gamepad_module.pad = VirtualGamepad()
            if gamepad_module.pad.ready:
                messagebox.showinfo("PhonePad ready", "ViGEmBus is installed. Connect your phone and start playing.", parent=root)
            elif proc.returncode == 3010:
                messagebox.showinfo("Restart required", "Windows requested a restart to finish installing ViGEmBus.", parent=root)
        else:
            messagebox.showwarning("Driver installation incomplete", "Install ViGEmBus manually, then restart PhonePad.", parent=root)
    except Exception as exc:
        messagebox.showerror("Driver installation failed", str(exc), parent=root)
    finally:
        root.destroy()


def show_browser_fallback(url: str, detail: str) -> None:
    """Keep a small native app window available if WebView2 cannot open."""
    from tkinter import Tk
    import tkinter as tk

    root = Tk()
    root.title("PhonePad")
    root.geometry("400x250")
    root.minsize(360, 220)
    root.configure(bg="#101319")
    root.resizable(False, False)
    tk.Label(root, text="PhonePad", bg="#101319", fg="#f5f6f8",
             font=("Segoe UI", 20, "bold")).pack(pady=(24, 5))
    tk.Label(root, text="The host is running. Open the dashboard to connect your phone.",
             bg="#101319", fg="#b9bfca", font=("Segoe UI", 10), wraplength=340).pack(pady=4)
    tk.Label(root, text=detail, bg="#101319", fg="#747d8c",
             font=("Segoe UI", 8), wraplength=340).pack(pady=(5, 12))
    tk.Button(root, text="Open dashboard", command=lambda: webbrowser.open(url),
              bg="#8b72ee", fg="white", activebackground="#a18df5",
              activeforeground="white", relief="flat", padx=18, pady=8,
              font=("Segoe UI", 10, "bold"), cursor="hand2").pack()
    webbrowser.open(url)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


def main() -> None:
    server = None
    thread: threading.Thread | None = None
    try:
        import uvicorn
        import backend.main as backend_main

        maybe_install_driver(backend_main)
        app = backend_main.app
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level="error",
            log_config=None,  # Avoid Uvicorn's default formatter calling isatty() on windowed sys.stdout=None.
            access_log=False,
        )
        server = uvicorn.Server(config)

        def serve() -> None:
            try:
                server.run()
            except Exception as exc:
                server._phonepad_error = exc  # surfaced by the waiting startup loop

        thread = threading.Thread(target=serve, name="PhonePad LAN server", daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not server.started:
            error = getattr(server, "_phonepad_error", None)
            raise RuntimeError(str(error or f"PhonePad could not start on port {PORT}. Is another instance already running?"))

        url = f"http://127.0.0.1:{PORT}/"
        try:
            import webview

            webview.create_window(
                "PhonePad",
                url,
                width=1180,
                height=800,
                min_size=(760, 560),
                background_color="#101319",
            )
            webview.start(debug=False)
        except Exception as exc:
            show_browser_fallback(url, f"The embedded browser could not start ({exc}); the dashboard opened in your default browser.")
    except Exception as exc:
        try:
            from tkinter import Tk, messagebox

            root = Tk()
            root.withdraw()
            messagebox.showerror("PhonePad could not start", str(exc))
            root.destroy()
        except Exception:
            print(f"PhonePad could not start: {exc}", file=sys.stderr)
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
