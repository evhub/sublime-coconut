"""Compiling Coconut code and turning compiler errors/warnings into LSP diagnostics.

This module imports Coconut lazily, and is normally run inside a separate worker process
(see worker.py) so that slow compiles never block the language server, and a pathological
compile can be killed without taking the server down.
"""

import re
import sys
import threading
import traceback

from .sourcemap import CompiledDocument, word_occurrences

SEVERITY_ERROR = 1
SEVERITY_WARNING = 2
SEVERITY_INFORMATION = 3
SEVERITY_HINT = 4

TAG_UNNECESSARY = 1
TAG_DEPRECATED = 2

DEFAULT_SETTINGS = {
    "target": "sys",
    "strict": False,
    "lint": True,
}

_coconut_lock = threading.Lock()
_current_setup = None
_collected_warnings = None


def coconut_info():
    """Information about the Coconut installation available to this interpreter."""
    info = {
        "python_version": ".".join(str(v) for v in sys.version_info[:3]),
        "python_executable": sys.executable,
    }
    try:
        from coconut.api import version
        info["coconut_version"] = version("num")
    except Exception as err:
        info["coconut_version"] = None
        info["coconut_error"] = "{t}: {e}".format(t=type(err).__name__, e=err)
    try:
        import pyflakes.checker  # noqa
        import pyflakes
        info["pyflakes_version"] = getattr(pyflakes, "__version__", "unknown")
    except Exception:
        info["pyflakes_version"] = None
    return info


def _install_warning_hook():
    """Make Coconut's logger hand us warnings instead of printing them."""
    from coconut.terminal import logger

    if getattr(logger, "_coconut_ls_hooked", False):
        return

    def warn_err(warning, force=False):
        if _collected_warnings is not None:
            _collected_warnings.append(warning)

    logger.warn_err = warn_err
    logger._coconut_ls_hooked = True


def _setup(settings):
    global _current_setup
    from coconut.api import setup
    key = (str(settings.get("target") or "sys"), bool(settings.get("strict")))
    if key != _current_setup:
        setup(target=key[0], strict=key[1], line_numbers=True, keep_lines=False, no_wrap=True, minify=False)
        _current_setup = key


def make_range(start_line, start_col, end_line, end_col):
    return {
        "start": {"line": max(start_line, 0), "character": max(start_col, 0)},
        "end": {"line": max(end_line, 0), "character": max(end_col, 0)},
    }


def _error_range(err, source_lines):
    """Compute an LSP range for a CoconutSyntaxError (or subclass)."""
    args = list(getattr(err, "args", ())) + [None] * 7
    _, snippet, point, ln, _, endpoint, _ = args[:7]
    if not ln:
        return make_range(0, 0, 0, len(source_lines[0]) if source_lines else 0)
    line = min(int(ln) - 1, max(len(source_lines) - 1, 0))
    doc_line = source_lines[line] if source_lines else ""
    snippet = snippet or ""
    snippet_lines = snippet.splitlines() or [""]
    start_col = point if isinstance(point, int) else 0

    # the snippet may have been reformatted; re-anchor columns on the real document line
    first = snippet_lines[0]
    offset = 0
    if first and first != doc_line:
        idx = doc_line.find(first.strip())
        if idx >= 0:
            offset = idx - (len(first) - len(first.lstrip()))
    start_col = start_col + offset

    end_line, end_col = line, None
    if isinstance(endpoint, int) and endpoint > (point or 0):
        before = snippet[:endpoint]
        newlines = before.count("\n")
        if newlines:
            end_line = min(line + newlines, len(source_lines) - 1)
            end_col = len(before) - before.rfind("\n") - 1
        else:
            end_col = endpoint + offset
    start_col = max(0, min(start_col, len(doc_line)))
    if end_col is None or (end_line == line and end_col <= start_col):
        # highlight the token at the error location (or the last char of the line)
        m = re.match(r"\w+|\S", doc_line[start_col:])
        if m:
            end_col = start_col + len(m.group(0))
        elif doc_line.rstrip():
            end_col = len(doc_line.rstrip())
            start_col = max(end_col - 1, 0)
        else:
            end_col = start_col
    end_line_text = source_lines[end_line] if 0 <= end_line < len(source_lines) else ""
    if end_line != line:
        end_col = min(end_col, len(end_line_text))
    return make_range(line, start_col, end_line, end_col)


def _error_message(err):
    args = list(getattr(err, "args", ())) + [None] * 5
    message = args[0] if isinstance(args[0], str) else str(err)
    # some errors embed a rendered snippet of the code; keep just the message itself
    message = message.split("\n", 1)[0]
    message = re.sub(r"\s*\(line \d+(?: in [^)]*)?\)\s*$", "", message)
    extra = args[4]
    if extra and str(extra) not in message:
        message += " (" + str(extra) + ")"
    return message


