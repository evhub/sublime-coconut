// VS Code extension entry point for Coconut.
//
// Syntax highlighting and snippets are contributed declaratively in package.json. This file starts
// the Coconut language server bundled in ./server (run with a Python interpreter that has Coconut
// installed) and adds commands for running, compiling, and viewing the compiled Python of Coconut files.

"use strict";

const path = require("path");
const cp = require("child_process");
const vscode = require("vscode");
const { LanguageClient, TransportKind, State } = require("vscode-languageclient/node");

const COMPILED_SCHEME = "coconut-compiled";
const DOCS_URL = "https://coconut.readthedocs.io/en/latest/DOCS.html";

let client = null;
let extensionContext = null;
let statusItem = null;
let lastStatus = null;
let outputChannel = null;
let restarting = Promise.resolve();
const compiledViews = new vscode.EventEmitter();

function config(resource) {
    return vscode.workspace.getConfiguration("coconut", resource === undefined ? null : resource);
}

function expandVariables(value, resource) {
    const folder = (resource && vscode.workspace.getWorkspaceFolder(resource))
        || (vscode.workspace.workspaceFolders || [])[0];
    return value
        .replace(/\$\{workspaceFolder\}/g, folder ? folder.uri.fsPath : "")
        .replace(/\$\{userHome\}/g, require("os").homedir())
        .replace(/^~(?=$|[\\/])/, require("os").homedir());
}

// Find the Python interpreter to use: the coconut.languageServer.pythonPath setting, else the
// interpreter selected in the Python extension, else python3/python on the PATH.
async function getPython(resource) {
    const configured = config(resource).get("languageServer.pythonPath");
    if (configured) {
        return expandVariables(configured, resource);
    }
    const pythonExt = vscode.extensions.getExtension("ms-python.python");
    if (pythonExt) {
        try {
            const api = pythonExt.isActive ? pythonExt.exports : await pythonExt.activate();
            if (api && api.environments) {
                const envPath = api.environments.getActiveEnvironmentPath(resource);
                const env = await api.environments.resolveEnvironment(envPath);
                if (env && env.executable && env.executable.uri) {
                    return env.executable.uri.fsPath;
                }
                if (envPath && envPath.path) {
                    return envPath.path;
                }
            } else if (api && api.settings && api.settings.getExecutionDetails) {
                const details = api.settings.getExecutionDetails(resource);
                if (details && details.execCommand && details.execCommand[0]) {
                    return details.execCommand[0];
                }
            }
        } catch (err) {
            log("Couldn't get the interpreter from the Python extension: " + err);
        }
    }
    return process.platform === "win32" ? "python" : "python3";
}

function activeResource() {
    const editor = vscode.window.activeTextEditor;
    return editor ? editor.document.uri : undefined;
}

function log(message) {
    if (outputChannel) {
        outputChannel.appendLine(message);
    }
}

async function getServerCommand() {
    const command = config().get("languageServer.command");
    if (Array.isArray(command) && command.length > 0) {
        return command.map((part) => expandVariables(part, activeResource()));
    }
    const python = await getPython(activeResource());
    return [python, extensionContext.asAbsolutePath(path.join("server", "coconut_language_server.py"))];
}

function serverSettings() {
    const cfg = config();
    return {
        target: cfg.get("target"),
        strict: cfg.get("strict"),
        lint: cfg.get("languageServer.lint"),
        mypy: cfg.get("languageServer.mypy"),
        compileTimeout: cfg.get("languageServer.compileTimeout"),
    };
}

