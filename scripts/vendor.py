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

# Pure-Python, MIT-licensed packages, bundled in two sets since recent releases dropped old Pythons.
# server/coconut_ls/__init__.py picks the set matching the running interpreter.
BUNDLES = {
    # (directory, python version to resolve for): requirements
    ("modern", "3.11"): ["jedi>=0.20.1", "parso>=0.8.7", "pyflakes>=4.1"],
    ("compat", "3.8"): ["jedi>=0.19.2,<0.20", "parso>=0.8.4", "pyflakes>=3.2,<3.3"],
}


def main():
    if os.path.isdir(VENDOR):
        shutil.rmtree(VENDOR)
    for (name, python_version), requirements in BUNDLES.items():
        install(os.path.join(VENDOR, name), python_version, requirements)
    with open(os.path.join(VENDOR, "README.md"), "w") as f:
        f.write("Bundled at package time by scripts/vendor.py; not checked in. Licenses are in the *.dist-info folders.\n")


def install(target, python_version, requirements):
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
        "--no-compile", "--only-binary", ":all:", "--python-version", python_version,
        "--implementation", "py", "--target", target,
    ] + requirements)
    # drop things that aren't needed at runtime
    for name in os.listdir(target):
        path = os.path.join(target, name)
        if name == "bin" or name == "__pycache__":
            shutil.rmtree(path)
    for dirpath, dirnames, filenames in os.walk(target):
        for d in list(dirnames):
            if d in ("__pycache__", "test", "tests"):
                shutil.rmtree(os.path.join(dirpath, d))
                dirnames.remove(d)
    # jedi bundles typeshed's third-party stubs (~25MB) and django-stubs; without them jedi just
    # analyzes the installed packages' sources directly, so keep only the standard library stubs
    third_party = os.path.join(target, "jedi", "third_party")
    for sub in (os.path.join("typeshed", "stubs"), os.path.join("typeshed", "third_party"), "django-stubs"):
        path = os.path.join(third_party, sub)
        if os.path.isdir(path):
            shutil.rmtree(path)
            os.makedirs(path)
    print("bundled " + ", ".join(sorted(os.listdir(target))) + " into " + os.path.relpath(target, ROOT))


if __name__ == "__main__":
    main()
