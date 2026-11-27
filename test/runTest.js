// Runs the extension's integration tests in a real VS Code instance.
//   COCONUT_TEST_PYTHON=/path/to/python-with-coconut node test/runTest.js
// (on Linux without a display, run under xvfb-run)

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { runTests } = require("@vscode/test-electron");

async function main() {
    const extensionDevelopmentPath = path.resolve(__dirname, "..");
    const extensionTestsPath = path.resolve(__dirname, "suite", "index.js");
    // copy the fixture so tests can't modify the checked-in files
    const workspace = fs.mkdtempSync(path.join(os.tmpdir(), "coconut-vscode-test-"));
    fs.copyFileSync(path.join(__dirname, "fixture", "main.coco"), path.join(workspace, "main.coco"));
    fs.mkdirSync(path.join(workspace, ".vscode"));
    fs.writeFileSync(path.join(workspace, ".vscode", "settings.json"), JSON.stringify({
        "coconut.languageServer.pythonPath": process.env.COCONUT_TEST_PYTHON || (process.platform === "win32" ? "python" : "python3"),
    }));
    try {
        await runTests({
            extensionDevelopmentPath,
            extensionTestsPath,
            launchArgs: [workspace, "--disable-extensions", "--disable-workspace-trust", "--skip-welcome", "--skip-release-notes"],
        });
    } catch (err) {
        console.error("Integration tests failed:", err);
        process.exit(1);
    }
}

main();
