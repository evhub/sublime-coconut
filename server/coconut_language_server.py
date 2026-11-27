#!/usr/bin/env python3
"""Entry point for the Coconut language server (and its CLI); see coconut_ls/cli.py.

Run with the Python interpreter that has Coconut installed:

    python3 server/coconut_language_server.py            # LSP over stdio
    python3 server/coconut_language_server.py --help     # other commands (check, hover, docs, mcp, ...)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coconut_ls.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
