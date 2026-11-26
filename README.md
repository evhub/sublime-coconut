# Sublime Text and VSCode Packages for Coconut

This repository contains [Coconut](https://github.com/evhub/coconut) syntax highlighting for both [Sublime Text](https://packagecontrol.io/packages/Coconut) and [Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=evhub.coconut). For installation instructions, see [Coconut's documentation](https://coconut.readthedocs.io/en/master/DOCS.html#syntax-highlighting).

The VS Code extension also includes a client for the [Coconut language server](https://coconut.readthedocs.io/en/latest/DOCS.html#language-server), which provides live errors and warnings, hover information, completions, go to definition, and document outlines. To enable it, install the language server with `pip install "coconut[lsp]"` (Python 3.9+). If `coconut` isn't on your `PATH` (e.g. it's installed in a virtual environment), set `coconut.languageServer.command` to e.g. `["/path/to/venv/bin/python", "-m", "coconut.lsp"]`. The language server can be disabled with `coconut.languageServer.enabled`.

Credits:
- VSCode integration based on [kobarity](https://github.com/kobarity)'s [Coconut VSCode package](https://github.com/kobarity/vsce-coconut).
- Python syntax highlighting based on [petervaro](https://github.com/petervaro)'s [Python highlighter](https://github.com/petervaro/python).