async function startClient() {
    if (!config().get("languageServer.enabled", true)) {
        updateStatusItem();
        return;
    }
    const [command, ...args] = await getServerCommand();
    log("Starting Coconut language server: " + [command, ...args].join(" "));
    const serverOptions = {
        command: command,
        args: args,
        transport: TransportKind.stdio,
        options: { env: Object.assign({}, process.env, { PYTHONIOENCODING: "utf-8" }) },
    };
    const clientOptions = {
        documentSelector: [
            { scheme: "file", language: "coconut" },
            { scheme: "untitled", language: "coconut" },
        ],
        synchronize: { configurationSection: "coconut" },
        initializationOptions: serverSettings(),
        outputChannel: outputChannel,
    };
    const newClient = new LanguageClient("coconut", "Coconut Language Server", serverOptions, clientOptions);
    newClient.onDidChangeState((event) => {
        if (event.newState === State.Stopped) {
            updateStatusItem();
        }
    });
    client = newClient;
    try {
        await newClient.start();
    } catch (err) {
        client = null;
        log("Failed to start the language server: " + err);
        updateStatusItem({ failed: true, python: command });
        const choice = await vscode.window.showWarningMessage(
            "Couldn't start the Coconut language server with '" + command + "'. "
            + "Syntax highlighting still works; for errors, hover, completions, and go to definition, "
            + "select a Python interpreter that has Coconut installed (or set coconut.languageServer.pythonPath).",
            "Select Interpreter", "Open Settings",
        );
        if (choice === "Select Interpreter") {
            vscode.commands.executeCommand("python.setInterpreter");
        } else if (choice === "Open Settings") {
            vscode.commands.executeCommand("workbench.action.openSettings", "coconut.languageServer");
        }
        return;
    }
    newClient.onNotification("coconut/status", (status) => onStatus(status));
    newClient.onNotification("coconut/compiled", (params) => {
        compiledViews.fire(compiledUriFor(vscode.Uri.parse(params.uri)));
    });
}

async function stopClient() {
    if (client !== null) {
        const oldClient = client;
        client = null;
        try {
            await oldClient.stop();
        } catch (err) {
            log("Error stopping the language server: " + err);
        }
    }
}

function restartClient() {
    restarting = restarting.then(async () => {
        await stopClient();
        lastStatus = null;
        await startClient();
    });
    return restarting;
}

// ---------------------------------------------------------------------------------------------
// status bar

function onStatus(status) {
    lastStatus = status;
    updateStatusItem();
    if (!status.coconut_version && !onStatus.warned) {
        onStatus.warned = true;
        const install = "Install Coconut";
        vscode.window.showWarningMessage(
            "Coconut isn't installed for " + status.python_executable
            + ". Install it to get errors, hover, completions, and go to definition for Coconut files.",
            install, "Select Interpreter",
        ).then((choice) => {
            if (choice === install) {
                vscode.commands.executeCommand("coconut.installCoconut");
            } else if (choice === "Select Interpreter") {
                vscode.commands.executeCommand("python.setInterpreter");
            }
        });
    }
}

function updateStatusItem(extra) {
    if (!statusItem) {
        return;
    }
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "coconut") {
        statusItem.hide();
        return;
    }
    if (!config().get("languageServer.enabled", true)) {
        statusItem.text = "$(circle-slash) Coconut";
        statusItem.tooltip = "The Coconut language server is disabled (coconut.languageServer.enabled)";
        statusItem.command = { command: "workbench.action.openSettings", title: "Settings", arguments: ["coconut.languageServer"] };
    } else if (extra && extra.failed) {
        statusItem.text = "$(error) Coconut";
        statusItem.tooltip = "The Coconut language server couldn't start with " + extra.python + ". Click to choose an interpreter.";
        statusItem.command = "python.setInterpreter";
    } else if (lastStatus && !lastStatus.coconut_version) {
        statusItem.text = "$(warning) Coconut not installed";
        statusItem.tooltip = "Coconut isn't installed for " + lastStatus.python_executable + ". Click to install it.";
        statusItem.command = "coconut.installCoconut";
    } else if (lastStatus) {
        statusItem.text = "$(check) Coconut " + lastStatus.coconut_version;
        const tooltip = new vscode.MarkdownString();
        tooltip.appendMarkdown("**Coconut " + lastStatus.coconut_version + "** (language server " + lastStatus.server_version + ")\n\n");
        tooltip.appendMarkdown("Python " + lastStatus.python_version + ": `" + lastStatus.python_executable + "`\n\n");
        tooltip.appendMarkdown("Code intelligence (jedi): " + (lastStatus.jedi ? "on" : "off") + "  \n");
        tooltip.appendMarkdown("Linting (pyflakes): " + (lastStatus.pyflakes_version ? "on" : "off") + "\n\n");
        tooltip.appendMarkdown("Click to show the compiled Python");
        statusItem.tooltip = tooltip;
        statusItem.command = "coconut.showCompiledPython";
    } else {
        statusItem.text = "$(sync~spin) Coconut";
        statusItem.tooltip = "Starting the Coconut language server...";
        statusItem.command = "coconut.showOutput";
    }
    statusItem.show();
}

