"""idavenv: Cross-platform automated IDAPython virtualenv management powered by uv."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("idavenv")
except PackageNotFoundError:
    __version__ = "unknown"

from idavenv.core import EnvStatus, IDAVirtualenvManager
from idavenv.env_backend import (
    BuiltinBackend,
    EnvBackend,
    ExecutionResult,
    UvBackend,
    get_backend,
)
from idavenv.hook_template import (
    generate_hook_code,
    has_hook,
    inject_hook,
    remove_hook,
)
from idavenv.paths import (
    detect_ida_python_path,
    get_ida_user_dir,
    get_venv_bin_dir,
    get_venv_python_executable,
    get_venv_site_packages,
)

__all__ = [
    "__version__",
    "IDAVirtualenvManager",
    "EnvStatus",
    "detect_ida_python_path",
    "get_ida_user_dir",
    "get_venv_site_packages",
    "get_venv_python_executable",
    "get_venv_bin_dir",
    "get_backend",
    "EnvBackend",
    "UvBackend",
    "BuiltinBackend",
    "ExecutionResult",
    "generate_hook_code",
    "inject_hook",
    "remove_hook",
    "has_hook",
]
