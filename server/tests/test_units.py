"""Unit tests for source mapping, diagnostics, docs, and the agent skill's examples."""

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


def skill_examples():
    with open(os.path.join(ROOT, "skills", "coconut", "SKILL.md")) as f:
        text = f.read()
    return re.findall(r"```coconut\n(.*?)```", text, re.DOTALL)


@pytest.mark.parametrize("example", skill_examples())
def test_skill_examples_compile_cleanly(example):
    result = compile_coconut(example)
    problems = [d["message"] for d in result["diagnostics"] if d["severity"] <= 2]
    assert result["compiled"] is not None and not problems, problems