// ---------------------------------------------------------------------------------------------
// compiled Python view

function compiledUriFor(sourceUri) {
    const parsed = path.parse(sourceUri.path);
    return vscode.Uri.from({
        scheme: COMPILED_SCHEME,
        path: path.posix.join(parsed.dir, parsed.name + ".py"),
        query: sourceUri.toString(),
    });
}

class CompiledContentProvider {
    constructor() {
        this.onDidChange = compiledViews.event;
    }

    async provideTextDocumentContent(uri) {
        if (client === null) {
            return "# The Coconut language server isn't running.\n";
        }
        const sourceUri = uri.query;
        let result;
        try {
            result = await client.sendRequest("coconut/compiled", { textDocument: { uri: sourceUri } });
        } catch (err) {
            return "# Couldn't get the compiled code: " + err + "\n";
        }
        if (!result || result.compiled === null || result.compiled === undefined) {
            const errors = (result && result.errors || []).map((e) => "#   line " + (e.range.start.line + 1) + ": " + e.message);
            return "# This file doesn't compile yet:\n" + errors.join("\n") + "\n";
        }
        if (!result.upToDate) {
            return "# NOTE: showing the last successfully compiled version (the current version has errors).\n" + result.compiled;
        }
        return result.compiled;
    }
}

async function showCompiledPython() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "coconut") {
        vscode.window.showInformationMessage("Open a Coconut file to see its compiled Python.");
        return;
    }
    const sourceLine = editor.selection.active.line;
    const doc = await vscode.workspace.openTextDocument(compiledUriFor(editor.document.uri));
    await vscode.languages.setTextDocumentLanguage(doc, "python");
    const shown = await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true, preview: true });
    revealCompiledLine(shown, sourceLine);
}

// scroll the compiled view to the code generated from the given (0-based) source line
function revealCompiledLine(compiledEditor, sourceLine) {
    const marker = "#" + (sourceLine + 1) + " (line in Coconut source)";
    const doc = compiledEditor.document;
    for (let i = 0; i < doc.lineCount; i++) {
        if (doc.lineAt(i).text.endsWith(marker)) {
            const range = new vscode.Range(i, 0, i, 0);
            compiledEditor.revealRange(range, vscode.TextEditorRevealType.InCenter);
            compiledEditor.selection = new vscode.Selection(range.start, range.start);
            return;
        }
    }
}

// ---------------------------------------------------------------------------------------------
// terminal commands

function shellQuote(arg) {
    if (process.platform === "win32") {
        return /[\s"&|<>^]/.test(arg) ? "\"" + arg.replace(/"/g, "\\\"") + "\"" : arg;
    }
    return /^[\w@%+=:,./-]+$/.test(arg) ? arg : "'" + arg.replace(/'/g, "'\\''") + "'";
}

let terminal = null;

async function runInTerminal(args, resource, cwd) {
    const python = await getPython(resource);
    if (terminal === null || terminal.exitStatus !== undefined) {
        terminal = vscode.window.createTerminal({ name: "Coconut", cwd: cwd });
    }
    terminal.show();
    const prefix = process.platform === "win32" && /\s/.test(python) ? "& " : "";
    terminal.sendText(prefix + [python, ...args].map(shellQuote).join(" "));
}

function compileArgs() {
    const args = [];
    const target = config().get("target");
    if (target) {
        args.push("--target", target);
    }
    if (config().get("strict")) {
        args.push("--strict");
    }
    return args;
}

async function activeCoconutFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "coconut") {
        vscode.window.showInformationMessage("Open a Coconut file first.");
        return null;
    }
    if (editor.document.isUntitled) {
        vscode.window.showInformationMessage("Save the file first.");
        return null;
    }
    if (editor.document.isDirty) {
        await editor.document.save();
    }
    return editor.document.uri;
}

