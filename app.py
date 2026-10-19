"""PhonePad launcher.

Used both from source (``python app.py``) and as the entry point of the
packaged ``PhonePad.exe``.  Before the server starts it makes sure the
ViGEmBus driver is present and offers to install the copy bundled with the
executable, so a fresh PC only needs this one file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def bundle_dir() -> Path:
    """Folder holding bundled data: ``_MEIPASS`` when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def _driver_msi() -> Path | None:
    """Locate the ViGEmBus installer shipped inside the bundle."""
    candidates: list[Path] = []
    try:
        import vgamepad

        candidates.append(
            Path(vgamepad.__file__).resolve().parent
            / "win"
            / "vigem"
            / "install"
            / "x64"
            / "ViGEmBusSetup_x64.msi"
        )
    except Exception:
        pass
    candidates.append(
        bundle_dir() / "vgamepad" / "win" / "vigem" / "install" / "x64" / "ViGEmBusSetup_x64.msi"
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _install_driver(msi: Path) -> bool:
    """Run the MSI elevated. True when msiexec reports success."""
    inner = f'/i "{msi}" /qb /norestart'
    script = (
        "$p = Start-Process -FilePath msiexec.exe -ArgumentList '"
        + inner
        + "' -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            timeout=300,
        )
    except Exception as exc:
        print(f"[!] Could not start the installer: {type(exc).__name__}: {exc}")
        return False
    return proc.returncode in (0, 3010)


def ensure_driver() -> None:
    """Explain / install ViGEmBus when it is missing."""
    from backend.pad import driver_installed

    if driver_installed():
        return

    line = "=" * 64
    print(line)
    print("  PhonePad needs the ViGEmBus virtual gamepad driver")
    print(line)
    print("  Windows uses it to create the controller that games see.")
    print("  It is a one-time install from the official ViGEm project.")
    print()

    msi = _driver_msi()
    if msi is None:
        print("  The bundled installer was not found.")
        print("  Download it from https://github.com/nefarius/ViGEmBus/releases")
        print("  install it, then run PhonePad again.")
        print(line)
        return

    try:
        answer = input("  Install it now? This asks for administrator rights [Y/n] ").strip().lower()
    except (EOFError, OSError):
        answer = "n"
    if answer not in ("", "y", "yes"):
        print("  Skipped. Games will not see a controller until it is installed.")
        print(line)
        return

    print("  Installing... (a Windows admin prompt may appear)")
    if _install_driver(msi):
        print("  ViGEmBus installed.")
        print("  If Windows asks to reboot, do that before playing.")
    else:
        print("  [!] The installer did not complete. Try running PhonePad as")
        print("      administrator, or install ViGEmBus manually from the link above.")
    print(line)


def main() -> None:
    ensure_driver()

    # Import late: the server module creates the virtual pad on import, and
    # that must happen after a possible driver install.
    from backend.main import main as run_server

    run_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback

        traceback.print_exc()
        try:
            input("\nPhonePad stopped unexpectedly. Press Enter to close...")
        except (EOFError, OSError):
            pass
        raise SystemExit(1)
