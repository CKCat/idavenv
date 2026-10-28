"""Template generator and injector for idapythonrc.py virtualenv hook."""

from __future__ import annotations

import re
from pathlib import Path

HOOK_START_MARKER = "# >>> IDAPython Virtualenv Hook (managed by idavenv) >>>"
HOOK_END_MARKER = "# <<< IDAPython Virtualenv Hook (managed by idavenv) <<<"

LEGACY_HOOK_START_MARKER = (
    "# >>> IDAPython Virtualenv Hook (managed by idavirtualenv) >>>"
)
LEGACY_HOOK_END_MARKER = (
    "# <<< IDAPython Virtualenv Hook (managed by idavirtualenv) <<<"
)

HOOK_TEMPLATE = """{start_marker}
def _activate_idapython_virtualenv():
    import builtins
    import os
    import sys
    import site
    from pathlib import Path

    _SENTINEL = "_idapython_venv_initialized"
    if getattr(builtins, _SENTINEL, False):
        return

    # Allow dynamic override via environment variable
    custom_env = os.environ.get("IDAPYTHON_VENV")
    if custom_env:
        venv_root = Path(custom_env).expanduser().resolve()
    else:
        venv_root = Path(r"{default_venv_path}").resolve()

    if not venv_root.exists():
        return

    curr_py_ver = f"python{{sys.version_info.major}}.{{sys.version_info.minor}}"
    site_dirs = []

    # Windows style: venv/Lib/site-packages
    win_site = venv_root / "Lib" / "site-packages"
    if win_site.exists():
        site_dirs.append(win_site)

    # POSIX version-specific style
    posix_site = venv_root / "lib" / curr_py_ver / "site-packages"
    if posix_site.exists() and posix_site not in site_dirs:
        site_dirs.append(posix_site)

    posix_site64 = venv_root / "lib64" / curr_py_ver / "site-packages"
    if posix_site64.exists() and posix_site64 not in site_dirs:
        site_dirs.append(posix_site64)

    local_site = venv_root / "local" / "lib" / curr_py_ver / "site-packages"
    if local_site.exists() and local_site not in site_dirs:
        site_dirs.append(local_site)

    def _register_dll_dirs(v_root, s_dirs):
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            _DLL_HANDLES = "_idapython_dll_handles"
            if not hasattr(builtins, _DLL_HANDLES):
                setattr(builtins, _DLL_HANDLES, [])
            handles = getattr(builtins, _DLL_HANDLES)

            def _safe_add(p):
                try:
                    h = os.add_dll_directory(str(p))
                    handles.append(h)
                except Exception:
                    pass

            b_dir = v_root / ("Scripts" if os.name == "nt" else "bin")
            if b_dir.exists():
                _safe_add(b_dir)
            for sd in s_dirs:
                if sd.exists():
                    _safe_add(sd)
                    try:
                        for sub in sd.iterdir():
                            if sub.is_dir():
                                sub_lib = sub / "lib"
                                if sub_lib.is_dir():
                                    _safe_add(sub_lib)
                                sub_bin = sub / "bin"
                                if sub_bin.is_dir():
                                    _safe_add(sub_bin)
                    except Exception:
                        pass

    # If already activated in current process (e.g. IDA 9.0+ native detect_venv()), ensure DLL paths and exit
    if Path(sys.prefix).resolve() == venv_root:
        _register_dll_dirs(venv_root, site_dirs)
        setattr(builtins, _SENTINEL, True)
        return

    # Check pyvenv.cfg for version mismatch (especially critical on Windows where Lib/site-packages lacks version in path)
    cfg_file = venv_root / "pyvenv.cfg"
    venv_py_ver = None
    if cfg_file.exists():
        try:
            for line in cfg_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("version_info") or line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip()
                        ver_nums = [p.strip() for p in val.split(".") if p.strip().isdigit()]
                        if len(ver_nums) >= 2:
                            venv_py_ver = f"python{{ver_nums[0]}}.{{ver_nums[1]}}"
                            break
        except Exception:
            pass

    if venv_py_ver and venv_py_ver != curr_py_ver:
        try:
            print(
                f"[!] IDAPython Warning: Python version mismatch (IDA is {{curr_py_ver}}, "
                f"but venv was created for {{venv_py_ver}})."
            )
            print(
                f"    Run 'idavenv init --python {{sys.version_info.major}}.{{sys.version_info.minor}} -f' to fix."
            )
        except Exception:
            pass

    # Check for version mismatch on POSIX if no exact site-packages found
    if not site_dirs:
        other_vers = []
        lib_dir = venv_root / "lib"
        if lib_dir.exists():
            for sub in lib_dir.iterdir():
                if sub.is_dir() and sub.name.startswith("python"):
                    other_vers.append(sub.name)
                    cand = sub / "site-packages"
                    if cand.exists():
                        site_dirs.append(cand)

        if other_vers and curr_py_ver not in other_vers and not venv_py_ver:
            try:
                print(
                    f"[!] IDAPython Warning: Python version mismatch (IDA is {{curr_py_ver}}, "
                    f"but venv was created for {{', '.join(other_vers)}})."
                )
                print(
                    f"    Run 'idavenv init --python {{sys.version_info.major}}.{{sys.version_info.minor}} -f' to fix."
                )
            except Exception:
                pass

    # Save original sys.path length to identify newly added directories
    orig_path_len = len(sys.path)

    for s_dir in site_dirs:
        site.addsitedir(str(s_dir))

    # Boost priority: Move newly added venv paths near front of sys.path (after position 0)
    if len(sys.path) > orig_path_len:
        newly_added = sys.path[orig_path_len:]
        del sys.path[orig_path_len:]
        # Insert after script directory (index 1) in reverse order to preserve addsitedir sequence
        for p in reversed(newly_added):
            if p not in sys.path[:1]:
                sys.path.insert(1, p)

    # Update runtime metadata
    sys.prefix = str(venv_root)
    sys.exec_prefix = str(venv_root)
    os.environ["VIRTUAL_ENV"] = str(venv_root)

    # Update PATH with venv bin/Scripts
    bin_dir = venv_root / ("Scripts" if os.name == "nt" else "bin")
    if bin_dir.exists():
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(bin_dir) + os.pathsep + current_path

        # Windows Python 3.8+ DLL directory resolution for C extensions (e.g. z3, unicorn)
        _register_dll_dirs(venv_root, site_dirs)

    setattr(builtins, _SENTINEL, True)
    try:
        print(f"[+] IDAPython: Virtual environment activated -> {{venv_root}}")
    except Exception:
        pass

_activate_idapython_virtualenv()
{end_marker}
"""


