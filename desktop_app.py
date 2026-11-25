"""Launch the PhonePad controller UI in a native desktop window.

The executable is packaged with PyInstaller in windowed mode so launching it
never opens a terminal. The current checkout contains the UI prototype only;
this shell deliberately does not claim to connect to a virtual gamepad.
"""
from __future__ import annotations

import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve the bundled UI without writing request logs to a console."""

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def frontend_dir() -> Path:
    """Return the source or PyInstaller-bundled frontend directory."""
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        root = Path(__file__).resolve().parent
    path = root / "frontend"
    if not (path / "index.html").is_file():
        raise FileNotFoundError(f"The PhonePad interface was not found at {path}")
    return path


def start_ui_server() -> tuple[ThreadingHTTPServer, str]:
    """Serve the local UI on an ephemeral loopback port."""
    directory = str(frontend_dir())

    class Handler(QuietHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=directory, **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="PhonePad UI", daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/"


def show_browser_fallback(url: str, detail: str) -> None:
    """Keep a small native app window available if WebView2 is unavailable."""
    from tkinter import Tk

    root = Tk()
    root.title("PhonePad")
    root.geometry("390x220")
    root.minsize(360, 200)
    root.configure(bg="#101319")
    root.resizable(False, False)

    import tkinter as tk

    tk.Label(root, text="PhonePad", bg="#101319", fg="#f5f6f8",
             font=("Segoe UI", 20, "bold")).pack(pady=(24, 5))
    tk.Label(root, text="Your controller preview is ready in your browser.",
             bg="#101319", fg="#b9bfca", font=("Segoe UI", 10)).pack(pady=4)
    tk.Label(root, text=detail, bg="#101319", fg="#747d8c",
             font=("Segoe UI", 8), wraplength=330).pack(pady=(5, 12))
    tk.Button(root, text="Open controller", command=lambda: webbrowser.open(url),
              bg="#8b72ee", fg="white", activebackground="#a18df5",
              activeforeground="white", relief="flat", padx=18, pady=8,
              font=("Segoe UI", 10, "bold"), cursor="hand2").pack()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


def main() -> None:
    server: ThreadingHTTPServer | None = None
    try:
        server, url = start_ui_server()
        try:
            import webview
        except ImportError:
            show_browser_fallback(url, "Install the desktop webview dependency to display the UI inside this window.")
            return

        try:
            webview.create_window(
                "PhonePad",
                url,
                width=1180,
                height=780,
                min_size=(720, 520),
                background_color="#101319",
            )
            # On Windows, pywebview uses the installed Microsoft Edge WebView2 runtime.
            webview.start(debug=False)
        except Exception as exc:
            show_browser_fallback(url, f"The embedded browser could not start: {exc}")
    except Exception as exc:
        try:
            from tkinter import Tk, messagebox

            root = Tk()
            root.withdraw()
            messagebox.showerror("PhonePad could not start", str(exc))
            root.destroy()
        except Exception:
            # Last-resort error path for environments without a GUI session.
            print(f"PhonePad could not start: {exc}", file=sys.stderr)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
