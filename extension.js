// VS Code extension entry point: starts the Coconut language server (coconut --lsp)
//  for .coco files. Syntax highlighting and snippets are contributed declaratively in package.json.

"use strict";

const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client = null;

function getServerCommand() {
    const config = vscode.workspace.getConfiguration("coconut.languageServer");
    const command = config.get("command");
    if (Array.isArray(command) && command.length > 0) {
        return command;
    }
    return ["coconut", "--lsp"];
}

async function startClient() {
    const config = vscode.workspace.getConfiguration("coconut.languageServer");
    if (!config.get("enabled", true)) {
        return;
    }
    const [command, ...args] = getServerCommand();
    const serverOptions = {
        command: command,
        args: args,
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [
            { scheme: "file", language: "coconut" },
            { scheme: "untitled", language: "coconut" },
        ],
    };
    client = new LanguageClient("coconut", "Coconut Language Server", serverOptions, clientOptions);
    try {
        await client.start();
    } catch (err) {
        client = null;
        const install = "How to Install";
        const choice = await vscode.window.showWarningMessage(
            "Couldn't start the Coconut language server (" + command + "). "
            + "Syntax highlighting will still work, but to get errors, hover, completions, and go to definition, "
            + "install it with 'pip install \"coconut[lsp]\"' (or set coconut.languageServer.command).",
            install,
        );
        if (choice === install) {
            vscode.env.openExternal(vscode.Uri.parse("https://coconut.readthedocs.io/en/latest/DOCS.html#language-server"));
        }
    }
}

async function stopClient() {
    if (client !== null) {
        const oldClient = client;
        client = null;
        await oldClient.stop();
    }
}

async function activate(context) {
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(async (event) => {
            if (event.affectsConfiguration("coconut.languageServer")) {
                await stopClient();
                await startClient();
            }
        }),
        vscode.commands.registerCommand("coconut.restartLanguageServer", async () => {
            await stopClient();
            await startClient();
        }),
    );
    await startClient();
}

function deactivate() {
    return stopClient();
}

module.exports = { activate, deactivate };