def generate_hook_code(venv_path: Path) -> str:
    """Generates the full hook source code with markers and absolute path."""
    posix_path = Path(venv_path).resolve().as_posix()
    return (
        HOOK_TEMPLATE.format(
            start_marker=HOOK_START_MARKER,
            end_marker=HOOK_END_MARKER,
            default_venv_path=posix_path,
        ).strip()
        + "\n"
    )


def has_hook(rc_file: Path) -> bool:
    """Checks whether the given idapythonrc.py already contains our hook."""
    if not rc_file.exists():
        return False
    content = rc_file.read_text(encoding="utf-8")
    return (HOOK_START_MARKER in content and HOOK_END_MARKER in content) or (
        LEGACY_HOOK_START_MARKER in content and LEGACY_HOOK_END_MARKER in content
    )


def _strip_legacy_hook(content: str) -> str:
    """Removes any legacy idavirtualenv hook markers and code."""
    legacy_pattern = re.compile(
        re.escape(LEGACY_HOOK_START_MARKER)
        + r".*?"
        + re.escape(LEGACY_HOOK_END_MARKER)
        + r"\n?",
        re.DOTALL,
    )
    return legacy_pattern.sub("", content)


def inject_hook(rc_file: Path, venv_path: Path) -> bool:
    """Injects or updates the virtualenv activation hook in idapythonrc.py.

    Preserves any existing user customizations and cleans legacy blocks.

    Args:
        rc_file: Path to idapythonrc.py.
        venv_path: Path to the target virtualenv directory.

    Returns:
        True if the file was modified or created.
    """
    rc_file.parent.mkdir(parents=True, exist_ok=True)
    new_hook_code = generate_hook_code(venv_path)

    if not rc_file.exists():
        rc_file.write_text(new_hook_code, encoding="utf-8")
        return True

    existing_content = rc_file.read_text(encoding="utf-8")

    # Clean legacy idavirtualenv hook block if present
    cleaned_content = _strip_legacy_hook(existing_content)

    pattern = re.compile(
        re.escape(HOOK_START_MARKER) + r".*?" + re.escape(HOOK_END_MARKER) + r"\n?",
        re.DOTALL,
    )

    if pattern.search(cleaned_content):
        updated_content = pattern.sub(lambda _: new_hook_code, cleaned_content)
    else:
        # Append to the end of existing file
        if cleaned_content and not cleaned_content.endswith("\n"):
            cleaned_content += "\n"
        updated_content = (
            cleaned_content + ("\n" if cleaned_content else "") + new_hook_code
        )

    rc_file.write_text(updated_content, encoding="utf-8")
    return True


def remove_hook(rc_file: Path) -> bool:
    """Safely removes the virtualenv hook block from idapythonrc.py.

    Args:
        rc_file: Path to idapythonrc.py.

    Returns:
        True if hook was found and removed, False otherwise.
    """
    if not rc_file.exists():
        return False

    existing_content = rc_file.read_text(encoding="utf-8")

    # Strip both legacy and new hooks
    content_without_legacy = _strip_legacy_hook(existing_content)
    pattern = re.compile(
        re.escape(HOOK_START_MARKER) + r".*?" + re.escape(HOOK_END_MARKER) + r"\n?",
        re.DOTALL,
    )

    had_hook = pattern.search(content_without_legacy) is not None or (
        content_without_legacy != existing_content
    )
    if not had_hook:
        return False

    updated_content = pattern.sub("", content_without_legacy).strip()
    if updated_content:
        rc_file.write_text(updated_content + "\n", encoding="utf-8")
    else:
        # If file is empty after removal, remove or write empty
        rc_file.write_text("", encoding="utf-8")

    return True
