"""idavenv: Cross-platform automated IDAPython virtualenv management powered by uv."""

__version__ = "0.1.1"

from idavenv.core import IDAVirtualenvManager, EnvStatus
from idavenv.paths import (
    get_ida_user_dir,
    get_venv_site_packages,
    get_venv_python_executable,
    get_venv_bin_dir,
)
from idavenv.env_backend import (
    get_backend,
    EnvBackend,
    UvBackend,
    BuiltinBackend,
    ExecutionResult,
)
from idavenv.hook_template import (
    generate_hook_code,
    inject_hook,
    remove_hook,
    has_hook,
)

__all__ = [
    "__version__",
    "IDAVirtualenvManager",
    "EnvStatus",
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