async function runFile() {
    const uri = await activeCoconutFile();
    if (uri) {
        await runInTerminal(["-m", "coconut", "--run", "--no-write", ...compileArgs(), uri.fsPath], uri, path.dirname(uri.fsPath));
    }
}

async function compileFile() {
    const uri = await activeCoconutFile();
    if (uri) {
        await runInTerminal(["-m", "coconut", ...compileArgs(), uri.fsPath], uri, path.dirname(uri.fsPath));
    }
}

async function openInterpreter() {
    const resource = activeResource();
    const folder = (resource && vscode.workspace.getWorkspaceFolder(resource)) || (vscode.workspace.workspaceFolders || [])[0];
    await runInTerminal(["-m", "coconut", "--interact", ...compileArgs()], resource, folder ? folder.uri.fsPath : undefined);
}

async function installCoconut() {
    const python = await getPython(activeResource());
    const task = new vscode.Task(
        { type: "process", task: "install-coconut" },
        vscode.TaskScope.Workspace,
        "Install Coconut",
        "coconut",
        new vscode.ProcessExecution(python, ["-m", "pip", "install", "--upgrade", "coconut"]),
    );
    const execution = await vscode.tasks.executeTask(task);
    const disposable = vscode.tasks.onDidEndTaskProcess((event) => {
        if (event.execution === execution) {
            disposable.dispose();
            if (event.exitCode === 0) {
                onStatus.warned = false;
                vscode.window.showInformationMessage("Coconut installed; restarting the language server.");
                restartClient();
            } else {
                vscode.window.showErrorMessage("Installing Coconut failed (see the terminal for details).");
            }
        }
    });
}

// ---------------------------------------------------------------------------------------------

async function activate(context) {
    extensionContext = context;
    outputChannel = vscode.window.createOutputChannel("Coconut");
    statusItem = vscode.window.createStatusBarItem("coconut.status", vscode.StatusBarAlignment.Right, 100);
    statusItem.name = "Coconut";
    context.subscriptions.push(
        outputChannel,
        statusItem,
        vscode.workspace.registerTextDocumentContentProvider(COMPILED_SCHEME, new CompiledContentProvider()),
        vscode.window.onDidChangeActiveTextEditor(() => updateStatusItem()),
        vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration("coconut.languageServer.enabled")
                || event.affectsConfiguration("coconut.languageServer.pythonPath")
                || event.affectsConfiguration("coconut.languageServer.command")) {
                restartClient();
            }
        }),
        vscode.commands.registerCommand("coconut.restartLanguageServer", () => restartClient()),
        vscode.commands.registerCommand("coconut.showCompiledPython", showCompiledPython),
        vscode.commands.registerCommand("coconut.runFile", runFile),
        vscode.commands.registerCommand("coconut.compileFile", compileFile),
        vscode.commands.registerCommand("coconut.openInterpreter", openInterpreter),
        vscode.commands.registerCommand("coconut.installCoconut", installCoconut),
        vscode.commands.registerCommand("coconut.showOutput", () => outputChannel.show()),
        vscode.commands.registerCommand("coconut.openDocumentation", () => vscode.env.openExternal(vscode.Uri.parse(DOCS_URL))),
    );

    // restart when the selected Python interpreter changes
    const pythonExt = vscode.extensions.getExtension("ms-python.python");
    if (pythonExt) {
        Promise.resolve(pythonExt.isActive ? pythonExt.exports : pythonExt.activate()).then((api) => {
            if (api && api.environments && api.environments.onDidChangeActiveEnvironmentPath) {
                context.subscriptions.push(api.environments.onDidChangeActiveEnvironmentPath(() => {
                    if (!config().get("languageServer.pythonPath") && client !== null) {
                        restartClient();
                    }
                }));
            }
        }, () => undefined);
    }

    updateStatusItem();
    await startClient();
}

function deactivate() {
    return stopClient();
}

module.exports = { activate, deactivate };
