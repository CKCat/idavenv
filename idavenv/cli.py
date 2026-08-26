"""Command-line interface for idavenv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from idavenv import __version__
from idavenv.core import IDAVirtualenvManager


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="idavenv",
        description="Automated cross-platform IDAPython virtualenv management powered by uv.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Common parent parser for shared arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--ida-dir",
        type=str,
        help="Custom IDA Pro user directory (defaults to $IDAUSR or system default).",
    )
    common_parser.add_argument(
        "--venv-dir",
        type=str,
        help="Custom virtualenv directory (defaults to <IDAUSR>/venv).",
    )
    common_parser.add_argument(
        "--backend",
        choices=["uv", "builtin"],
        default="uv",
        help="Virtualenv backend engine (default: uv).",
    )

    # 1. init
    init_parser = subparsers.add_parser(
        "init",
        parents=[common_parser],
        help="Create virtualenv and link to IDA via idapythonrc.py",
    )
    init_parser.add_argument(
        "--python",
        type=str,
        help="Base Python interpreter for virtualenv (e.g. 3.11, /usr/bin/python3).",
    )
    init_parser.add_argument(
        "--system-site-packages",
        action="store_true",
        help="Give virtual environment access to system site-packages.",
    )
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-creation of virtualenv even if it already exists.",
    )

    # 2. info / status
    subparsers.add_parser(
        "info",
        parents=[common_parser],
        help="Display IDA and IDAPython virtualenv status.",
    )

    # 3. install
    install_parser = subparsers.add_parser(
        "install",
        parents=[common_parser],
        help="Install Python packages into IDAPython virtualenv.",
    )
    install_parser.add_argument(
        "packages",
        nargs="*",
        help="Package names or requirement specs to install.",
    )
    install_parser.add_argument(
        "-r",
        "--requirement",
        action="append",
        dest="requirements",
        default=[],
        help="Install from the given requirements file (can be used multiple times).",
    )
    install_parser.add_argument(
        "--upgrade",
        "-U",
        action="store_true",
        help="Upgrade specified packages to the newest available version.",
    )

    # 4. list
    subparsers.add_parser(
        "list",
        parents=[common_parser],
        help="List packages installed in IDAPython virtualenv.",
    )

    # 5. run
    run_parser = subparsers.add_parser(
        "run",
        parents=[common_parser],
        help="Run a command inside IDAPython virtualenv environment.",
    )
    run_parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command to execute inside the virtualenv context.",
    )

    # 6. uninstall
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        parents=[common_parser],
        help="Remove IDAPython virtualenv hook and optionally delete venv.",
    )
    uninstall_parser.add_argument(
        "--clean-venv",
        action="store_true",
        help="Also remove the virtualenv directory on disk.",
    )

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    ida_dir = (
        Path(parsed_args.ida_dir) if getattr(parsed_args, "ida_dir", None) else None
    )
    venv_dir = (
        Path(parsed_args.venv_dir) if getattr(parsed_args, "venv_dir", None) else None
    )
    backend_name = getattr(parsed_args, "backend", "uv")

    manager = IDAVirtualenvManager(
        ida_dir=ida_dir,
        venv_dir=venv_dir,
        backend_name=backend_name,
    )

    if parsed_args.command == "init":
        print(
            f"[*] Initializing IDAPython virtualenv using '{backend_name}' backend..."
        )
        res = manager.init(
            python_executable=parsed_args.python,
            system_site_packages=parsed_args.system_site_packages,
            force=parsed_args.force,
        )
        if res.success:
            print(f"[+] {res.stdout}")
            print(f"[+] IDA configuration: {manager.rc_file}")
            print(
                "[+] Done! IDAPython will now automatically load this virtualenv on IDA startup."
            )
            return 0
        else:
            print(
                f"[-] Failed to initialize virtualenv:\n{res.stderr}", file=sys.stderr
            )
            return res.returncode or 1

    elif parsed_args.command == "info":
        status = manager.status()
        print("=== IDAPython Virtualenv Status ===")
        print(f"IDA User Directory  : {status.ida_dir}")
        print(f"Hook File Path      : {status.rc_file}")
        print(f"Hook Installed      : {'Yes' if status.is_hooked else 'No'}")
        print(f"Virtualenv Path     : {status.venv_dir}")
        print(f"Virtualenv Exists   : {'Yes' if status.venv_exists else 'No'}")
        print(f"Active Backend      : {status.backend_name}")
        if status.python_executable:
            print(f"Python Executable   : {status.python_executable}")
        if status.site_packages:
            print("Site-Packages Dirs  :")
            for sp in status.site_packages:
                print(f"  - {sp}")
        return 0

    elif parsed_args.command == "install":
        packages = parsed_args.packages or []
        requirements = parsed_args.requirements or []
        if not packages and not requirements:
            print(
                "[-] Error: Please specify at least one package or a requirements file via -r.",
                file=sys.stderr,
            )
            return 1

        items = []
        if packages:
            items.append(f"packages: {', '.join(packages)}")
        if requirements:
            items.append(f"files: {', '.join(requirements)}")
        print(f"[*] Installing {', '.join(items)} ...")

        res = manager.install_packages(
            packages=packages,
            requirement_files=requirements,
            upgrade=parsed_args.upgrade,
        )
        if res.success:
            if res.stdout:
                print(res.stdout)
            print("[+] Packages installed successfully.")
            return 0
        else:
            print(f"[-] Installation failed:\n{res.stderr}", file=sys.stderr)
            return res.returncode or 1

    elif parsed_args.command == "list":
        res = manager.list_packages()
        if res.success:
            print(res.stdout)
            return 0
        else:
            print(f"[-] Failed to list packages:\n{res.stderr}", file=sys.stderr)
            return res.returncode or 1

    elif parsed_args.command == "run":
        if not parsed_args.cmd:
            print("[-] Error: No command specified to run.", file=sys.stderr)
            return 1
        res = manager.run_command(parsed_args.cmd)
        if res.stdout:
            sys.stdout.write(res.stdout)
        if res.stderr:
            sys.stderr.write(res.stderr)
        return res.returncode

    elif parsed_args.command == "uninstall":
        removed = manager.uninstall(remove_venv=parsed_args.clean_venv)
        if removed:
            print("[+] Hook successfully removed from idapythonrc.py.")
        else:
            print("[*] No active hook found in idapythonrc.py.")
        if parsed_args.clean_venv:
            print("[+] Virtualenv directory cleaned.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
