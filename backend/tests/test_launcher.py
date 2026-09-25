import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("truco_launcher", Path(__file__).resolve().parents[2] / "run.py")
assert spec and spec.loader
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_virtualenv_python_paths_are_portable():
    base = Path("virtualenv")
    assert launcher.venv_python(base, "nt") == base / "Scripts/python.exe"
    assert launcher.venv_python(base, "posix") == base / "bin/python"


def test_frontend_installer_reuses_matching_lockfile(monkeypatch, tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    lock = frontend / "package-lock.json"
    lock.write_text("first")
    monkeypatch.setattr(launcher, "FRONTEND", frontend)
    installs = []

    def fake_command(args, cwd):
        installs.append(args)
        (frontend / "node_modules" / "next").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(launcher, "command", fake_command)
    launcher.install_frontend("npm")
    launcher.install_frontend("npm")
    assert installs == [["npm", "ci"]]

    lock.write_text("updated")
    launcher.install_frontend("npm")
    assert installs == [["npm", "ci"], ["npm", "ci"]]
