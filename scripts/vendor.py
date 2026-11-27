#!/usr/bin/env python3
"""Bundle the language server's pure-Python dependencies into server/vendor.

The VS Code extension ships these so that code intelligence (jedi) and linting (pyflakes) work
out of the box; only Coconut itself needs to be installed in the user's environment. Packages
the user has installed themselves take precedence over the bundled copies.

Usage: python3 scripts/vendor.py
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "server", "vendor")

# pure-Python, MIT-licensed; keep in sync with server/requirements.txt
REQUIREMENTS = ["jedi>=0.19.1", "parso>=0.8.4", "pyflakes>=3.1"]


def main():
    if os.path.isdir(VENDOR):
        shutil.rmtree(VENDOR)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
        "--no-compile", "--only-binary", ":all:", "--target", VENDOR,
    ] + REQUIREMENTS)
    # drop things that aren't needed at runtime
    for name in os.listdir(VENDOR):
        path = os.path.join(VENDOR, name)
        if name == "bin" or name == "__pycache__":
            shutil.rmtree(path)
    for dirpath, dirnames, filenames in os.walk(VENDOR):
        for d in list(dirnames):
            if d in ("__pycache__", "test", "tests"):
                shutil.rmtree(os.path.join(dirpath, d))
                dirnames.remove(d)
    # jedi bundles typeshed's third-party stubs (~25MB) and django-stubs; without them jedi just
    # analyzes the installed packages' sources directly, so keep only the standard library stubs
    third_party = os.path.join(VENDOR, "jedi", "third_party")
    for sub in (os.path.join("typeshed", "stubs"), "django-stubs"):
        path = os.path.join(third_party, sub)
        if os.path.isdir(path):
            shutil.rmtree(path)
            os.makedirs(path)
    with open(os.path.join(VENDOR, "README.md"), "w") as f:
        f.write("Bundled at package time by scripts/vendor.py; not checked in. Licenses are in the *.dist-info folders.\n")
    print("vendored " + ", ".join(REQUIREMENTS) + " into " + os.path.relpath(VENDOR, ROOT))


if __name__ == "__main__":
    main()
