"""Cross-platform path resolution for IDA Pro user directory and Python virtualenv."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional


def get_ida_user_dir(system: Optional[str] = None) -> Path:
    """Resolves the default IDA Pro user directory (IDAUSR) across platforms.

    Resolution order:
    1. $IDAUSR environment variable (takes the first path if multiple).
    2. OS-specific default path:
       - Windows: %APPDATA%/Hex-Rays/IDA Pro
       - Linux: ~/.idapro
       - macOS: ~/.idapro (or ~/Library/Application Support/Hex-Rays/IDA Pro)

    Args:
        system: Target operating system ('windows', 'linux', 'darwin'). Defaults to sys.platform.

    Returns:
        Path object pointing to the resolved IDA user directory.
    """
    env_idausr = os.environ.get("IDAUSR")
    if env_idausr:
        # IDAUSR can contain multiple paths separated by ';' (Windows) or ':' (POSIX)
        separator = (
            ";"
            if (system == "windows" or (system is None and sys.platform == "win32"))
            else os.pathsep
        )
        candidate_paths = [
            Path(p.strip()).expanduser().resolve()
            for p in env_idausr.split(separator)
            if p.strip()
        ]
        # Prefer the path that already contains idapythonrc.py
        for cand in candidate_paths:
            if (cand / "idapythonrc.py").exists():
                return cand

        if candidate_paths:
            return candidate_paths[0]

    target_system = (system or sys.platform).lower()

    if target_system.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata)
        else:
            base_dir = Path.home() / "AppData" / "Roaming"
        return (base_dir / "Hex-Rays" / "IDA Pro").resolve()

    if target_system == "darwin":
        # IDA on macOS primarily uses ~/.idapro
        default_dir = Path.home() / ".idapro"
        return default_dir.resolve()

    # Default to Linux / Unix (~/.idapro)
    return (Path.home() / ".idapro").resolve()


def get_venv_site_packages(venv_dir: Path) -> List[Path]:
    """Finds all candidate site-packages directories in a virtual environment.

    Args:
        venv_dir: Root path of the Python virtual environment.

    Returns:
        List of Path objects pointing to existing site-packages directories.
    """
    resolved_venv = Path(venv_dir).resolve()
    candidates: List[Path] = []
    resolved_set: set = set()

    def _add_candidate(path: Path) -> None:
        real = path.resolve()
        if real not in resolved_set:
            resolved_set.add(real)
            candidates.append(path)

    # Windows style: venv/Lib/site-packages
    win_site = resolved_venv / "Lib" / "site-packages"
    if win_site.exists():
        _add_candidate(win_site)

    # POSIX style: venv/lib/pythonX.Y/site-packages
    lib_dir = resolved_venv / "lib"
    if lib_dir.exists():
        for sub in lib_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("python"):
                site_dir = sub / "site-packages"
                if site_dir.exists():
                    _add_candidate(site_dir)

    # POSIX 64-bit style: venv/lib64/pythonX.Y/site-packages
    lib64_dir = resolved_venv / "lib64"
    if lib64_dir.exists():
        for sub in lib64_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("python"):
                site_dir = sub / "site-packages"
                if site_dir.exists():
                    _add_candidate(site_dir)

    # Fallback to local lib if exists
    local_lib = resolved_venv / "local" / "lib"
    if local_lib.exists():
        for sub in local_lib.iterdir():
            if sub.is_dir() and sub.name.startswith("python"):
                site_dir = sub / "site-packages"
                if site_dir.exists():
                    _add_candidate(site_dir)

    return candidates


def get_venv_bin_dir(venv_dir: Path, system: Optional[str] = None) -> Path:
    """Returns the executable directory for a virtual environment (bin or Scripts).

    Args:
        venv_dir: Root path of the Python virtual environment.
        system: Target operating system ('windows', 'linux', 'darwin').

    Returns:
        Path pointing to bin (POSIX) or Scripts (Windows).
    """
    target_system = (system or sys.platform).lower()
    resolved_venv = Path(venv_dir).resolve()

    if target_system.startswith("win"):
        return (resolved_venv / "Scripts").resolve()
    return (resolved_venv / "bin").resolve()


def get_venv_python_executable(venv_dir: Path, system: Optional[str] = None) -> Path:
    """Returns the Python executable path within a virtual environment.

    Args:
        venv_dir: Root path of the Python virtual environment.
        system: Target operating system.

    Returns:
        Path to python executable (python.exe or python).
    """
    target_system = (system or sys.platform).lower()
    bin_dir = get_venv_bin_dir(venv_dir, system=target_system)

    if target_system.startswith("win"):
        return bin_dir / "python.exe"
    return bin_dir / "python"
