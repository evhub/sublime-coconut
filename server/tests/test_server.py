"""End-to-end tests of the language server over stdio."""

import os
import textwrap

import pytest

from lsp_client import LspClient, LspError

MAIN = textwrap.dedent('''\
    import os
    from helpers import double

    data Point(x, y):
        def norm(self) = (self.x**2 + self.y**2)**0.5

    def add(a, b) = a + b

    match def fact(0) = 1
    addpattern def fact(n) = n * fact(n - 1)

    result = [1, 2, 3] |> map$(x => x * 2) |> list
    p = Point(1, 2)
    print(p.norm(), os.path.join("a", "b"), result |> fmap$(double), add(1, 2))
''')

HELPERS = textwrap.dedent('''\
    def double(x) = x * 2

    def triple(x) = x * 3
''')


def pos(text, line, needle, offset=0, nth=0):
    """Position of the nth occurrence of needle on (0-based) line, plus offset."""
    src = text.splitlines()[line]
    idx = -1
    for _ in range(nth + 1):
        idx = src.index(needle, idx + 1)
    return {"line": line, "character": idx + offset}


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    root = tmp_path_factory.mktemp("proj")
    (root / "main.coco").write_text(MAIN)
    (root / "helpers.coco").write_text(HELPERS)
    return str(root)


@pytest.fixture(scope="module")
def client(project):
    c = LspClient(project)
    yield c
    c.close()


@pytest.fixture(scope="module")
def main_uri(client, project):
    uri = client.open(os.path.join(project, "main.coco"), MAIN)
    diags = client.diagnostics(uri)
    assert [d for d in diags if d["severity"] == 1] == []
    return uri


def td(uri):
    return {"uri": uri}


def test_capabilities(client):
    caps = client.init_result["capabilities"]
    for cap in ("hoverProvider", "completionProvider", "definitionProvider", "referencesProvider",
                "documentSymbolProvider", "workspaceSymbolProvider", "renameProvider", "signatureHelpProvider"):
        assert caps[cap]


def test_syntax_error_diagnostic(client, project):
    text = "x = 1\ny = (1 +\nz = 3\n"
    uri = client.open(os.path.join(project, "broken.coco"), text)
    diags = client.diagnostics(uri)
    errors = [d for d in diags if d["severity"] == 1]
    assert len(errors) == 1
    assert "unclosed" in errors[0]["message"]
    assert errors[0]["range"]["start"] == {"line": 1, "character": 4}
    # fix it: diagnostics clear
    client.change(uri, "x = 1\ny = (1 + 2)\nz = 3\n", 2)
    assert [d for d in client.diagnostics(uri, version=2) if d["severity"] == 1] == []


def test_lint_diagnostics(client, project):
    text = "import sys\ndef f(x) = x + undefined_name\ndef g():\n    unused_local = 3\n    return 1\n"
    uri = client.open(os.path.join(project, "lint.coco"), text)
    diags = client.diagnostics(uri)
    messages = [d["message"] for d in diags]
    assert any("sys" in m and "unused" in m for m in messages)
    assert any("undefined_name" in m for m in messages)
    assert any("unused_local" in m for m in messages)
    undefined = [d for d in diags if "undefined_name" in d["message"]][0]
    assert undefined["range"]["start"] == {"line": 1, "character": 15}
    # code actions: remove the unused import / suppress with NOQA
    unused = [d for d in diags if "sys" in d["message"]][0]
    actions = client.request("textDocument/codeAction", {
        "textDocument": td(uri), "range": unused["range"], "context": {"diagnostics": [unused]},
    })
    titles = [a["title"] for a in actions]
    assert "Remove unused import 'sys'" in titles
    noqa = [d for d in diags if d.get("source") == "coconut" and "NOQA" in d["message"]]
    if noqa:
        actions = client.request("textDocument/codeAction", {
            "textDocument": td(uri), "range": noqa[0]["range"], "context": {"diagnostics": [noqa[0]]},
        })
        assert any(a["title"] == "Suppress with # NOQA" for a in actions)


def test_hover_user_function(client, main_uri):
    result = client.request("textDocument/hover", {"textDocument": td(main_uri), "position": pos(MAIN, 13, "norm")})
    assert "norm" in result["contents"]["value"]
    assert result["range"]["start"] == pos(MAIN, 13, "norm")


def test_hover_coconut_builtin(client, main_uri):
    result = client.request("textDocument/hover", {"textDocument": td(main_uri), "position": pos(MAIN, 13, "fmap", 1)})
    value = result["contents"]["value"]
    assert "Coconut" in value and "fmap" in value
    assert "coconut.readthedocs.io" in value


def test_hover_operator_and_keyword(client, main_uri):
    result = client.request("textDocument/hover", {"textDocument": td(main_uri), "position": pos(MAIN, 11, "|>", 1)})
    assert "Pipes" in result["contents"]["value"]
    result = client.request("textDocument/hover", {"textDocument": td(main_uri), "position": pos(MAIN, 3, "data", 1)})
    assert "data" in result["contents"]["value"]
    result = client.request("textDocument/hover", {"textDocument": td(main_uri), "position": pos(MAIN, 8, "match", 1)})
    assert "Pattern-Matching Functions" in result["contents"]["value"]


