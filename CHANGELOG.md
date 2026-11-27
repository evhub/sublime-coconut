# Changelog

## 2.3.1

- The language server prefers Coconut's own `coconut --lsp` only when it's the full-featured server merged into Coconut (`coconut-develop` 3.2.0.post0.dev20 and later). Older `coconut --lsp` versions do less than the bundled server, so the bundled server runs instead (setting `coconut.languageServer.server` to `"coconut"` still forces Coconut's).
- The Claude Code plugin now lives in the Coconut repository: `/plugin marketplace add evhub/coconut`.

## 2.3.0

- **New: language server support.** The editor packages run Coconut's own language server (`coconut --lsp`, from `coconut[lsp]`) when the installed Coconut has one, and otherwise a language server bundled with both the VS Code extension and the Sublime Text package, providing:
  - compiler errors and warnings as you type, plus pyflakes linting of the compiled code, mapped back to the Coconut source;
  - optional mypy type checking (`coconut.languageServer.mypy`), mapped back to the Coconut source;
  - hover with types, signatures, and docstrings, and Coconut's own documentation for built-ins, keywords, and operators;
  - completions (even while the file doesn't compile) and signature help;
  - go to definition (including across `.coco` files), type definition, references, document highlights, and rename;
  - document outline and workspace symbols;
  - quick fixes: remove unused imports, suppress warnings with `# NOQA`.
- VS Code: new commands to show the compiled Python side by side (live-updating), run or compile the current file, open the Coconut interpreter, and install Coconut; a status bar item showing the Coconut version in use; new settings `coconut.target`, `coconut.strict`, and `coconut.languageServer.*`. The language server uses the interpreter selected in the Python extension.
- Sublime Text: the language server starts automatically when the [LSP package](https://packagecontrol.io/packages/LSP) is installed; new "Run file" and "Check file/project for errors" build variants.
- AI agents: an MCP server and a command-line interface (`check`, `compile`, `hover`, `definition`, `references`, `symbols`, `docs`).
- Highlight `final`, lazy imports, `prepattern`, `datamaker`, `reveal_type`, `reveal_locals`, `TYPE_CHECKING`, `py_oct`, `py_repr`, and `py_dict`.
- Snippets use modern syntax (`match`/`case`, `=>` statement lambdas); new `matchcase`, `casedef`, `data`, and `where` snippets.
- VS Code: requires VS Code 1.82 or newer.

## 2.2.4

- Added `case def`, `CoconutWarning`, `py_min`, and `py_max` highlighting.