def _reanchor_on_quoted_name(diag, source_lines):
    """For messages like "found unused import 'os'", point the range at the name itself."""
    m = re.search(r"(?:unused import|undefined name|unused variable) '([\w.]+)'", diag["message"])
    if not m:
        return
    rng = diag["range"]
    line = rng["start"]["line"]
    if not 0 <= line < len(source_lines):
        return
    name = m.group(1).split(".")[-1]
    occ = word_occurrences(source_lines[line], name)
    if occ and not any(rng["start"]["character"] <= c < rng["end"]["character"] for c in occ):
        start = min(occ, key=lambda c: abs(c - rng["start"]["character"]))
        diag["range"] = make_range(line, start, line, start + len(name))
    if "unused" in m.group(0):
        diag["tags"] = [TAG_UNNECESSARY]


def _err_to_diagnostic(err, source_lines, severity):
    from coconut.exceptions import CoconutSyntaxError
    name = type(err).__name__
    diag = {
        "severity": severity,
        "source": "coconut",
        "code": name,
        "message": _error_message(err) if isinstance(err, CoconutSyntaxError) else str(err),
    }
    if isinstance(err, CoconutSyntaxError):
        diag["range"] = _error_range(err, source_lines)
    else:
        diag["range"] = make_range(0, 0, 0, len(source_lines[0]) if source_lines else 0)
    _reanchor_on_quoted_name(diag, source_lines)
    if "deprecated" in diag["message"].lower():
        diag["tags"] = [TAG_DEPRECATED]
    if "NOQA" in diag["message"]:
        diag["data"] = {"noqa": True}
    return diag


def compile_coconut(code, settings=None):
    """Compile code; returns {"compiled": str or None, "diagnostics": [...], "info": {...}}."""
    global _collected_warnings
    settings = dict(DEFAULT_SETTINGS, **(settings or {}))
    source_lines = code.splitlines()
    diagnostics = []
    compiled = None
    try:
        from coconut.api import parse
        from coconut.exceptions import CoconutException, CoconutStyleError
    except Exception as err:
        return {
            "compiled": None,
            "diagnostics": [],
            "fatal": "Coconut is not installed for {exe} ({t}: {e}); install it with: {exe} -m pip install coconut".format(
                exe=sys.executable, t=type(err).__name__, e=err,
            ),
        }

    with _coconut_lock:
        _install_warning_hook()
        warnings = _collected_warnings = []
        try:
            try:
                _setup(settings)
                compiled = parse(code, "sys")
            except CoconutStyleError as err:
                # in strict mode, report the style error as a warning and still compile normally
                diagnostics.append(_err_to_diagnostic(err, source_lines, SEVERITY_WARNING))
                _setup(dict(settings, strict=False))
                try:
                    compiled = parse(code, "sys")
                finally:
                    _setup(settings)
        except CoconutException as err:
            diagnostics.append(_err_to_diagnostic(err, source_lines, SEVERITY_ERROR))
        except RecursionError:
            diagnostics.append({
                "range": make_range(0, 0, 0, 0), "severity": SEVERITY_ERROR, "source": "coconut",
                "message": "maximum recursion depth exceeded while compiling (expression nested too deeply?)",
            })
        except Exception as err:
            diagnostics.append({
                "range": make_range(0, 0, 0, 0), "severity": SEVERITY_ERROR, "source": "coconut",
                "message": "internal Coconut compiler error: {t}: {e}".format(t=type(err).__name__, e=err),
            })
            traceback.print_exc(file=sys.stderr)
        finally:
            _collected_warnings = None

    seen = set()
    for warning in warnings:
        diag = _err_to_diagnostic(warning, source_lines, SEVERITY_WARNING)
        key = (diag["message"], diag["range"]["start"]["line"])
        if key not in seen:
            seen.add(key)
            diagnostics.append(diag)

    if compiled is not None and settings.get("lint", True):
        try:
            covered = set()
            for diag in diagnostics:
                for name in re.findall(r"'([\w.]+)'", diag["message"]):
                    covered.add((diag["range"]["start"]["line"], name.split(".")[-1]))
            for diag in lint_compiled(code, compiled):
                names = re.findall(r"'([\w.]+)'", diag["message"])
                line = diag["range"]["start"]["line"]
                if diag["code"] in ("UndefinedName", "UnusedImport") and any((line, n.split(".")[-1]) in covered for n in names):
                    continue
                diagnostics.append(diag)
        except Exception:
            traceback.print_exc(file=sys.stderr)

    return {"compiled": compiled, "diagnostics": diagnostics}


# -----------------------------------------------------------------------------------------------------------------------
# PYFLAKES LINTING OF COMPILED CODE
# -----------------------------------------------------------------------------------------------------------------------

_star_import_names = None


