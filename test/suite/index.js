// Integration tests: exercise the language server through VS Code's own APIs.

"use strict";

const assert = require("assert");
const path = require("path");
const vscode = require("vscode");

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(description, fn, timeout = 60000) {
    const deadline = Date.now() + timeout;
    let last;
    while (Date.now() < deadline) {
        last = await fn();
        if (last) {
            return last;
        }
        await sleep(250);
    }
    throw new Error("timed out waiting for " + description + " (last value: " + JSON.stringify(last) + ")");
}

function positionOf(doc, needle, offset = 0) {
    const index = doc.getText().indexOf(needle);
    assert.ok(index >= 0, "couldn't find " + needle);
    return doc.positionAt(index + offset);
}

function hoverText(hovers) {
    return hovers.map((h) => h.contents.map((c) => (typeof c === "string" ? c : c.value)).join("\n")).join("\n");
}

// some features only exist in the server bundled with the extension
const BUNDLED = (process.env.COCONUT_TEST_SERVER || "bundled") === "bundled";

const tests = {
    async "reports diagnostics"(doc) {
        const diags = await waitFor("diagnostics", () => {
            const d = vscode.languages.getDiagnostics(doc.uri);
            return d.length > 0 ? d : null;
        });
        assert.ok(diags.some((d) => d.message.includes("sys")), JSON.stringify(diags.map((d) => d.message)));
    },

    async "hover shows Coconut docs for built-ins"(doc) {
        const hovers = await vscode.commands.executeCommand("vscode.executeHoverProvider", doc.uri, positionOf(doc, "fmap", 1));
        const text = hoverText(hovers);
        assert.ok(text.includes("fmap"), text);
        if (BUNDLED) {
            assert.ok(text.includes("coconut.readthedocs.io"), text);
        }
    },

    async "hover on user code"(doc) {
        const hovers = await vscode.commands.executeCommand("vscode.executeHoverProvider", doc.uri, positionOf(doc, "p.norm", 3));
        assert.ok(hoverText(hovers).includes("norm"));
    },

    async "go to definition"(doc) {
        const locs = await vscode.commands.executeCommand("vscode.executeDefinitionProvider", doc.uri, positionOf(doc, "Point(3", 1));
        assert.strictEqual(locs.length, 1);
        const loc = locs[0];
        const range = loc.range || loc.targetSelectionRange || loc.targetRange;
        assert.strictEqual(range.start.line, 3);
    },

    async "document symbols"(doc) {
        const symbols = await vscode.commands.executeCommand("vscode.executeDocumentSymbolProvider", doc.uri);
        const names = symbols.map((s) => s.name);
        assert.ok(["Point", "add"].every((n) => names.includes(n)), JSON.stringify(names));
        if (BUNDLED) {
            assert.deepStrictEqual(names, ["Point", "add", "p"]);
            assert.deepStrictEqual(symbols[0].children.map((s) => s.name), ["norm"]);
        }
    },

    async "completion while typing"(doc, editor) {
        const end = doc.lineAt(doc.lineCount - 1).range.end;
        await editor.edit((b) => b.insert(end, "\np.no"));
        const pos = doc.lineAt(doc.lineCount - 1).range.end;
        const list = await waitFor("completions", async () => {
            const result = await vscode.commands.executeCommand("vscode.executeCompletionItemProvider", doc.uri, pos);
            return result.items.some((i) => (i.label.label || i.label) === "norm") ? result : null;
        }, 20000);
        assert.ok(list);
        await vscode.commands.executeCommand("undo");
    },

    async "show compiled Python"(doc, editor) {
        await vscode.window.showTextDocument(doc);
        await vscode.commands.executeCommand("coconut.showCompiledPython");
        const compiled = await waitFor("compiled view", () => vscode.workspace.textDocuments.find(
            (d) => d.uri.scheme === "coconut-compiled" && d.getText().includes("class Point") && !d.getText().includes("(line in Coconut source)"),
        ), 20000);
        assert.strictEqual(compiled.languageId, "python");
    },
};

async function run() {
    const folder = vscode.workspace.workspaceFolders[0].uri.fsPath;
    const doc = await vscode.workspace.openTextDocument(path.join(folder, "main.coco"));
    const editor = await vscode.window.showTextDocument(doc);
    assert.strictEqual(doc.languageId, "coconut");
    const failures = [];
    for (const [name, test] of Object.entries(tests)) {
        try {
            await test(doc, editor);
            console.log("  ✓ " + name);
        } catch (err) {
            console.log("  ✗ " + name + ": " + (err && err.stack || err));
            failures.push(name);
        }
    }
    if (failures.length) {
        throw new Error(failures.length + " test(s) failed: " + failures.join(", "));
    }
}

module.exports = { run };
