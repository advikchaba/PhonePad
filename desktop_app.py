"""Windowed desktop host for the PhonePad LAN controller server."""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser


PORT = int(os.environ.get("PHONEPAD_PORT", "8765"))



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
