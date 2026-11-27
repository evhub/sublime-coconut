"""Unit tests for source mapping, diagnostics, docs, snippets, and running without jedi."""

import os
import re

import pytest

from coconut_ls import docs
from coconut_ls.compiler import compile_coconut, repair_source
from coconut_ls.sourcemap import CompiledDocument, LineDiff, blank_strings_and_comments, word_occurrences
from coconut_ls.uris import path_to_uri, uri_to_path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_blank_strings_and_comments():
    line = '''x = f("a(b)", 'c') + g(f"{x}") # comment x'''
    blanked = blank_strings_and_comments(line)
    assert len(blanked) == len(line)
    assert "a(b)" not in blanked and "comment" not in blanked and "{x}" in blanked
    assert word_occurrences(line, "x") == [0, 26]


def test_line_diff():
    old = ["a", "b", "c", "d"]
    new = ["a", "b", "X", "c", "d"]
    diff = LineDiff(old, new)
    assert diff.new_to_old(3) == 2 and diff.old_to_new(2) == 3
    assert diff.new_to_old(2) is None
    assert diff.nearest_new_to_old_before(2) == 1


def test_source_mapping_roundtrip():
    src = "def add(a, b) = a + b\nresult = [1, 2] |> map$(add$(1)) |> list\n"
    doc = CompiledDocument(src, compile_coconut(src)["compiled"])
    line = src.splitlines()[1]
    col = line.index("add")
    cl, cc = doc.source_to_compiled(1, col)
    assert doc.compiled_line(cl)[cc:cc + 3] == "add"
    assert doc.compiled_to_source(cl, cc, word="add") == (1, col, col + 3)


@pytest.mark.parametrize("code, line, col", [
    ("x = 1\ny = (1 +\nz = 3\n", 1, 4),
    ("def f(x) =\n", 0, None),
    ("a = 1\nb = 2 3\n", 1, None),
])
def test_error_positions(code, line, col):
    result = compile_coconut(code)
    assert result["compiled"] is None
    errors = [d for d in result["diagnostics"] if d["severity"] == 1]
    assert errors and errors[0]["range"]["start"]["line"] == line
    if col is not None:
        assert errors[0]["range"]["start"]["character"] == col
    rng = errors[0]["range"]
    assert (rng["end"]["line"], rng["end"]["character"]) >= (rng["start"]["line"], rng["start"]["character"])


def test_repair_source():
    assert repair_source("x = 1\ny = (\nz = 2", 1) == "x = 1\npass\nz = 2"
    assert repair_source("def f(x) =\n    x +\n", 0) == "if True:\n    x +\n"
    repaired = repair_source("a = 1\ndef g():\n    b = (\n    return 1\n", 2)
    assert compile_coconut(repaired)["compiled"] is not None


def test_docs():
    assert docs.lookup("fmap")["url"].endswith("#fmap")
    assert docs.operator_at("x |> f", 3)[0] == "|>"
    assert docs.operator_at("f ..> g", 2)[0] == "..>"
    assert docs.operator_at("a + b", 2) is None
    assert docs.keyword_entry("match def f(x) = x", 0, 5) == "match def"
    assert docs.keyword_entry("data = 5", 0, 4) is None
    assert docs.keyword_entry("data Point(x, y)", 0, 4) == "data"
    assert docs.search("pattern matching")


def test_uris():
    path = os.path.abspath("some dir/file.coco")
    assert uri_to_path(path_to_uri(path)) == path
    assert uri_to_path("untitled:Untitled-1") is None


def test_snippets_compile():
    import json
    with open(os.path.join(ROOT, "snippets.json")) as f:
        snippets = json.load(f)
    for name, snippet in snippets.items():
        body = snippet["body"]
        body = re.sub(r"\$\{\d+:([^}]*)\}", r"\1", body)
        body = re.sub(r"\$\d+", "pass", body)
        if name in ("case", "casematch"):
            body = "match x:" + body.replace("\n", "\n    ")
        if name.startswith("pattern"):
            body = "def func(args) = None\n" + body
        result = compile_coconut(body)
        problems = [d["message"] for d in result["diagnostics"] if d["severity"] == 1 or "deprecated" in d["message"]]
        assert result["compiled"] is not None and not problems, (name, body, problems)


def test_works_without_jedi(monkeypatch):
    from coconut_ls import intel
    monkeypatch.setattr(intel, "jedi", None)
    src = "x = [1] |> fmap$(y => y)\n"
    doc = CompiledDocument(src, compile_coconut(src)["compiled"])
    analyzer = intel.Analyzer("/tmp/nojedi.coco", src + "fm", doc)
    hover = analyzer.hover(0, src.index("fmap") + 1)
    assert hover and "fmap" in hover[0]
    labels = [i["label"] for i in analyzer.completions(1, 2)]
    assert "fmap" in labels
    assert analyzer.definitions(0, 0) == [] or analyzer.definitions(0, 0)
    assert analyzer.signature_help(0, 5) is None
