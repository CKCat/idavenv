import subprocess
import sys

from idavenv.env_backend import BuiltinBackend
from idavenv.hook_template import generate_hook_code


def test_hook_runtime_execution(tmp_path):
    # 1. Create a real venv with builtin backend
    venv_dir = tmp_path / "runtime_venv"
    BuiltinBackend().create_venv(venv_dir)

    # 2. Generate hook code pointing to this venv
    hook_code = generate_hook_code(venv_path=venv_dir)

    # 3. Create a test runner script simulating IDA Python startup
    runner_script = tmp_path / "simulate_ida.py"
    runner_script.write_text(
        f"""
import sys
import os

# Define mock idaapi if needed
class MockIdaApi:
    @staticmethod
    def get_user_idadir():
        return r"{tmp_path}"

sys.modules["idaapi"] = MockIdaApi()

# Run the hook code twice to test idempotency and sentinel
{hook_code}

# Run it again (simulating opening another IDB in the same IDA session)
{hook_code}

# Verify assertions inside the runtime
import builtins
assert getattr(builtins, "_idapython_venv_initialized", False) is True
print("VENV_PREFIX_OK" if sys.prefix == str(r"{venv_dir.resolve()}") else "VENV_PREFIX_FAIL")
print("SUCCESS")
""",
        encoding="utf-8",
    )

    # 4. Execute with system python
    proc = subprocess.run(
        [sys.executable, str(runner_script)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"Error running hook: {proc.stderr}"
    assert "SUCCESS" in proc.stdout
    assert "VENV_PREFIX_OK" in proc.stdout


def test_hook_sys_path_priority(tmp_path):
    venv_dir = tmp_path / "prio_venv"
    if sys.platform == "win32":
        site_dir = venv_dir / "Lib" / "site-packages"
    else:
        site_dir = (
            venv_dir
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
    site_dir.mkdir(parents=True)

    hook_code = generate_hook_code(venv_path=venv_dir)

    runner_script = tmp_path / "test_prio.py"
    runner_script.write_text(
        f"""
import sys

# Prepend dummy script path to sys.path (preserve standard library paths)
sys.path.insert(0, "/dummy/ida/scripts")

{hook_code}

# Verify that venv site-packages is near the front of sys.path, before standard global paths
site_str = str(r"{site_dir.resolve()}")
assert site_str in sys.path
idx = sys.path.index(site_str)
assert idx <= 1, f"Expected site-packages at front, got index {{idx}} in {{sys.path}}"
print("PRIORITY_OK")
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(runner_script)], capture_output=True, text=True
    )
    assert proc.returncode == 0, f"Failed: {proc.stderr}"
    assert "PRIORITY_OK" in proc.stdout


def test_hook_version_mismatch_warning(tmp_path):
    venv_dir = tmp_path / "mismatch_venv"
    # Create fake venv with python2.7 directory structure
    fake_site = venv_dir / "lib" / "python2.7" / "site-packages"
    fake_site.mkdir(parents=True)
    (venv_dir / "pyvenv.cfg").touch()

    hook_code = generate_hook_code(venv_path=venv_dir)

    runner_script = tmp_path / "test_mismatch.py"
    runner_script.write_text(
        f"""
import sys
{hook_code}
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(runner_script)], capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert "Python version mismatch" in proc.stdout or "Warning" in proc.stdout


def test_hook_retains_dll_handles_on_windows(tmp_path):
    venv_dir = tmp_path / "dll_venv"
    site_dir = venv_dir / "Lib" / "site-packages"
    site_dir.mkdir(parents=True)
    scripts_dir = venv_dir / "Scripts"
    scripts_dir.mkdir(parents=True)

    hook_code = generate_hook_code(venv_path=venv_dir)

    runner_script = tmp_path / "test_dll_handle.py"
    runner_script.write_text(
        f"""
import sys
import builtins
import os

{hook_code}

if os.name == "nt" and hasattr(os, "add_dll_directory"):
    handles = getattr(builtins, "_idapython_dll_handles", None)
    assert handles is not None, "_idapython_dll_handles should exist in builtins"
    assert len(handles) > 0, "DLL handles list should not be empty"
print("DLL_HANDLES_OK")
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(runner_script)], capture_output=True, text=True
    )
    assert proc.returncode == 0, f"Failed: {proc.stderr}\n{proc.stdout}"
    assert "DLL_HANDLES_OK" in proc.stdout


def test_hook_version_mismatch_windows_pyvenv_cfg(tmp_path):
    venv_dir = tmp_path / "win_mismatch_venv"
    site_dir = venv_dir / "Lib" / "site-packages"
    site_dir.mkdir(parents=True)
    (venv_dir / "pyvenv.cfg").write_text(
        "home = C:\\Fake\\Python310\nversion_info = 3.10.0\n", encoding="utf-8"
    )

    hook_code = generate_hook_code(venv_path=venv_dir)

    runner_script = tmp_path / "test_win_mismatch.py"
    runner_script.write_text(
        f"""
import sys
{hook_code}
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(runner_script)], capture_output=True, text=True
    )
    assert proc.returncode == 0
    # Current runner is not 3.10, so it should warn about version mismatch
    if (sys.version_info.major, sys.version_info.minor) != (3, 10):
        assert "Python version mismatch" in proc.stdout, f"Expected mismatch warning, got: {proc.stdout}"

