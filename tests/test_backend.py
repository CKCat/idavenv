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
    expected_py = get_venv_python_executable(venv_dir).resolve()
    assert str(expected_py).lower() in result.stdout.lower()


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