def test_definition_same_file(client, main_uri):
    result = client.request("textDocument/definition", {"textDocument": td(main_uri), "position": pos(MAIN, 12, "Point", 2)})
    assert result[0]["uri"] == main_uri
    assert result[0]["range"]["start"] == pos(MAIN, 3, "Point")
    result = client.request("textDocument/definition", {"textDocument": td(main_uri), "position": pos(MAIN, 13, "norm", 1)})
    assert result[0]["range"]["start"] == pos(MAIN, 4, "norm")


def test_definition_other_coconut_file(client, main_uri, project):
    result = client.request("textDocument/definition", {"textDocument": td(main_uri), "position": pos(MAIN, 13, "double", 1)})
    uris = [r["uri"] for r in result]
    assert any(u.endswith("helpers.coco") for u in uris), result
    target = [r for r in result if r["uri"].endswith("helpers.coco")][0]
    assert target["range"]["start"] == {"line": 0, "character": 4}


def test_references_and_highlight(client, main_uri):
    result = client.request("textDocument/references", {
        "textDocument": td(main_uri), "position": pos(MAIN, 12, "p"), "context": {"includeDeclaration": True},
    })
    starts = [r["range"]["start"] for r in result]
    assert pos(MAIN, 12, "p") in starts and pos(MAIN, 13, "p.", 0) in starts
    highlights = client.request("textDocument/documentHighlight", {"textDocument": td(main_uri), "position": pos(MAIN, 6, "a", 0, 1)})
    assert len(highlights) == 2


def test_rename(client, main_uri):
    prep = client.request("textDocument/prepareRename", {"textDocument": td(main_uri), "position": pos(MAIN, 9, "n)")})
    assert prep["placeholder"] == "n"
    edit = client.request("textDocument/rename", {"textDocument": td(main_uri), "position": pos(MAIN, 9, "n)"), "newName": "k"})
    edits = edit["changes"][main_uri]
    assert len(edits) == 3
    assert all(e["range"]["start"]["line"] == 9 for e in edits)
    with pytest.raises(LspError):
        client.request("textDocument/rename", {"textDocument": td(main_uri), "position": pos(MAIN, 9, "n)"), "newName": "not valid"})


def test_document_symbols(client, main_uri):
    symbols = client.request("textDocument/documentSymbol", {"textDocument": td(main_uri)})
    names = [s["name"] for s in symbols]
    assert names[:5] == ["Point", "add", "fact", "result", "p"]
    point = symbols[0]
    assert point["detail"] == "data"
    assert [c["name"] for c in point["children"]] == ["norm"]
    fact = symbols[2]
    assert fact["range"]["start"]["line"] == 8 and fact["range"]["end"]["line"] == 9


def test_workspace_symbols(client, main_uri):
    result = client.request("workspace/symbol", {"query": "trip"})
    assert [r["name"] for r in result] == ["triple"]
    assert result[0]["location"]["uri"].endswith("helpers.coco")
    result = client.request("workspace/symbol", {"query": "Point"})
    assert any(r["name"] == "Point" for r in result)


def test_completion_while_typing(client, project):
    path = os.path.join(project, "typing.coco")
    base = MAIN.replace("from helpers import double\n", "")
    uri = client.open(path, base)
    client.diagnostics(uri)
    # start typing a new line: the document no longer compiles, completion must still work
    typed = base + "p.no"
    client.change(uri, typed, 2)
    line = len(typed.splitlines()) - 1
    result = client.request("textDocument/completion", {"textDocument": td(uri), "position": {"line": line, "character": 4}})
    labels = [i["label"] for i in result["items"]]
    assert "norm" in labels
    typed = base + "os.path.jo"
    client.change(uri, typed, 3)
    result = client.request("textDocument/completion", {"textDocument": td(uri), "position": {"line": line, "character": 10}})
    assert "join" in [i["label"] for i in result["items"]]
    # completion inside a method body, on self
    typed = base.replace(
        "    def norm(self) = (self.x**2 + self.y**2)**0.5\n",
        "    def norm(self) = (self.x**2 + self.y**2)**0.5\n    def other(self):\n        self.\n",
    )
    client.change(uri, typed, 4)
    result = client.request("textDocument/completion", {"textDocument": td(uri), "position": {"line": 5, "character": 13}})
    labels = [i["label"] for i in result["items"]]
    assert "norm" in labels and "x" in labels
    # Coconut built-ins and keywords
    typed = base + "fm"
    client.change(uri, typed, 5)
    result = client.request("textDocument/completion", {"textDocument": td(uri), "position": {"line": line, "character": 2}})
    fmap = [i for i in result["items"] if i["label"] == "fmap"]
    assert fmap and "Coconut" in fmap[0]["documentation"]["value"]


