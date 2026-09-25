"""One-command local installer and launcher for Windows, Linux, and macOS."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"


def venv_python(base: Path, platform: str = os.name) -> Path:
    return base / ("Scripts/python.exe" if platform == "nt" else "bin/python")


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args: list[str], cwd: Path = ROOT) -> None:
    print("→", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def check_requirements() -> tuple[str, str]:
    if sys.version_info < (3, 10):  # noqa: UP036 - show a useful error on older Python
        raise RuntimeError("Necesitás Python 3.10 o superior. Instalalo desde python.org.")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise RuntimeError("Necesitás Node.js 20.9 o superior con npm. Instalá la versión LTS desde nodejs.org.")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.\d+", version)
    if not match or (int(match.group(1)), int(match.group(2))) < (20, 9):
        raise RuntimeError(f"Node.js 20.9 o superior es necesario; encontré {version}.")
    return node, npm


def install_backend() -> Path:
    python = venv_python(VENV)
    stamp = VENV / ".truco-install"
    expected = fingerprint(BACKEND / "pyproject.toml")
    if python.exists() and stamp.exists() and stamp.read_text() == expected:
        print("✓ Backend instalado")
        return python
    if not python.exists():
        print("Creando entorno Python…", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    # CPU wheels keep Linux/Windows installs smaller and work without a GPU.
    # macOS uses the regular PyTorch wheel, which supports Apple's MPS backend.
    if sys.platform != "darwin":
        command([str(python), "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"])
    command([str(python), "-m", "pip", "install", "-e", str(BACKEND)])
    stamp.write_text(expected)
    print("✓ Backend listo")
    return python


def install_frontend(npm: str) -> None:
    stamp = FRONTEND / "node_modules" / ".truco-install"
    expected = fingerprint(FRONTEND / "package-lock.json")
    if stamp.exists() and stamp.read_text() == expected and (FRONTEND / "node_modules" / "next").exists():
        print("✓ Frontend instalado")
        return
    command([npm, "ci"], cwd=FRONTEND)
    stamp.write_text(expected)
    print("✓ Frontend listo")


def ensure_ports_available(api_port: int, web_port: int) -> None:
    for port in (api_port, web_port):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise RuntimeError(f"El puerto {port} está ocupado. Cerrá el programa que lo usa y reintentá.") from error


def start(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    options = {"cwd": cwd, "env": env, "start_new_session": os.name != "nt"}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(args, **options)


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)


def wait_for_server(url: str, process: subprocess.Popen, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"El servidor terminó con código {process.returncode}.")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.5)
    raise RuntimeError(f"El servidor no respondió en {url} después de {timeout} segundos.")


def run(python: Path, node: str, open_browser: bool, api_port: int = 8000, web_port: int = 3000) -> None:
    ensure_ports_available(api_port, web_port)
    api_url = f"http://127.0.0.1:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    env = os.environ.copy()
    env["API_INTERNAL_URL"] = api_url
    api = start([str(python), "-m", "uvicorn", "truco.api:app", "--host", "127.0.0.1", "--port", str(api_port)], BACKEND)
    web = None
    try:
        wait_for_server(f"{api_url}/health", api)
        web = start([node, str(FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"), "dev", "--hostname", "127.0.0.1", "--port", str(web_port)], FRONTEND, env)
        wait_for_server(web_url, web)
        print(f"\nTruco Laya listo: {web_url}")
        print("Para detenerlo, presioná Ctrl+C.\n", flush=True)
        if open_browser:
            webbrowser.open(web_url)
        while api.poll() is None and web.poll() is None:
            time.sleep(0.5)
        raise RuntimeError("Uno de los servidores se detuvo. Revisá los mensajes anteriores.")
    finally:
        if web is not None:
            stop(web)
        stop(api)


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala y ejecuta Truco Laya sin Docker")
    parser.add_argument("--install-only", action="store_true", help="Instala sin iniciar el juego")
    parser.add_argument("--no-browser", action="store_true", help="No abre el navegador automáticamente")
    parser.add_argument("--port", type=int, default=3000, help="Puerto web (por defecto: 3000)")
    parser.add_argument("--api-port", type=int, default=8000, help="Puerto API (por defecto: 8000)")
    args = parser.parse_args()
    try:
        if not (1 <= args.port <= 65535 and 1 <= args.api_port <= 65535) or args.port == args.api_port:
            raise RuntimeError("Elegí dos puertos distintos entre 1 y 65535.")
        node, npm = check_requirements()
        python = install_backend()
        install_frontend(npm)
        if not args.install_only:
            run(python, node, not args.no_browser, args.api_port, args.port)
    except KeyboardInterrupt:
        print("\nJuego detenido.")
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
