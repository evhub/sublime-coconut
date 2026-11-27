"""A tiny synchronous LSP client for testing the server end to end over stdio."""

import json
import os
import queue
import subprocess
import sys
import threading

SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "coconut_language_server.py")


class LspClient(object):

    def __init__(self, root, init_options=None):
        self.proc = subprocess.Popen(
            # these tests are for the bundled server, even where 'coconut --lsp' is installed
            [sys.executable, SERVER, "--server", "bundled"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.next_id = 0
        self.responses = {}
        self.notifications = queue.Queue()
        self.cond = threading.Condition()
        self.reader = threading.Thread(target=self._read)
        self.reader.daemon = True
        self.reader.start()
        self.stderr_lines = []
        self.err_reader = threading.Thread(target=self._read_err)
        self.err_reader.daemon = True
        self.err_reader.start()
        self.root = root
        self.init_result = self.request("initialize", {
            "processId": os.getpid(),
            "rootUri": self.uri(root),
            "workspaceFolders": [{"uri": self.uri(root), "name": "root"}],
            "capabilities": {},
            "initializationOptions": init_options or {},
        })
        self.notify("initialized", {})

    @staticmethod
    def uri(path):
        from coconut_ls.uris import path_to_uri
        return path_to_uri(path)

    def _read_err(self):
        for line in self.proc.stderr:
            self.stderr_lines.append(line.decode("utf-8", "replace"))

    def _read(self):
        stream = self.proc.stdout
        while True:
            headers = {}
            while True:
                line = stream.readline()
                if not line:
                    return
                line = line.decode("ascii").strip()
                if not line:
                    break
                key, value = line.split(":", 1)
                headers[key.lower()] = value.strip()
            body = stream.read(int(headers["content-length"]))
            msg = json.loads(body.decode("utf-8"))
            if "id" in msg and "method" not in msg:
                with self.cond:
                    self.responses[msg["id"]] = msg
                    self.cond.notify_all()
            elif "id" in msg:
                # server -> client request: answer with null
                self._send({"jsonrpc": "2.0", "id": msg["id"], "result": None})
            else:
                self.notifications.put(msg)

    def _send(self, msg):
        body = json.dumps(msg).encode("utf-8")
        self.proc.stdin.write(b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body)
        self.proc.stdin.flush()

    def request(self, method, params, timeout=60):
        self.next_id += 1
        msg_id = self.next_id
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
        with self.cond:
            ok = self.cond.wait_for(lambda: msg_id in self.responses, timeout)
        if not ok:
            raise AssertionError("timed out waiting for " + method + "\nstderr:\n" + "".join(self.stderr_lines))
        response = self.responses.pop(msg_id)
        if "error" in response:
            raise LspError(response["error"])
        return response.get("result")

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def wait_notification(self, method, predicate=None, timeout=60):
        import time
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise AssertionError("timed out waiting for " + method + "\nstderr:\n" + "".join(self.stderr_lines))
            try:
                msg = self.notifications.get(timeout=remaining)
            except queue.Empty:
                continue
            if msg["method"] == method and (predicate is None or predicate(msg["params"])):
                return msg["params"]

    def open(self, path, text, version=1):
        uri = self.uri(path)
        self.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": "coconut", "version": version, "text": text}})
        return uri

    def change(self, uri, text, version):
        self.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]})

    def diagnostics(self, uri, version=None, timeout=60):
        return self.wait_notification(
            "textDocument/publishDiagnostics",
            lambda p: p["uri"] == uri and (version is None or p.get("version") == version),
            timeout,
        )["diagnostics"]

    def close(self):
        try:
            self.request("shutdown", None, timeout=10)
            self.notify("exit", None)
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


class LspError(Exception):
    def __init__(self, error):
        super(LspError, self).__init__(error.get("message"))
        self.error = error
