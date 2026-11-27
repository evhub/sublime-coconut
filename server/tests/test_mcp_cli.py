"""Tests for the MCP server and the command-line interface."""

import json
import os
import queue
import subprocess
import threading
import sys
import textwrap

import pytest

SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "coconut_language_server.py")

CODE = textwrap.dedent('''\
    import sys

    data Point(x, y)

    def scale(p, k) = Point(p.x * k, p.y * k)

    origin = Point(0, 0) |> scale$(k=2)
''')


@pytest.fixture(scope="module")
def coco_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("cli") / "geo.coco"
    path.write_text(CODE)
    return str(path)


@pytest.fixture(scope="module")
def mcp():
    # stderr must be drained (or discarded): a full pipe would block the server (Windows pipes are tiny)
    proc = subprocess.Popen([sys.executable, SERVER, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, universal_newlines=True, bufsize=1)
    lines = queue.Queue()

    def reader():
        for line in proc.stdout:
            lines.put(line)

    threading.Thread(target=reader, daemon=True).start()
    state = {"id": 0}

    def call(method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            state["id"] += 1
            msg["id"] = state["id"]
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        if notify:
            return None
        response = json.loads(lines.get(timeout=120))
        assert response["id"] == state["id"]
        return response

    init = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
    assert init["result"]["protocolVersion"] == "2025-06-18"
    call("notifications/initialized", notify=True)
    yield call
    proc.stdin.close()
    proc.wait(timeout=10)


def tool(mcp, name, **args):
    response = mcp("tools/call", {"name": name, "arguments": args})
    result = response["result"]
    return result["content"][0]["text"], result["isError"]


def test_mcp_tools_list(mcp):
    names = [t["name"] for t in mcp("tools/list")["result"]["tools"]]
    assert names == ["coconut_check", "coconut_compile", "coconut_docs", "coconut_hover",
                     "coconut_definition", "coconut_references", "coconut_symbols"]


def test_mcp_check(mcp, coco_file):
    text, err = tool(mcp, "coconut_check", path=coco_file)
    assert not err
    assert "0 errors" in text and "'sys'" in text
    text, err = tool(mcp, "coconut_check", code="x = (1 +\n")
    assert "1 error" in text and ":1:5: error: unclosed" in text


def test_mcp_compile(mcp):
    text, err = tool(mcp, "coconut_compile", code="x = [1, 2] |> map$(.+1) |> list\n")
    assert not err
    assert "Coconut Header" not in text and "(line in Coconut source)" not in text
    assert "map" in text and "list" in text
    text, err = tool(mcp, "coconut_compile", code="x = (\n")
    assert err and "doesn't compile" in text


def test_mcp_docs(mcp):
    text, err = tool(mcp, "coconut_docs", query="|>")
    assert not err and "Pipes" in text
    text, err = tool(mcp, "coconut_docs", query="addpattern")
    assert "addpattern" in text
    text, err = tool(mcp, "coconut_docs")
    assert "`fmap`" in text
    text, err = tool(mcp, "coconut_docs", query="zzzz-nothing")
    assert err


def test_mcp_code_intelligence(mcp, coco_file):
    text, err = tool(mcp, "coconut_definition", path=coco_file, line=7, column=25)
    assert not err and ":5:5:" in text  # scale
    text, err = tool(mcp, "coconut_hover", path=coco_file, line=7, column=25)
    assert "scale" in text
    text, err = tool(mcp, "coconut_references", path=coco_file, line=5, column=5)
    assert text.count("geo.coco") == 2
    text, err = tool(mcp, "coconut_symbols", path=coco_file)
    assert "data Point" in text and "function scale" in text and "variable origin" in text
    text, err = tool(mcp, "coconut_hover", path=coco_file, line=0, column=1)
    assert err


def test_mcp_unknown(mcp):
    assert mcp("bogus/method")["error"]["code"] == -32601
    text, err = tool(mcp, "nope")
    assert err


def run_cli(*args):
    proc = subprocess.run([sys.executable, SERVER] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=240)
    return proc.returncode, proc.stdout, proc.stderr


def test_cli_check(coco_file, tmp_path):
    code, out, err = run_cli("check", coco_file)
    assert code == 0 and "unused import 'sys'" in out
    code, out, err = run_cli("check", coco_file, "-W")
    assert code == 1
    bad = tmp_path / "bad.coco"
    bad.write_text("def f(x) =\n")
    code, out, err = run_cli("check", str(tmp_path), "--json")
    assert code == 1
    data = json.loads(out)
    assert data["files_checked"] == 1 and data["diagnostics"][0]["severity"] == "error"


def test_cli_position_commands(coco_file):
    code, out, err = run_cli("definition", coco_file, "7", "25")
    assert code == 0 and ":5:5:" in out
    code, out, err = run_cli("symbols", coco_file, "--json")
    assert [s["name"] for s in json.loads(out)] == ["Point", "scale", "origin"]
    code, out, err = run_cli("compile", coco_file, "--no-line-comments")
    assert code == 0 and "def scale(p, k):" in out
    code, out, err = run_cli("docs", "fmap")
    assert code == 0 and "fmap" in out


def test_cli_accepts_stdio_flag():
    # LSP clients often launch servers with --stdio; it must start the server, not error out
    proc = subprocess.Popen([sys.executable, SERVER, "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(b"", timeout=30)
    assert b"unrecognized arguments" not in err


def test_cli_check_mypy(tmp_path):
    pytest.importorskip("mypy")
    path = tmp_path / "typed.coco"
    path.write_text("def f(x: int) -> str = x\n")
    code, out, err = run_cli("check", str(path), "--mypy")
    assert code == 1 and ":1:24: error: Incompatible return value type" in out, out + err
