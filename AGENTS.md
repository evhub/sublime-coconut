# Working on sublime-coconut

Editor support for the [Coconut](https://github.com/evhub/coconut) language: a VS Code extension, a Sublime Text package, a language server, and a Claude Code plugin, all in one repository.

## Layout

| Path | What |
| --- | --- |
| `sublime_coconut/specification.py` | Source of the syntax grammar. `python build.py` (needs [tmtools](https://github.com/evhub/tmtools)) regenerates `langs/Coconut.tmLanguage`; if tmtools isn't available, make the identical edit in both files. |
| `langs/`, `*.tmPreferences`, `snippets/`, `*.sublime-*`, `coconut_lsp.py` | Sublime Text package (`coconut_lsp.py` registers the language server with the LSP package). `.no-sublime-package` makes Package Control unpack the package so `server/` can run. |
| `package.json`, `extension.js`, `language-configuration.json`, `snippets.json` | VS Code extension. |
| `server/coconut_language_server.py` | Entry point for the language server, CLI, and MCP server. |
| `server/coconut_ls/` | The server package (stdlib only; jedi and pyflakes optional). |
| `server/tests/` | pytest suite: end-to-end LSP tests over stdio, MCP/CLI tests, unit tests. |
| `test/` | VS Code integration tests (drive a real VS Code via `@vscode/test-electron`). |
| `.claude-plugin/`, `.lsp.json`, `.mcp.json`, `skills/` | Claude Code plugin marketplace + plugin. The repo root is the plugin root. |
| `scripts/vendor.py` | Bundles jedi/parso/pyflakes into `server/vendor/` (not committed) for the `.vsix`. |
| `scripts/generate_docs.py` | Regenerates `server/coconut_ls/data/docs.json` (hover docs) from Coconut's `DOCS.md`. |

## Server architecture (`server/coconut_ls/`)

- `protocol.py`: JSON-RPC framing over stdio. `stdout` is reserved for protocol messages; `sys.stdout` is redirected to stderr. Set `COCONUT_LS_LOG=/path` to log every message.
- `server.py`: LSP handlers. Documents use full text sync. A compile thread debounces changes and sends compiles to `worker.py` (a child process, killed on timeout). After a failed compile, `repaired_compile` neutralizes broken lines (`compiler.repair_source`) so analysis keeps working.
- `compiler.py`: runs Coconut (`coconut.api.parse(code, "sys")` with `line_numbers=True`), converts `CoconutSyntaxError`s and captured warnings into diagnostics, lints compiled code with pyflakes. The worker enables Coconut's incremental parsing for inputs under 20KB (much faster recompiles).
- `sourcemap.py`: maps positions between Coconut source and compiled Python using the `#N (line in Coconut source)` comments plus identifier occurrence matching; `LineDiff` maps lines between the current text and the last successfully compiled text.
- `intel.py`: jedi on the compiled code (`Analyzer`): hover, completion, signatures, definitions, references, rename. If the cursor's line changed since the last good compile, the expression under the cursor is spliced into the compiled code (`Analyzer.splice`).
- `overlay.py`: a mirror of the workspace (in the temp dir) where the Coconut modules a document imports are compiled to `.py` next to copies of the real `.py` files, so jedi and mypy can follow imports of uncompiled `.coco` modules; results in the mirror are mapped back to the real files.
- `typecheck.py`: optional mypy run over the compiled document in the mirror (setting `mypy`), on open/save in its own thread.
- `symbols.py`: document symbols from the compiled AST; regex index for workspace symbols and cross-file fallbacks.
- `docs.py`: lookup/formatting of the generated Coconut docs; `cli.py` and `mcp.py` reuse everything above in-process via `cli.Engine`.

Keep the server compatible with Python 3.8+ (no newer syntax) and free of required third-party dependencies.

## Testing

```bash
cd server && python -m pytest tests            # needs: pip install -r server/requirements.txt pytest
COCONUT_TEST_PYTHON=$(which python) xvfb-run -a npm run test:vscode   # after npm install && python scripts/vendor.py
claude plugin validate .                       # plugin manifests
```

Add an end-to-end test in `server/tests/test_server.py` for every LSP feature change. The skill's ```` ```coconut ```` examples and `snippets.json` are compiled by `test_units.py`, so they must compile without warnings/deprecations. Check UX changes in a real VS Code too: the integration tests run headless under `xvfb-run`, and ImageMagick's `import -window root` can screenshot the Xvfb display.

## Releasing

Bump `version` in `package.json` (and `.claude-plugin/plugin.json`), add a `CHANGELOG.md` entry, then `make publish` (VS Code Marketplace + Open VSX). Sublime Text users get updates from Package Control via git tags.
