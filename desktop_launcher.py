# SEZDocs - Copyright (c) 2026 Mohammad Reza Sebzari
# Licensed under the GNU General Public License v3.0 (see LICENSE).
"""
SEZDocs Desktop Launcher
========================
Runs the Streamlit app as a background server and opens it in a native
desktop window (via pywebview) instead of a browser tab - so it looks
and feels like a normal Windows application, not a website.

The Streamlit server runs as a separate subprocess (not an in-process
thread) because Streamlit registers a SIGTERM handler on startup, and
that only works from the main thread of a process - running it inside
a background thread raises "signal only works in main thread".

This is the file PyInstaller packages into SEZDocs.exe. See
BUILD_WINDOWS_EXE.md for the exact build command.
"""

import os
import sys
import subprocess
import socket
import time
import atexit

import webview


def get_base_dir() -> str:
    """Works both as a normal script and as a PyInstaller-frozen exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port(start: int = 8501) -> int:
    port = start
    while port < start + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start


def start_streamlit(app_path: str, port: int) -> subprocess.Popen:
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", app_path,
            "--server.port", str(port),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.runOnSave", "false",
        ],
        cwd=os.path.dirname(app_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def wait_for_server(port: int, proc: subprocess.Popen, timeout: float = 60.0):
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            return False  # the server process died on its own
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.25)
    return False


def main():
    base_dir = get_base_dir()
    app_path = os.path.join(base_dir, "app.py")
    port = find_free_port()

    proc = start_streamlit(app_path, port)
    atexit.register(lambda: proc.poll() is None and proc.terminate())

    if not wait_for_server(port, proc):
        print("SEZDocs failed to start - the local server never came up.")
        sys.exit(1)

    try:  # let the Report button save PDFs from inside the desktop window
        webview.settings["ALLOW_DOWNLOADS"] = True
    except Exception:
        pass

    webview.create_window(
        "SEZDocs - Offline Document Search",
        f"http://127.0.0.1:{port}",
        width=1280,
        height=860,
        min_size=(900, 600),
    )
    webview.start()

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
