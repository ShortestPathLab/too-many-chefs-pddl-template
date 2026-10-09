"""Find and open a window for the visualiser."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time

# Maximum wait for a native window to start.
WINDOW_STARTUP_GRACE = 4.0


def is_wsl() -> bool:
    """Are we a Linux process inside WSL?"""
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease") as release:
            return "microsoft" in release.read().lower()
    except OSError:
        return False


def native_window_reason() -> str | None:
    """Return ``None`` when pywebview can open a window, otherwise the reason."""
    if importlib.util.find_spec("webview") is None:
        return "pywebview is not installed (uv sync --extra native)"
    if sys.platform.startswith("linux"):
        if not (importlib.util.find_spec("gi") or importlib.util.find_spec("qtpy")):
            return "pywebview has no GTK or Qt backend on this machine"
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return "there is no display attached to this machine"
    return None


# Chromium browsers that can open an app window on Windows.
_WINDOWS_BROWSER_APPS = ("msedge.exe", "chrome.exe")

# Fallback paths when the registry has no entry.
_WINDOWS_BROWSER_FALLBACKS = (
    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
)


def _run_windows(args: list[str], timeout: float = 15) -> str:
    """Run a Windows command from WSL and return stdout."""
    try:
        # Use a path that Windows can represent.
        finished = subprocess.run(
            args,
            cwd="/mnt/c",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return finished.stdout.replace("\r", "")
    except OSError, subprocess.SubprocessError:
        return ""


def _windows_env(name: str, default: str) -> str:
    """Read a Windows environment variable from WSL."""
    value = _run_windows(["cmd.exe", "/c", f"echo %{name}%"]).strip()
    return value if value and not value.startswith("%") else default


def find_windows_browser() -> str | None:
    """Return the installed Windows Edge or Chrome executable."""
    for browser in _WINDOWS_BROWSER_APPS:
        for hive in ("HKLM", "HKCU"):
            key = (
                rf"{hive}\SOFTWARE\Microsoft\Windows\CurrentVersion"
                rf"\App Paths\{browser}"
            )
            for line in _run_windows(["reg.exe", "query", key, "/ve"]).splitlines():
                if "REG_SZ" not in line:
                    continue
                windows_path = line.split("REG_SZ", 1)[1].strip()
                path = _run_windows(["wslpath", "-u", windows_path]).strip()
                if path and os.path.isfile(path):
                    return path

    return next((p for p in _WINDOWS_BROWSER_FALLBACKS if os.path.isfile(p)), None)


def open_wsl_window(
    url: str,
    *,
    size: tuple[int, int],
) -> tuple[subprocess.Popen[bytes] | None, str | None]:
    """Open ``url`` in a Windows app window from WSL.

    Return the process and ``None`` on success, or ``None`` and a reason on
    failure. A dedicated profile keeps the process attached to this window.
    """
    browser = find_windows_browser()
    if browser is None:
        return None, "no Windows Edge or Chrome was found to open a window with"

    profile = _windows_env("TEMP", "C:\\Windows\\Temp") + "\\too-many-chefs-window"
    width, height = size

    try:
        window = subprocess.Popen(
            [
                browser,
                f"--app={url}",
                f"--user-data-dir={profile}",
                f"--window-size={width},{height}",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        return None, str(error)

    deadline = time.monotonic() + WINDOW_STARTUP_GRACE
    while time.monotonic() < deadline:
        if window.poll() is not None:
            return (
                None,
                f"the Windows window exited straight away (code {window.returncode})",
            )
        time.sleep(0.1)
    return window, None


def open_native_window(
    url: str,
    *,
    title: str,
    size: tuple[int, int],
    alive_url: str,
) -> tuple[subprocess.Popen[bytes] | None, str | None]:
    """Open ``url`` in a pywebview window run by a fresh interpreter.

    Return the process and ``None`` on success, or ``None`` and a reason on
    failure. A visualiser running beside a training loop uses this instead of
    NiceGUI's native mode, which interrupts the main thread when its window
    closes. A fresh interpreter, rather than multiprocessing, keeps the child
    from importing the caller's script again.

    ``window.close()`` does not reliably close a pywebview window, so the child
    polls ``alive_url`` and closes itself once the server stops answering.
    """
    reason = native_window_reason()
    if reason is not None:
        return None, reason

    width, height = size
    code = (
        "import threading, time, urllib.request, webview\n"
        f"window = webview.create_window({title!r}, {url!r},"
        f" width={width}, height={height})\n"
        "def watch():\n"
        "    misses = 0\n"
        "    while misses < 3:\n"
        "        time.sleep(1)\n"
        "        try:\n"
        f"            urllib.request.urlopen({alive_url!r}, timeout=2).read()\n"
        "            misses = 0\n"
        "        except Exception:\n"
        "            misses += 1\n"
        "    window.destroy()\n"
        "threading.Thread(target=watch, daemon=True).start()\n"
        "webview.start()\n"
    )
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        return None, str(error)

    # A missing display or backend fails straight away.
    deadline = time.monotonic() + WINDOW_STARTUP_GRACE
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raw = process.stderr.read() if process.stderr is not None else b""
            error = raw.decode(errors="replace").strip()
            return None, (
                error.splitlines()[-1]
                if error
                else f"the window exited straight away (code {process.returncode})"
            )
        time.sleep(0.1)
    return process, None
