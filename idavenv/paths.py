"""Cross-platform path resolution for IDA Pro user directory and Python virtualenv."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Union


def _extract_py_version_from_dll(dll_path: Path) -> Optional[str]:
    """Extracts Python major.minor version from a python DLL or shared library filename (e.g. python314.dll -> 3.14, libpython3.10.so -> 3.10)."""
    name = dll_path.name.lower()
    # 1. Match dotted versions common in Linux/macOS shared libraries (e.g. libpython3.10.so, libpython3.12.so.1.0, libpython3.11.dylib)
    m_dotted = re.search(r"python(\d+)\.(\d+)", name)
    if m_dotted:
        return f"{m_dotted.group(1)}.{m_dotted.group(2)}"

    # 2. Match compact versions common in Windows DLLs (e.g. python314.dll, python310.dll)
    stem = dll_path.stem.lower()
    m_compact = re.search(r"python(\d)(\d+)", stem)
    if m_compact:
        return f"{m_compact.group(1)}.{m_compact.group(2)}"

    # If it is python3.dll, extract real version from Windows PE version resource
    if stem == "python3" and sys.platform == "win32" and dll_path.exists():
        try:
            import ctypes
            import struct
            from ctypes import wintypes

            size = ctypes.windll.version.GetFileVersionInfoSizeW(str(dll_path), None)
            if size > 0:
                res = ctypes.create_string_buffer(size)
                if ctypes.windll.version.GetFileVersionInfoW(
                    str(dll_path), 0, size, res
                ):
                    ptr = ctypes.c_void_p()
                    u_len = wintypes.UINT()
                    if ctypes.windll.version.VerQueryValueW(
                        res, "\\", ctypes.byref(ptr), ctypes.byref(u_len)
                    ):
                        buf = (ctypes.c_char * 8).from_address(ptr.value + 8)
                        ms, _ = struct.unpack("II", buf.raw)
                        major = ms >> 16
                        minor = ms & 0xFFFF
                        if major > 0:
                            return f"{major}.{minor}"
        except Exception:
            pass

    return None


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


def get_venv_python_version(venv_dir: Path) -> Optional[str]:
    """Reads the Python major.minor version of an existing virtual environment.

    Inspects pyvenv.cfg for 'version_info' or 'version', or checks lib/pythonX.Y.

    Args:
        venv_dir: Root path of the virtual environment.

    Returns:
        Version string (e.g. '3.12') or None.
    """
    resolved_venv = Path(venv_dir).resolve()
    cfg_file = resolved_venv / "pyvenv.cfg"
    if cfg_file.exists():
        try:
            content = cfg_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("version_info") or line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip()
                        m = re.search(r"(\d+)\.(\d+)", val)
                        if m:
                            return f"{m.group(1)}.{m.group(2)}"
        except Exception:
            pass

    # Fallback to check lib/pythonX.Y on POSIX or similar layouts
    lib_dir = resolved_venv / "lib"
    if lib_dir.exists():
        for sub in lib_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("python"):
                m = re.search(r"python(\d+)\.(\d+)", sub.name)
                if m:
                    return f"{m.group(1)}.{m.group(2)}"

    return None


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


def detect_ida_python_path(system: Optional[str] = None) -> Optional[Union[Path, str]]:
    """Detects the host Python executable or version string configured for IDA Pro.

    Resolution order:
    1. IDA_PYTHON_EXE or IDA_PYTHON_DLL environment variable (explicit IDA host Python).
    2. IDAPYTHON_VENV_EXECUTABLE environment variable (IDA 9.0+ venv override).
    3. Windows Registry (HKCU/HKLM -> Software\\Hex-Rays\\IDA -> Python3TargetDLL).

    Returns:
        Path to Python executable or version string (e.g. '3.14') if detected, else None.
    """
    target_system = (system or sys.platform).lower()

    # 1. Explicit IDA Python host environment variables
    val_exe = os.environ.get("IDA_PYTHON_EXE")
    if val_exe:
        p = Path(val_exe).expanduser().resolve()
        if p.exists():
            return p

    val_dll = os.environ.get("IDA_PYTHON_DLL")
    if val_dll:
        p = Path(val_dll).expanduser().resolve()
        if p.exists():
            cand_exe = p.parent / "python.exe"
            if cand_exe.exists():
                return cand_exe
            ver = _extract_py_version_from_dll(p)
            return ver if ver else None

    # 2. IDAPYTHON_VENV_EXECUTABLE
    val_venv = os.environ.get("IDAPYTHON_VENV_EXECUTABLE")
    if val_venv:
        p = Path(val_venv).expanduser().resolve()
        if p.exists():
            return p

    # 3. Windows registry
    if target_system.startswith("win"):
        try:
            import winreg

            subkeys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Hex-Rays\IDA"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Hex-Rays\IDA"),
            ]
            for hkey, subkey in subkeys:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        val, _ = winreg.QueryValueEx(key, "Python3TargetDLL")
                        if val:
                            dll_path = Path(val).expanduser().resolve()
                            if dll_path.exists():
                                cand_exe = dll_path.parent / "python.exe"
                                if cand_exe.exists():
                                    return cand_exe
                                cand_exe_parent = dll_path.parent.parent / "python.exe"
                                if cand_exe_parent.exists():
                                    return cand_exe_parent
                                ver = _extract_py_version_from_dll(dll_path)
                                return ver if ver else None
                except OSError:
                    continue
        except ImportError:
            pass

    return None

