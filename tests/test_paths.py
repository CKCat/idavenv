import sys
from pathlib import Path

from idavenv.paths import (
    get_ida_user_dir,
    get_venv_bin_dir,
    get_venv_python_executable,
    get_venv_site_packages,
)


def test_get_ida_user_dir_from_env(monkeypatch, tmp_path):
    custom_dir = tmp_path / "custom_ida_dir"
    custom_dir.mkdir()
    monkeypatch.setenv("IDAUSR", str(custom_dir))

    resolved = get_ida_user_dir()
    assert resolved == custom_dir.resolve()


def test_get_ida_user_dir_from_env_multiple_paths(monkeypatch, tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    path_sep = ";" if sys.platform == "win32" else ":"
    monkeypatch.setenv("IDAUSR", f"{dir1}{path_sep}{dir2}")

    resolved = get_ida_user_dir()
    assert resolved == dir1.resolve()


def test_get_ida_user_dir_from_env_multiple_paths_prefers_existing_rc(
    monkeypatch, tmp_path
):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    # Create idapythonrc.py in dir2
    (dir2 / "idapythonrc.py").write_text("# existing rc", encoding="utf-8")

    path_sep = ";" if sys.platform == "win32" else ":"
    monkeypatch.setenv("IDAUSR", f"{dir1}{path_sep}{dir2}")

    resolved = get_ida_user_dir()
    assert resolved == dir2.resolve()


def test_get_ida_user_dir_linux_default(monkeypatch, tmp_path):
    monkeypatch.delenv("IDAUSR", raising=False)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    target = get_ida_user_dir(system="linux")
    assert target == (fake_home / ".idapro").resolve()


def test_get_ida_user_dir_windows_default(monkeypatch, tmp_path):
    monkeypatch.delenv("IDAUSR", raising=False)
    fake_appdata = tmp_path / "AppData" / "Roaming"
    fake_appdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(fake_appdata))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    target = get_ida_user_dir(system="windows")
    assert target == (fake_appdata / "Hex-Rays" / "IDA Pro").resolve()


def test_get_ida_user_dir_macos_default(monkeypatch, tmp_path):
    monkeypatch.delenv("IDAUSR", raising=False)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    target = get_ida_user_dir(system="darwin")
    assert target == (fake_home / ".idapro").resolve()


def test_get_venv_site_packages_posix(tmp_path):
    venv_dir = tmp_path / "test_venv"
    site_pkg = venv_dir / "lib" / "python3.10" / "site-packages"
    site_pkg.mkdir(parents=True)

    found = get_venv_site_packages(venv_dir)
    assert site_pkg.resolve() in [p.resolve() for p in found]


def test_get_venv_site_packages_windows(tmp_path):
    venv_dir = tmp_path / "test_venv_win"
    site_pkg = venv_dir / "Lib" / "site-packages"
    site_pkg.mkdir(parents=True)

    found = get_venv_site_packages(venv_dir)
    assert site_pkg.resolve() in [p.resolve() for p in found]


def test_get_venv_python_executable_posix(tmp_path):
    venv_dir = tmp_path / "test_venv"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    python_bin = bin_dir / "python"
    python_bin.touch(mode=0o755)

    res = get_venv_python_executable(venv_dir, system="linux")
    assert res == python_bin.resolve()


def test_get_venv_python_executable_windows(tmp_path):
    venv_dir = tmp_path / "test_venv_win"
    scripts_dir = venv_dir / "Scripts"
    scripts_dir.mkdir(parents=True)
    python_exe = scripts_dir / "python.exe"
    python_exe.touch()

    res = get_venv_python_executable(venv_dir, system="windows")
    assert res == python_exe.resolve()


def test_get_venv_bin_dir(tmp_path):
    venv_dir = tmp_path / "test_venv"
    assert get_venv_bin_dir(venv_dir, system="linux") == (venv_dir / "bin").resolve()
    assert (
        get_venv_bin_dir(venv_dir, system="windows") == (venv_dir / "Scripts").resolve()
    )


def test_get_venv_site_packages_lib64(tmp_path):
    venv_dir = tmp_path / "test_venv_lib64"
    site_pkg = venv_dir / "lib64" / "python3.10" / "site-packages"
    site_pkg.mkdir(parents=True)

    found = get_venv_site_packages(venv_dir)
    assert site_pkg.resolve() in [p.resolve() for p in found]


def test_get_venv_site_packages_local_lib(tmp_path):
    venv_dir = tmp_path / "test_venv_local"
    site_pkg = venv_dir / "local" / "lib" / "python3.10" / "site-packages"
    site_pkg.mkdir(parents=True)

    found = get_venv_site_packages(venv_dir)
    assert site_pkg.resolve() in [p.resolve() for p in found]
