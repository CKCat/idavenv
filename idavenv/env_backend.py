"""Environment backends for creating virtualenvs and installing packages (uv / builtin)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from idavenv.paths import get_venv_bin_dir, get_venv_python_executable


def get_user_fallback_uv_paths() -> List[Path]:
    """Returns candidate fallback paths for uv binary in user directories."""
    home = Path.home()
    is_win = sys.platform == "win32"
    exe_name = "uv.exe" if is_win else "uv"
    return [
        home / ".local" / "bin" / exe_name,
        home / ".cargo" / "bin" / exe_name,
    ]


@dataclass
class ExecutionResult:
    """Represents the result of an environment or package execution."""

    success: bool
    returncode: int
    stdout: str
    stderr: str


class EnvBackend(ABC):
    """Abstract interface for virtual environment management."""

    @abstractmethod
    def name(self) -> str:
        """Returns the backend name."""
        pass

    @abstractmethod
    def create_venv(
        self,
        venv_dir: Path,
        python_executable: Optional[str] = None,
        system_site_packages: bool = False,
    ) -> ExecutionResult:
        """Creates a virtual environment at target path."""
        pass

    @abstractmethod
    def install_packages(
        self,
        venv_dir: Path,
        packages: Optional[List[str]] = None,
        requirement_files: Optional[List[str]] = None,
        upgrade: bool = False,
    ) -> ExecutionResult:
        """Installs packages into the target virtual environment."""
        pass

    @abstractmethod
    def list_packages(self, venv_dir: Path) -> ExecutionResult:
        """Lists packages installed in the virtual environment."""
        pass

    def run_command(
        self,
        venv_dir: Path,
        command: List[str],
        env_vars: Optional[dict] = None,
    ) -> ExecutionResult:
        """Runs a command inside the virtual environment context."""
        bin_dir = get_venv_bin_dir(venv_dir)
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_dir.resolve())
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        if env_vars:
            env.update(env_vars)

        # Resolve executable inside virtualenv bin_dir to prevent Windows PATH shadowing
        actual_cmd = list(command)
        if actual_cmd:
            exe = actual_cmd[0]
            cand = bin_dir / exe
            cand_exe = bin_dir / f"{exe}.exe"
            if cand.is_file():
                actual_cmd[0] = str(cand)
            elif sys.platform == "win32" and cand_exe.is_file():
                actual_cmd[0] = str(cand_exe)

        try:
            proc = subprocess.run(
                actual_cmd,
                cwd=str(venv_dir),
                env=env,
                capture_output=True,
                text=True,
            )
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )


class UvBackend(EnvBackend):
    """Virtualenv and package management backend powered by uv."""

    def __init__(self, uv_path: Optional[str] = None):
        if uv_path:
            self._uv_path = uv_path
        else:
            found = shutil.which("uv")
            if not found:
                for cand in get_user_fallback_uv_paths():
                    if cand.exists():
                        found = str(cand)
                        break
            self._uv_path = found or "uv"

    @classmethod
    def is_available(cls) -> bool:
        """Checks if uv is installed and accessible in PATH or user fallback dirs."""
        if shutil.which("uv") is not None:
            return True
        for cand in get_user_fallback_uv_paths():
            if cand.exists():
                return True
        return False

    def name(self) -> str:
        return "uv"

    def create_venv(
        self,
        venv_dir: Path,
        python_executable: Optional[str] = None,
        system_site_packages: bool = False,
    ) -> ExecutionResult:
        venv_dir = Path(venv_dir).resolve()
        cmd = [self._uv_path, "venv", str(venv_dir)]
        if python_executable:
            cmd.extend(["--python", python_executable])
        if system_site_packages:
            cmd.append("--system-site-packages")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )

    def install_packages(
        self,
        venv_dir: Path,
        packages: Optional[List[str]] = None,
        requirement_files: Optional[List[str]] = None,
        upgrade: bool = False,
    ) -> ExecutionResult:
        pkg_list = packages or []
        req_list = requirement_files or []
        if not pkg_list and not req_list:
            return ExecutionResult(success=True, returncode=0, stdout="", stderr="")

        python_exe = get_venv_python_executable(venv_dir)
        cmd = [self._uv_path, "pip", "install", "--python", str(python_exe)]
        if upgrade:
            cmd.append("--upgrade")
        for req in req_list:
            cmd.extend(["-r", str(req)])
        cmd.extend(pkg_list)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )

    def list_packages(self, venv_dir: Path) -> ExecutionResult:
        python_exe = get_venv_python_executable(venv_dir)
        cmd = [self._uv_path, "pip", "list", "--python", str(python_exe)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )


class BuiltinBackend(EnvBackend):
    """Virtualenv and package management backend using Python's standard library venv."""

    def name(self) -> str:
        return "builtin"

    def create_venv(
        self,
        venv_dir: Path,
        python_executable: Optional[str] = None,
        system_site_packages: bool = False,
    ) -> ExecutionResult:
        venv_dir = Path(venv_dir).resolve()
        try:
            if python_executable:
                cmd = [python_executable, "-m", "venv", str(venv_dir)]
                if system_site_packages:
                    cmd.append("--system-site-packages")
                proc = subprocess.run(cmd, capture_output=True, text=True)
                return ExecutionResult(
                    success=(proc.returncode == 0),
                    returncode=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                )
            else:
                try:
                    builder = venv.EnvBuilder(
                        system_site_packages=system_site_packages,
                        with_pip=True,
                    )
                    builder.create(str(venv_dir))
                except SystemExit:
                    # On Debian/Ubuntu without python3-venv, with_pip=True calls sys.exit(1)
                    builder = venv.EnvBuilder(
                        system_site_packages=system_site_packages,
                        with_pip=False,
                    )
                    builder.create(str(venv_dir))
                    return ExecutionResult(
                        success=True,
                        returncode=0,
                        stdout=f"Virtualenv created at {venv_dir} (without pip: ensurepip/python3-venv unavailable)",
                        stderr="Warning: ensurepip is unavailable; packages cannot be installed via pip without installing pip first.",
                    )

                return ExecutionResult(
                    success=True,
                    returncode=0,
                    stdout=f"Virtualenv created at {venv_dir}",
                    stderr="",
                )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )

    def install_packages(
        self,
        venv_dir: Path,
        packages: Optional[List[str]] = None,
        requirement_files: Optional[List[str]] = None,
        upgrade: bool = False,
    ) -> ExecutionResult:
        pkg_list = packages or []
        req_list = requirement_files or []
        if not pkg_list and not req_list:
            return ExecutionResult(success=True, returncode=0, stdout="", stderr="")

        python_exe = get_venv_python_executable(venv_dir)
        cmd = [str(python_exe), "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        for req in req_list:
            cmd.extend(["-r", str(req)])
        cmd.extend(pkg_list)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )

    def list_packages(self, venv_dir: Path) -> ExecutionResult:
        python_exe = get_venv_python_executable(venv_dir)
        cmd = [str(python_exe), "-m", "pip", "list"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return ExecutionResult(
                success=(proc.returncode == 0),
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            )


def get_backend(preferred: str = "uv") -> EnvBackend:
    """Returns the requested or best available environment backend.

    Args:
        preferred: Preferred backend ('uv' or 'builtin').

    Returns:
        Instance of EnvBackend.
    """
    pref = preferred.strip().lower()
    if pref == "uv":
        if UvBackend.is_available():
            return UvBackend()
        # Fallback to builtin if uv is not available
        return BuiltinBackend()
    return BuiltinBackend()
