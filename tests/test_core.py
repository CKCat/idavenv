from idavenv.core import IDAVirtualenvManager
from idavenv.hook_template import has_hook


def test_manager_init_default(tmp_path, monkeypatch):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    monkeypatch.setenv("IDAUSR", str(ida_dir))

    manager = IDAVirtualenvManager(ida_dir=ida_dir, backend_name="builtin")
    result = manager.init(force=True)

    assert result.success is True
    assert (ida_dir / "venv").exists()
    assert (ida_dir / "idapythonrc.py").exists()
    assert has_hook(ida_dir / "idapythonrc.py") is True


def test_manager_init_custom_venv_path(tmp_path):
    ida_dir = tmp_path / "ida_user"
    custom_venv = tmp_path / "my_custom_venv"
    ida_dir.mkdir()

    manager = IDAVirtualenvManager(
        ida_dir=ida_dir, venv_dir=custom_venv, backend_name="builtin"
    )
    result = manager.init()

    assert result.success is True
    assert custom_venv.exists()
    assert has_hook(ida_dir / "idapythonrc.py") is True

    status = manager.status()
    assert status.is_hooked is True
    assert status.venv_exists is True
    assert status.venv_dir == custom_venv.resolve()


def test_manager_uninstall(tmp_path):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    manager = IDAVirtualenvManager(ida_dir=ida_dir, backend_name="builtin")
    manager.init()

    assert has_hook(ida_dir / "idapythonrc.py") is True

    uninstalled = manager.uninstall(remove_venv=False)
    assert uninstalled is True
    assert has_hook(ida_dir / "idapythonrc.py") is False
    assert (ida_dir / "venv").exists()

    # Uninstall with remove_venv
    manager.init()
    uninstalled = manager.uninstall(remove_venv=True)
    assert uninstalled is True
    assert not (ida_dir / "venv").exists()


def test_manager_list_and_run(tmp_path):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    manager = IDAVirtualenvManager(ida_dir=ida_dir, backend_name="uv")
    manager.init()

    list_res = manager.list_packages()
    assert list_res.success is True

    run_res = manager.run_command(["python", "-c", "print('RUN_OK')"])
    assert run_res.success is True
    assert "RUN_OK" in run_res.stdout


def test_manager_operations_before_init(tmp_path):
    ida_dir = tmp_path / "non_existing_ida_dir"
    manager = IDAVirtualenvManager(ida_dir=ida_dir)

    assert manager.list_packages().success is False
    assert manager.install_packages(["some_pkg"]).success is False
    assert manager.run_command(["python"]).success is False


def test_manager_init_uses_detected_ida_python(tmp_path, monkeypatch):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    fake_python = tmp_path / "ida_python.exe"
    fake_python.touch()

    # Mock detect_ida_python_path
    monkeypatch.setattr(
        "idavenv.core.detect_ida_python_path", lambda: fake_python
    )

    manager = IDAVirtualenvManager(ida_dir=ida_dir, backend_name="builtin")
    recorded_python = []

    def fake_create_venv(venv_dir, python_executable=None, system_site_packages=False):
        recorded_python.append(python_executable)
        from idavenv.env_backend import ExecutionResult
        return ExecutionResult(success=True, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(manager.backend, "create_venv", fake_create_venv)
    manager.init()

    assert recorded_python == [str(fake_python)]


def test_uninstall_returns_true_if_venv_removed_even_without_hook(tmp_path):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    venv_dir = ida_dir / "venv"
    venv_dir.mkdir()

    manager = IDAVirtualenvManager(ida_dir=ida_dir, venv_dir=venv_dir)
    # Notice: idapythonrc.py does not exist or has no hook
    res = manager.uninstall(remove_venv=True)
    assert res is True
    assert not venv_dir.exists()


def test_env_status_ida9_native_detection(tmp_path, monkeypatch):
    ida_dir = tmp_path / "ida_user"
    ida_dir.mkdir()
    manager = IDAVirtualenvManager(ida_dir=ida_dir, backend_name="builtin")
    manager.init()

    # When IDAPYTHON_VENV_EXECUTABLE is not set
    monkeypatch.delenv("IDAPYTHON_VENV_EXECUTABLE", raising=False)
    status = manager.status()
    assert status.is_ida9_native is False

    # When IDAPYTHON_VENV_EXECUTABLE points to venv python executable
    monkeypatch.setenv("IDAPYTHON_VENV_EXECUTABLE", str(status.python_executable))
    status2 = manager.status()
    assert status2.is_ida9_native is True


def test_init_fails_if_existing_venv_has_different_python_without_force(tmp_path):
    ida_dir = tmp_path / "ida_mismatch_init"
    ida_dir.mkdir()
    venv_dir = ida_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("version_info = 3.14.7\n", encoding="utf-8")

    manager = IDAVirtualenvManager(
        ida_dir=ida_dir, venv_dir=venv_dir, backend_name="builtin"
    )
    res = manager.init(python_executable="3.12", force=False)
    assert res.success is False
    assert "Existing virtualenv" in res.stderr
    assert "--force" in res.stderr


def test_status_reports_venv_python_version(tmp_path):
    ida_dir = tmp_path / "ida_status_ver"
    ida_dir.mkdir()
    venv_dir = ida_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("version_info = 3.12.4\n", encoding="utf-8")

    manager = IDAVirtualenvManager(
        ida_dir=ida_dir, venv_dir=venv_dir, backend_name="builtin"
    )
    status = manager.status()
    assert status.venv_python_version == "3.12"




