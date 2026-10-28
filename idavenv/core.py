"""Core orchestrator for IDAPython virtualenv lifecycle management."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from idavenv.env_backend import (
    EnvBackend,
    ExecutionResult,
    get_backend,
)
from idavenv.hook_template import (
    has_hook,
    inject_hook,
    remove_hook,
)
from idavenv.paths import (
    detect_ida_python_path,
    get_ida_user_dir,
    get_venv_python_executable,
    get_venv_site_packages,
)


@dataclass
class EnvStatus:
    """Detailed status report of IDAPython virtualenv setup."""

    ida_dir: Path
    rc_file: Path
    venv_dir: Path
    venv_exists: bool
    is_hooked: bool
    backend_name: str
    site_packages: List[Path]
    python_executable: Optional[Path]
    detected_ida_python: Optional[Union[Path, str]] = None
    is_ida9_native: bool = False


class IDAVirtualenvManager:
    """Manager class coordinating virtualenv creation, hook management and package operations."""

    def __init__(
        self,
        ida_dir: Optional[Path] = None,
        venv_dir: Optional[Path] = None,
        backend_name: str = "uv",
    ):
        self.ida_dir = (
            Path(ida_dir).expanduser().resolve() if ida_dir else get_ida_user_dir()
        )
        self.rc_file = self.ida_dir / "idapythonrc.py"
        self.venv_dir = (
            Path(venv_dir).expanduser().resolve() if venv_dir else self.ida_dir / "venv"
        )
        self.backend: EnvBackend = get_backend(preferred=backend_name)

    def init(
        self,
        python_executable: Optional[str] = None,
        system_site_packages: bool = False,
        force: bool = False,
    ) -> ExecutionResult:
        """Initializes or re-creates the IDAPython virtual environment and links it to IDA.

        Args:
            python_executable: Path or name of python interpreter to base venv on.
            system_site_packages: Whether to grant access to system site-packages.
            force: If True, removes existing venv directory before re-creating.

        Returns:
            ExecutionResult indicating success or failure.
        """
        self.ida_dir.mkdir(parents=True, exist_ok=True)

        if self.venv_dir.exists() and force:
            if self.venv_dir.is_symlink():
                self.venv_dir.unlink()
            else:
                shutil.rmtree(self.venv_dir)

        if not self.venv_dir.exists():
            base_py = python_executable
            if not base_py:
                detected_py = detect_ida_python_path()
                if detected_py:
                    base_py = str(detected_py)

            create_res = self.backend.create_venv(
                venv_dir=self.venv_dir,
                python_executable=base_py,
                system_site_packages=system_site_packages,
            )
            if not create_res.success:
                return create_res

        # Inject hook into idapythonrc.py
        inject_hook(self.rc_file, self.venv_dir)

        return ExecutionResult(
            success=True,
            returncode=0,
            stdout=f"IDAPython virtualenv successfully initialized at {self.venv_dir} using {self.backend.name()}",
            stderr="",
        )

    def status(self) -> EnvStatus:
        """Returns the current state and health of the environment."""
        venv_exists = self.venv_dir.exists()
        is_hooked = has_hook(self.rc_file)
        site_packages = get_venv_site_packages(self.venv_dir) if venv_exists else []
        python_executable = (
            get_venv_python_executable(self.venv_dir) if venv_exists else None
        )

        env_override = os.environ.get("IDAPYTHON_VENV_EXECUTABLE")
        is_ida9_native = False
        if env_override and python_executable:
            try:
                is_ida9_native = (
                    Path(env_override).expanduser().resolve()
                    == python_executable.resolve()
                )
            except Exception:
                pass

        return EnvStatus(
            ida_dir=self.ida_dir,
            rc_file=self.rc_file,
            venv_dir=self.venv_dir,
            venv_exists=venv_exists,
            is_hooked=is_hooked,
            backend_name=self.backend.name(),
            site_packages=site_packages,
            python_executable=python_executable,
            detected_ida_python=detect_ida_python_path(),
            is_ida9_native=is_ida9_native,
        )

    def install_packages(
        self,
        packages: Optional[List[str]] = None,
        requirement_files: Optional[List[str]] = None,
        upgrade: bool = False,
    ) -> ExecutionResult:
        """Installs Python packages or requirement files into the linked IDAPython virtualenv."""
        if not self.venv_dir.exists():
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Virtualenv does not exist at {self.venv_dir}. Run init first.",
            )
        return self.backend.install_packages(
            self.venv_dir,
            packages=packages,
            requirement_files=requirement_files,
            upgrade=upgrade,
        )

    def list_packages(self) -> ExecutionResult:
        """Lists packages installed in the virtual environment."""
        if not self.venv_dir.exists():
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Virtualenv does not exist at {self.venv_dir}.",
            )
        return self.backend.list_packages(self.venv_dir)

    def remove_hook(self) -> bool:
        """Removes the virtualenv hook from idapythonrc.py."""
        return remove_hook(self.rc_file)

    def clean_venv(self) -> bool:
        """Removes the virtualenv directory on disk."""
        if self.venv_dir.exists():
            shutil.rmtree(self.venv_dir)
            return True
        return False

    def uninstall(self, remove_venv: bool = False) -> bool:
        """Unlinks the virtualenv by removing hook from idapythonrc.py and optionally deletes venv.

        Args:
            remove_venv: If True, completely deletes the virtual environment directory.

        Returns:
            True if hook was removed or virtualenv was deleted.
        """
        hook_removed = self.remove_hook()
        venv_cleaned = self.clean_venv() if remove_venv else False
        return hook_removed or venv_cleaned

    def run_command(self, command: List[str]) -> ExecutionResult:
        """Runs an arbitrary command inside the virtual environment context."""
        if not self.venv_dir.exists():
            return ExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Virtualenv does not exist at {self.venv_dir}.",
            )
        return self.backend.run_command(self.venv_dir, command)
