"""Optional mypy type checking of the compiled Python, mapped back to the Coconut source.

The compiled document is written into the workspace mirror (see overlay.py), next to compiled
versions of the Coconut modules it imports, and mypy checks it there.
"""

import os
import re
import subprocess
import sys

from .compiler import SEVERITY_ERROR, SEVERITY_INFORMATION, make_range
from .sourcemap import CompiledDocument

MYPY_LINE_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<col>\d+):)? (?P<sev>error|note|warning): (?P<msg>.*?)(?:  \[(?P<code>[\w-]+)\])?$")
_running = set()


def kill_running():
    """Kill any mypy processes still running (e.g. when the server exits)."""
    for proc in list(_running):
        try:
            proc.kill()
        except Exception:
            pass


CONFIG_FILES = ("mypy.ini", ".mypy.ini", "pyproject.toml", "setup.cfg")


def mypy_available(python=None):
    try:
        import importlib.util
        return importlib.util.find_spec("mypy") is not None
    except Exception:
        return False


def find_config(root):
    for name in CONFIG_FILES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            if name in ("pyproject.toml", "setup.cfg"):
                try:
                    with open(path, encoding="utf-8") as f:
                        if "mypy" not in f.read():
                            continue
                except (OSError, UnicodeDecodeError):
                    continue
            return path
    return None


def run_mypy(doc_path, source, compiled, overlay, roots, timeout=120, extra_args=()):
    """Type-check compiled code; returns a list of LSP diagnostics for the Coconut source."""
    root = overlay.root_for(doc_path, roots)
    mirror_root = overlay.mirror_root(root)
    target = overlay.script_path(doc_path, roots)
    overlay.prepare(doc_path, source, roots)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(compiled)
    args = [
        sys.executable, "-m", "mypy",
        "--show-column-numbers", "--show-error-codes", "--no-error-summary", "--no-pretty",
        "--hide-error-context", "--no-color-output", "--follow-imports=silent",
        "--cache-dir", os.path.join(mirror_root, ".mypy_cache"),
    ]
    config = find_config(root)
    if config:
        args += ["--config-file", config]
    args += list(extra_args) + [target]
    env = dict(os.environ)
    env["MYPYPATH"] = mirror_root + (os.pathsep + root)
    proc = subprocess.Popen(
        args, cwd=mirror_root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    _running.add(proc)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return []
    finally:
        _running.discard(proc)
    return parse_mypy_output(out, target, source, compiled, cwd=mirror_root)


def parse_mypy_output(output, target, source, compiled, cwd=None):
    doc = CompiledDocument(source, compiled)
    target_norm = os.path.normcase(os.path.abspath(target))
    diagnostics = []
    seen = set()
    for line in output.splitlines():
        m = MYPY_LINE_RE.match(line.strip())
        if not m:
            continue
        path = m.group("path")
        if cwd is not None and not os.path.isabs(path):
            path = os.path.join(cwd, path)
        if os.path.normcase(os.path.abspath(path)) != target_norm:
            continue
        message = m.group("msg")
        if "_coconut" in message or "__coconut__" in message:
            continue
        cline = int(m.group("line")) - 1
        col = int(m.group("col")) - 1 if m.group("col") else None
        mapped = doc.compiled_to_source(cline, col)
        if mapped is None:
            continue
        sline, scol, ecol = mapped
        key = (sline, scol, message)
        if key in seen:
            continue
        seen.add(key)
        diag = {
            "range": make_range(sline, scol, sline, ecol),
            "severity": SEVERITY_ERROR if m.group("sev") == "error" else SEVERITY_INFORMATION,
            "source": "mypy",
            "message": message,
        }
        if m.group("code"):
            diag["code"] = m.group("code")
        diagnostics.append(diag)
    return diagnostics
