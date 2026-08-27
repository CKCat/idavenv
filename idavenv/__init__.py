"""idavenv: Cross-platform automated IDAPython virtualenv management powered by uv."""

__version__ = "0.1.3"

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
    get_ida_user_dir,
    get_venv_bin_dir,
    get_venv_python_executable,
    get_venv_site_packages,
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
