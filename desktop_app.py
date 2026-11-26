"""Native Windows desktop host for the PhonePad LAN controller."""
from __future__ import annotations

import os
import threading
import time
from typing import Any

PORT = int(os.environ.get("PHONEPAD_PORT", "8765"))


def main() -> None:
    """Run the local server beside a native Tk dashboard (no WebView/browser on PC)."""
    import tkinter as tk
    from tkinter import messagebox

    try:
        import uvicorn
        import backend.main as backend_main
        import qrcode
        from PIL import ImageTk
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("PhonePad could not start", str(exc))
        root.destroy()
        return

    bg = "#101319"
    panel = "#191d25"
    panel_alt = "#20242d"
    line = "#303540"
    text = "#f5f6f8"
    muted = "#9aa2b0"
    accent = "#a78bfa"
    green = "#55d6a2"
    amber = "#f3bd5e"

    root = tk.Tk()
    root.title("PhonePad")
    root.geometry("980x720")
    root.minsize(820, 640)
    root.configure(bg=bg)

    def label(parent: Any, value: str, *, size: int = 10, color: str = text,
              bold: bool = False, **kwargs: Any) -> tk.Label:
        return tk.Label(parent, text=value, bg=kwargs.pop("bg", parent.cget("bg")), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor=kwargs.pop("anchor", "w"), justify=kwargs.pop("justify", "left"),
                        **kwargs)

    header = tk.Frame(root, bg=bg, padx=28, pady=18)
    header.pack(fill="x")
    logo = tk.Label(header, text="⌘", bg="#7055d9", fg="white", width=3, height=1,
                    font=("Segoe UI Symbol", 16, "bold"), padx=3, pady=4)
    logo.pack(side="left")
    brand = tk.Frame(header, bg=bg)
    brand.pack(side="left", padx=12)
    label(brand, "PhonePad", size=17, bold=True).pack(anchor="w")
    label(brand, "Phone-to-PC wireless controls", size=9, color=muted).pack(anchor="w", pady=(1, 0))
    badge = label(header, "NO DRIVER REQUIRED", size=9, color="#d7c9ff", bold=True,
                  bg="#302842", padx=12, pady=7)
    badge.pack(side="right")
    tk.Frame(root, bg=line, height=1).pack(fill="x")

    content = tk.Frame(root, bg=bg, padx=28, pady=20)
    content.pack(fill="both", expand=True)
    label(content, "CONNECT YOUR PHONE", size=9, color=accent, bold=True).pack(anchor="w")
    label(content, "Scan the code. Start playing.", size=23, bold=True).pack(anchor="w", pady=(7, 4))
    label(content, "Use the phone's built-in browser. Put both devices on the same trusted Wi-Fi.", size=10, color=muted).pack(anchor="w", pady=(0, 17))

    columns = tk.Frame(content, bg=bg)
    columns.pack(fill="both", expand=True)
    columns.grid_columnconfigure(0, weight=6, uniform="cards")
    columns.grid_columnconfigure(1, weight=4, uniform="cards")
    columns.grid_rowconfigure(0, weight=1)

    connect_card = tk.Frame(columns, bg=panel, highlightbackground=line, highlightthickness=1, padx=20, pady=18)
    connect_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    status_card = tk.Frame(columns, bg=panel, highlightbackground=line, highlightthickness=1, padx=18, pady=18)
    status_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

    label(connect_card, "PHONE CONNECTION", size=9, color=muted, bold=True).pack(anchor="w")
    connected_text = tk.StringVar(value="Starting PhonePad server…")
    connected_label = label(connect_card, "", size=12, bold=True)
    connected_label.configure(textvariable=connected_text)
    connected_label.pack(anchor="w", pady=(10, 12))

    qr_frame = tk.Frame(connect_card, bg="white", padx=10, pady=10)
    qr_frame.pack(anchor="center", pady=(0, 12))
    qr_label = tk.Label(qr_frame, bg="white")
    qr_label.pack()

    label(connect_card, "PHONE ADDRESS", size=8, color=muted, bold=True).pack(anchor="w", pady=(2, 5))
    url_var = tk.StringVar(value="Waiting for local server…")
    url_label = label(connect_card, "", size=10, color="#d8ccff", bg="#12151b", padx=10, pady=10,
                      wraplength=520, justify="left")
    url_label.configure(textvariable=url_var)
    url_label.pack(fill="x")

    def copy_url() -> None:
        value = url_var.get()
        if value.startswith("http"):
            root.clipboard_clear()
            root.clipboard_append(value)
            copy_button.configure(text="Copied")
            root.after(1400, lambda: copy_button.configure(text="Copy phone address"))

    copy_button = tk.Button(connect_card, text="Copy phone address", command=copy_url,
                            bg="#302842", fg="#e0d6ff", activebackground="#42365a",
                            activeforeground="white", relief="flat", padx=12, pady=8,
                            font=("Segoe UI", 9, "bold"), cursor="hand2", borderwidth=0)
    copy_button.pack(anchor="w", pady=(9, 14))
    label(connect_card, "1  Scan the QR code with your phone camera", size=9, color=text).pack(anchor="w", pady=3)
    label(connect_card, "2  Open the page in your phone's built-in browser", size=9, color=text).pack(anchor="w", pady=3)
    label(connect_card, "3  Keep this window open; focus your game to play", size=9, color=text).pack(anchor="w", pady=3)

    label(status_card, "LIVE STATUS", size=9, color=muted, bold=True).pack(anchor="w")
    phone_title = tk.StringVar(value="Waiting for phone")
    phone_detail = tk.StringVar(value="Scan the QR code to connect over Wi-Fi.")
    input_title = tk.StringVar(value="Windows keyboard/mouse")
    input_detail = tk.StringVar(value="Checking native input support…")

    def status_row(title: tk.StringVar, detail: tk.StringVar, icon: str) -> tuple[tk.Frame, tk.Label]:
        row = tk.Frame(status_card, bg=panel)
        row.pack(fill="x", pady=(13, 4))
        ico = tk.Label(row, text=icon, bg=panel_alt, fg=accent, width=3, height=1,
                       font=("Segoe UI", 13, "bold"), padx=3, pady=7)
        ico.pack(side="left", padx=(0, 10))
        copy = tk.Frame(row, bg=panel)
        copy.pack(side="left", fill="x", expand=True)
        label(copy, "", size=10, bold=True).configure(textvariable=title)
        title_label = copy.winfo_children()[-1]
        title_label.pack(anchor="w")
        label(copy, "", size=8, color=muted, wraplength=250).configure(textvariable=detail)
        detail_label = copy.winfo_children()[-1]
        detail_label.pack(anchor="w", pady=(3, 0))
        return row, ico

    phone_row, phone_icon = status_row(phone_title, phone_detail, "⌁")
    input_row, input_icon = status_row(input_title, input_detail, "⌨")

    tk.Frame(status_card, bg=line, height=1).pack(fill="x", pady=(13, 15))
    label(status_card, "LIVE INPUT MIRROR", size=9, color=muted, bold=True).pack(anchor="w")
    buttons_var = tk.StringVar(value="No phone input yet")
    label(status_card, "", size=11, color="#d9caff", bg=panel_alt, padx=10, pady=10,
          wraplength=300, justify="left").configure(textvariable=buttons_var)
    buttons_label = status_card.winfo_children()[-1]
    buttons_label.pack(fill="x", pady=(10, 12))
    sticks_var = tk.StringVar(value="Left stick    0, 0\nRight stick  0, 0")
    label(status_card, "", size=10, color=text, bg="#14171e", padx=10, pady=10,
          justify="left").configure(textvariable=sticks_var)
    sticks_label = status_card.winfo_children()[-1]
    sticks_label.pack(fill="x")
    triggers_var = tk.StringVar(value="Triggers    LT 0%     RT 0%")
    label(status_card, "", size=9, color=muted, bg="#14171e", padx=10, pady=8).configure(textvariable=triggers_var)
    triggers_label = status_card.winfo_children()[-1]
    triggers_label.pack(fill="x", pady=(8, 0))

    map_card = tk.Frame(content, bg="#1b1d25", highlightbackground=line, highlightthickness=1, padx=14, pady=11)
    map_card.pack(fill="x", pady=(14, 0))
    label(map_card, "DEFAULT GAME MAPPING", size=8, color=accent, bold=True).pack(anchor="w")
    label(map_card, "Left stick: WASD   ·   Right stick: mouse   ·   A: Space   ·   B: Ctrl   ·   X: E   ·   Y: Q\n"
          "LB: Shift   ·   RB: R   ·   LT / RT: right / left mouse click   ·   D-pad: arrows",
          size=9, color=muted, wraplength=900, justify="left").pack(anchor="w", pady=(5, 0))
    label(content, "Keyboard/mouse emulation works in games that accept those inputs; it is not a virtual gamepad.",
          size=8, color="#7f8794", wraplength=900).pack(anchor="w", pady=(10, 0))

    server = None
    server_thread: threading.Thread | None = None
    qr_image = None
    closing = False

    def close_app() -> None:
        nonlocal closing
        if closing:
            return
        closing = True
        if server is not None:
            server.should_exit = True
        root.after(100, root.destroy)

    root.protocol("WM_DELETE_WINDOW", close_app)

    def refresh() -> None:
        nonlocal qr_image
        if closing:
            return
        if server is not None and server.started:
            address = backend_main.phone_url()
            if url_var.get() != address:
                url_var.set(address)
                try:
                    qr = qrcode.make(address).resize((190, 190))
                    qr_image = ImageTk.PhotoImage(qr)
                    qr_label.configure(image=qr_image, width=190, height=190)
                except Exception as exc:
                    connected_text.set(f"QR code unavailable: {exc}")
            if backend_main.connected:
                connected_text.set("Phone connected · inputs live")
                connected_label.configure(fg=green)
                phone_title.set("Phone connected")
                phone_detail.set("Receiving controller input over your local network.")
                phone_icon.configure(fg=green)
            else:
                connected_text.set("Waiting for phone")
                connected_label.configure(fg=amber)
                phone_title.set("Waiting for phone")
                phone_detail.set("Scan the QR code from a phone on the same Wi-Fi.")
                phone_icon.configure(fg=muted)
            output = backend_main.input_output
            if output.ready:
                input_title.set("Keyboard/mouse input ready")
                input_detail.set("No virtual controller driver required.")
                input_icon.configure(fg=green)
            else:
                input_title.set("Windows input unavailable")
                input_detail.set(output.error or "This app needs Windows for input injection.")
                input_icon.configure(fg=amber)
            state = backend_main.public_state()
            names = state["buttons"]
            buttons_var.set("Pressed: " + (" · ".join(names) if names else "None"))
            axes = state["axes"]
            sticks_var.set(f"Left stick     X {axes['lx']:>4}   Y {axes['ly']:>4}\nRight stick  X {axes['rx']:>4}   Y {axes['ry']:>4}")
            triggers_var.set(f"Triggers    LT {state['lt']:>3}%     RT {state['rt']:>3}%")
        elif server is not None and not (server_thread and server_thread.is_alive()):
            error = getattr(server, "_phonepad_error", None)
            connected_text.set(f"Could not start server: {error or 'port unavailable'}")
            connected_label.configure(fg=amber)
        root.after(250, refresh)

    try:
        config = uvicorn.Config(
            backend_main.app,
            host="0.0.0.0",
            port=PORT,
            log_level="error",
            log_config=None,
            access_log=False,
        )
        server = uvicorn.Server(config)

        def run_server() -> None:
            try:
                server.run()
            except Exception as exc:
                server._phonepad_error = exc

        server_thread = threading.Thread(target=run_server, name="PhonePad LAN server", daemon=True)
        server_thread.start()
        root.after(100, refresh)
        root.mainloop()
    except Exception as exc:
        messagebox.showerror("PhonePad could not start", str(exc), parent=root)
    finally:
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=5)
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    main()
