"""Coconut language server: compiler diagnostics and Python-level code intelligence for Coconut.

Only the Coconut compiler itself (pip install coconut) is required. Code intelligence (hover,
completion, go to definition, ...) uses jedi and linting uses pyflakes; both are used from the
current environment if installed, and otherwise from the copies bundled in server/vendor
(when present, as in the VS Code extension).
"""

import os
import sys

__version__ = "0.1.0"

_VENDOR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vendor",
    "modern" if sys.version_info >= (3, 11) else "compat",
)
if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    # appended, so packages installed in the user's environment take precedence
    sys.path.append(_VENDOR_DIR)
