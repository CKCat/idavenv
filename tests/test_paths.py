import sys
from pathlib import Path

from idavenv.paths import (
    detect_ida_python_path,
    get_ida_user_dir,
    get_venv_bin_dir,
    get_venv_python_executable,
    get_venv_python_version,
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


def test_detect_ida_python_from_env(monkeypatch, tmp_path):
    fake_exe = tmp_path / "python.exe"
    fake_exe.touch()
    monkeypatch.setenv("IDAPYTHON_VENV_EXECUTABLE", str(fake_exe))

    detected = detect_ida_python_path()
    assert detected == fake_exe.resolve()


def test_detect_ida_python_returns_none_when_nothing(monkeypatch):
    monkeypatch.delenv("IDAPYTHON_VENV_EXECUTABLE", raising=False)
    monkeypatch.delenv("IDA_PYTHON_EXE", raising=False)
    monkeypatch.delenv("IDA_PYTHON_DLL", raising=False)

    # Mock winreg if on windows or pass system="linux"
    detected = detect_ida_python_path(system="linux")
    assert detected is None


def test_detect_ida_python_dll_fallback_version(monkeypatch, tmp_path):
    dll_file = tmp_path / "python314.dll"
    dll_file.touch()
    monkeypatch.setenv("IDA_PYTHON_DLL", str(dll_file))

    # There is no python.exe nearby, should extract version "3.14" instead of returning dll Path
    detected = detect_ida_python_path()
    assert detected == "3.14"


def test_init_exports_detect_ida_python():
    import idavenv
    assert hasattr(idavenv, "detect_ida_python_path")
    assert "detect_ida_python_path" in idavenv.__all__


def test_extract_py_version_from_dll_variants(tmp_path):
    from idavenv.paths import _extract_py_version_from_dll

    # 1. Standard python314.dll
    f1 = tmp_path / "python314.dll"
    assert _extract_py_version_from_dll(f1) == "3.14"

    # 2. python310.dll
    f2 = tmp_path / "python310.dll"
    assert _extract_py_version_from_dll(f2) == "3.10"

    # 3. Non-python dll
    f3 = tmp_path / "other.dll"
    assert _extract_py_version_from_dll(f3) is None

    # 4. python3.dll on Windows with PE version resource
    cand_python3_dlls = list(Path.home().glob("AppData/Roaming/uv/python/*/python3.dll"))
    if cand_python3_dlls and cand_python3_dlls[0].exists():
        ver = _extract_py_version_from_dll(cand_python3_dlls[0])
        assert ver is not None


def test_get_venv_python_version(tmp_path):
    venv = tmp_path / "venv"
    venv.mkdir()
    assert get_venv_python_version(venv) is None

    cfg = venv / "pyvenv.cfg"
    cfg.write_text("version = 3.11.8\n", encoding="utf-8")
    assert get_venv_python_version(venv) == "3.11"

    cfg.write_text("version_info = 3.12.3.final.0\n", encoding="utf-8")
    assert get_venv_python_version(venv) == "3.12"


def test_detect_ida_python_path_prioritizes_host_exe(monkeypatch, tmp_path):
    host_exe = tmp_path / "host_python.exe"
    host_exe.touch()
    venv_exe = tmp_path / "venv_python.exe"
    venv_exe.touch()

    monkeypatch.setenv("IDA_PYTHON_EXE", str(host_exe))
    monkeypatch.setenv("IDAPYTHON_VENV_EXECUTABLE", str(venv_exe))

    # IDA_PYTHON_EXE should have higher priority than IDAPYTHON_VENV_EXECUTABLE
    detected = detect_ida_python_path()
    assert detected == host_exe.resolve()





