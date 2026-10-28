from pathlib import Path

import pytest

from idavenv.env_backend import (
    BuiltinBackend,
    UvBackend,
    get_backend,
)


def test_get_backend_uv_preference():
    backend = get_backend(preferred="uv")
    # If uv is available on machine, it should be UvBackend
    if UvBackend.is_available():
        assert isinstance(backend, UvBackend)
    else:
        assert isinstance(backend, BuiltinBackend)


def test_get_backend_builtin():
    backend = get_backend(preferred="builtin")
    assert isinstance(backend, BuiltinBackend)


def test_uv_backend_create_venv(tmp_path):
    if not UvBackend.is_available():
        pytest.skip("uv is not available on this system")

    backend = UvBackend()
    venv_dir = tmp_path / "uv_test_venv"

    result = backend.create_venv(venv_dir)
    assert result.success is True
    assert venv_dir.exists()

    # Check pyvenv.cfg
    assert (venv_dir / "pyvenv.cfg").exists()


def test_builtin_backend_create_venv(tmp_path):
    backend = BuiltinBackend()
    venv_dir = tmp_path / "builtin_test_venv"

    result = backend.create_venv(venv_dir)
    assert result.success is True
    assert venv_dir.exists()
    assert (venv_dir / "pyvenv.cfg").exists()


def test_backend_run_command(tmp_path):
    backend = get_backend()
    venv_dir = tmp_path / "run_venv"
    backend.create_venv(venv_dir)

    result = backend.run_command(
        venv_dir, ["python", "-c", "import sys; print('HELLO_RUN'); print(sys.executable)"]
    )
    assert result.success is True
    assert "HELLO_RUN" in result.stdout
    from idavenv.paths import get_venv_python_executable
    expected_py = get_venv_python_executable(venv_dir)
    assert str(expected_py).lower() in result.stdout.lower()
    actual_py = Path(result.stdout.strip().splitlines()[-1])
    assert actual_py.resolve() == expected_py.resolve()


def test_backend_list_packages(tmp_path):
    backend = get_backend()
    venv_dir = tmp_path / "list_venv"
    backend.create_venv(venv_dir)

    result = backend.list_packages(venv_dir)
    assert result.success is True


def test_backend_empty_packages(tmp_path):
    backend = get_backend()
    venv_dir = tmp_path / "empty_pkg_venv"
    backend.create_venv(venv_dir)

    result = backend.install_packages(venv_dir, [])
    assert result.success is True


def test_uv_backend_finds_uv_in_fallback_dir(monkeypatch, tmp_path):
    import shutil
    # Simulate shutil.which("uv") returning None
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    fake_uv = tmp_path / ".local" / "bin" / ("uv.exe" if pytest.importorskip("sys").platform == "win32" else "uv")
    fake_uv.parent.mkdir(parents=True)
    fake_uv.touch()

    monkeypatch.setattr(
        "idavenv.env_backend.get_user_fallback_uv_paths", lambda: [fake_uv]
    )

    assert UvBackend.is_available() is True
    backend = UvBackend()
    assert backend._uv_path == str(fake_uv)


def test_builtin_backend_version_string_handling(tmp_path):
    backend = BuiltinBackend()
    venv_dir = tmp_path / "builtin_ver_venv"

    # When given a non-existent version string like "99.99"
    result = backend.create_venv(venv_dir, python_executable="99.99")
    assert result.success is False
    assert "99.99" in result.stderr


def test_resolve_python_cmd_matches_python3_when_version_matches(monkeypatch):
    import shutil
    import subprocess
    from idavenv.env_backend import _resolve_python_cmd

    # Simulate environment where python3.12 doesn't exist, but python3 exists and is 3.12
    def mock_which(cmd):
        if cmd == "python3":
            return "/usr/bin/python3"
        return None

    monkeypatch.setattr(shutil, "which", mock_which)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode=0, stdout="3.12\n"
        ),
    )

    resolved = _resolve_python_cmd("3.12")
    assert resolved == ["/usr/bin/python3"]


def test_safe_decode_handles_utf8_gbk_and_binary():
    from idavenv.env_backend import _safe_decode

    # 1. UTF-8 with special characters
    utf8_data = "安装成功 ⚡ ✓ 🚀".encode("utf-8")
    assert _safe_decode(utf8_data) == "安装成功 ⚡ ✓ 🚀"

    # 2. Pure GBK that is invalid UTF-8
    # 0xb6 0xaf is '动' in GBK, but invalid UTF-8 sequence
    gbk_data = "测试gbk编码".encode("gbk")
    assert "测试gbk编码" in _safe_decode(gbk_data)

    # 3. Invalid bytes that cannot decode in neither UTF-8 nor GBK
    raw_bad = b"prefix \xff\xfe\xba\xbb suffix"
    decoded = _safe_decode(raw_bad)
    assert "prefix" in decoded
    assert "suffix" in decoded


def test_backend_run_command_with_utf8_multibyte_output(tmp_path):
    backend = get_backend()
    venv_dir = tmp_path / "utf8_out_venv"
    backend.create_venv(venv_dir)

    # Print multibyte UTF-8 characters that often trigger Windows GBK UnicodeDecodeError
    cmd = [
        "python",
        "-c",
        "import sys; sys.stdout.buffer.write('安装完成 ⚡ 0xb6: \\xb6\\n'.encode('utf-8'))",
    ]
    res = backend.run_command(venv_dir, cmd)
    assert res.success is True
    assert "安装完成" in res.stdout




