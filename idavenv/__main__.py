"""Executable entrypoint when invoked as `python -m idavenv`."""

import sys

from idavenv.cli import main

if __name__ == "__main__":
    sys.exit(main())
