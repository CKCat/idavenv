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
        venv_dir, ["python", "-c", "import sys; print('HELLO_RUN')"]
    )
    assert result.success is True
    assert "HELLO_RUN" in result.stdout


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