def test_signature_help(client, main_uri, project):
    path = os.path.join(project, "sig.coco")
    text = "def add(a, b) = a + b\nadd(1, "
    uri = client.open(path, text)
    result = client.request("textDocument/signatureHelp", {"textDocument": td(uri), "position": {"line": 1, "character": 7}})
    assert result["signatures"][0]["label"] == "add(a, b)"
    assert result["activeParameter"] == 1


def test_compiled_request(client, main_uri):
    result = client.request("coconut/compiled", {"textDocument": td(main_uri)})
    assert result["upToDate"]
    assert "class Point" in result["compiled"]
    info = client.request("coconut/info", {})
    assert info["coconut_version"]


def test_settings_change_recompiles(client, project):
    # 'match x:' style errors aside, use a target-dependent feature: walrus requires 3.8+
    text = "if (n := 10) > 5:\n    print(n)\n"
    uri = client.open(os.path.join(project, "target.coco"), text)
    assert [d for d in client.diagnostics(uri) if d["severity"] == 1] == []
    client.notify("workspace/didChangeConfiguration", {"settings": {"coconut": {"target": "2.7"}}})
    diags = client.diagnostics(uri)
    assert any(d["severity"] == 1 for d in diags), diags
    client.notify("workspace/didChangeConfiguration", {"settings": {"coconut": {"target": "sys"}}})
    assert [d for d in client.diagnostics(uri) if d["severity"] == 1] == []


def test_cross_module_intelligence(client, project):
    # helpers.coco has no compiled helpers.py, so jedi only sees it through the overlay
    assert not os.path.exists(os.path.join(project, "helpers.py"))
    text = "import helpers\nfrom helpers import double\nhelpers.tr\ndouble(\n"
    uri = client.open(os.path.join(project, "importer.coco"), text)
    client.diagnostics(uri)
    result = client.request("textDocument/completion", {"textDocument": td(uri), "position": {"line": 2, "character": 10}})
    assert "triple" in [i["label"] for i in result["items"]]
    sig = client.request("textDocument/signatureHelp", {"textDocument": td(uri), "position": {"line": 3, "character": 7}})
    assert sig["signatures"][0]["label"] == "double(x)"
    hover = client.request("textDocument/hover", {"textDocument": td(uri), "position": {"line": 1, "character": 22}})
    assert "double(x)" in hover["contents"]["value"]
    result = client.request("textDocument/definition", {"textDocument": td(uri), "position": {"line": 3, "character": 2}})
    assert result and result[0]["uri"].endswith("helpers.coco")
    assert result[0]["range"]["start"] == {"line": 0, "character": 4}


def test_mypy_type_checking(project):
    pytest.importorskip("mypy")
    client = LspClient(project, init_options={"mypy": True})
    try:
        text = "def g() -> int = 1\ndef f(x: int) -> str = x\nw: str = g()\nok: int = g()\n"
        uri = client.open(os.path.join(project, "typed.coco"), text)
        diags = client.wait_notification(
            "textDocument/publishDiagnostics",
            lambda p: p["uri"] == uri and any(d.get("source") == "mypy" for d in p["diagnostics"]),
            timeout=120,
        )["diagnostics"]
        mypy = sorted((d["range"]["start"]["line"], d["range"]["start"]["character"], d["code"]) for d in diags if d.get("source") == "mypy")
        assert mypy == [(1, 23, "return-value"), (2, 9, "assignment")], diags
    finally:
        client.close()


def test_utf16_positions(client, project):
    # columns are UTF-16 code units in LSP; the emoji takes two of them
    text = 'foo = 1\nprint("\U0001F600", foo)\n'
    uri = client.open(os.path.join(project, "emoji.coco"), text)
    client.diagnostics(uri)
    refs = client.request("textDocument/references", {
        "textDocument": td(uri), "position": {"line": 1, "character": 12}, "context": {"includeDeclaration": True},
    })
    starts = sorted((r["range"]["start"]["line"], r["range"]["start"]["character"], r["range"]["end"]["character"]) for r in refs)
    assert starts == [(0, 0, 3), (1, 12, 15)]
    edit = client.request("textDocument/rename", {"textDocument": td(uri), "position": {"line": 1, "character": 13}, "newName": "bar"})
    assert sorted(e["range"]["start"]["character"] for e in edit["changes"][uri]) == [0, 12]


def test_rename_refused_when_file_has_errors(client, project):
    text = "foo = 1\nprint(foo +)\nprint(foo)\n"
    uri = client.open(os.path.join(project, "broken_rename.coco"), text)
    client.diagnostics(uri)
    with pytest.raises(LspError):
        client.request("textDocument/rename", {"textDocument": td(uri), "position": {"line": 0, "character": 0}, "newName": "bar"})


def test_no_diagnostics_after_close(client, project):
    uri = client.open(os.path.join(project, "closed.coco"), "x = (\n")
    client.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
    cleared = client.wait_notification("textDocument/publishDiagnostics", lambda p: p["uri"] == uri)
    assert cleared["diagnostics"] == []
    # nothing may be published for the closed document afterwards
    import time
    time.sleep(2)
    while not client.notifications.empty():
        msg = client.notifications.get()
        assert not (msg["method"] == "textDocument/publishDiagnostics" and msg["params"]["uri"] == uri), msg