def _coconut_star_names():
    global _star_import_names
    if _star_import_names is None:
        try:
            import coconut.__coconut__ as header_module
            names = getattr(header_module, "__all__", None)
            if names is None:
                names = [n for n in dir(header_module) if not n.startswith("_")]
            _star_import_names = list(names)
        except Exception:
            _star_import_names = []
    return _star_import_names


STAR_IMPORT_RE = re.compile(r"^from coconut\.__coconut__ import \*\s*$", re.MULTILINE)

# pyflakes message classes we never report, since they're artifacts of compilation
IGNORED_PYFLAKES = (
    "ImportStarUsed", "ImportStarUsage", "ImportStarNotPermitted", "FutureFeatureNotDefined",
    "LateFutureImport", "ReturnOutsideFunction", "YieldOutsideFunction",
)

PYFLAKES_SEVERITY = {
    "UndefinedName": SEVERITY_WARNING,
    "UndefinedLocal": SEVERITY_WARNING,
    "UndefinedExport": SEVERITY_WARNING,
    "UnusedImport": SEVERITY_HINT,
    "UnusedVariable": SEVERITY_HINT,
    "UnusedAnnotation": SEVERITY_HINT,
    "RedefinedWhileUnused": SEVERITY_INFORMATION,
    "ImportShadowedByLoopVar": SEVERITY_INFORMATION,
}


def lint_compiled(source, compiled):
    """Run pyflakes (if available) over the compiled Python and map its messages back to source."""
    try:
        from pyflakes import checker
    except Exception:
        return []
    import ast

    # make the header's star import explicit so pyflakes can detect undefined names
    names = _coconut_star_names()
    explicit = "from coconut.__coconut__ import " + ", ".join(names) if names else "pass"
    checked = STAR_IMPORT_RE.sub(lambda m: explicit, compiled, count=1)
    try:
        tree = ast.parse(checked)
    except SyntaxError:
        return []
    w = checker.Checker(tree, filename="<coconut>")
    doc = CompiledDocument(source, compiled)
    diagnostics = []
    seen = set()
    for message in w.messages:
        kind = type(message).__name__
        if kind in IGNORED_PYFLAKES:
            continue
        line = message.lineno - 1
        src = doc.line_map[line] if 0 <= line < len(doc.line_map) else None
        if src is None:
            continue
        args = [a for a in getattr(message, "message_args", ()) if isinstance(a, str)]
        if any("_coconut" in a for a in args):
            continue
        text = message.message % message.message_args
        name = args[0] if args else None
        if kind == "UnusedImport" and name:
            # 'a.b.c' imported but unused -> highlight the last component
            name = name.split(" as ")[-1].split(".")[-1]
        src_line = doc.source_line(src)
        if name and not word_occurrences(src_line, name):
            # name doesn't appear in the source line: compiler-generated, so don't report it
            continue
        if kind == "RedefinedWhileUnused" and re.search(r"\b(addpattern|match|case)\b", src_line):
            continue
        mapped = doc.compiled_to_source(line, getattr(message, "col", None), word=name)
        if mapped is None:
            continue
        sline, scol, ecol = mapped
        key = (kind, sline, scol, text)
        if key in seen:
            continue
        seen.add(key)
        diag = {
            "range": make_range(sline, scol, sline, ecol),
            "severity": PYFLAKES_SEVERITY.get(kind, SEVERITY_WARNING),
            "source": "pyflakes",
            "code": kind,
            "message": text,
        }
        if kind in ("UnusedImport", "UnusedVariable", "UnusedAnnotation"):
            diag["tags"] = [TAG_UNNECESSARY]
        diagnostics.append(diag)
    return diagnostics


# -----------------------------------------------------------------------------------------------------------------------
# ERROR-TOLERANT ANALYSIS
# -----------------------------------------------------------------------------------------------------------------------

def first_error_line(diagnostics):
    lines = [d["range"]["start"]["line"] for d in diagnostics if d.get("severity") == SEVERITY_ERROR and d.get("source") == "coconut"]
    return min(lines) if lines else None


def repair_source(text, line):
    """Neutralize source line `line` so that the rest of the file can compile for analysis.

    The line is replaced (keeping the line count) by 'pass', or by 'if True:' if it opens an
    indented block, so that the block's body stays syntactically valid."""
    lines = text.split("\n")
    if not 0 <= line < len(lines):
        return None
    current = lines[line]
    indent = current[:len(current) - len(current.lstrip())]
    next_indent = None
    for following in lines[line + 1:]:
        if following.strip() and not following.strip().startswith("#"):
            next_indent = len(following) - len(following.lstrip())
            break
    if next_indent is not None and next_indent > len(indent):
        replacement = indent + "if True:"
    else:
        replacement = indent + "pass"
    if replacement == current:
        return None
    lines[line] = replacement
    return "\n".join(lines)
