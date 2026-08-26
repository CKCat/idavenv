import subprocess
import sys


def test_package_main_invocation():
    proc = subprocess.run(
        [sys.executable, "-m", "idavenv", "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "usage:" in proc.stdout
