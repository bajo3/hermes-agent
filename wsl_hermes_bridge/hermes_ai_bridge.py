from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.getenv("HERMES_AI_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.getenv("HERMES_AI_BRIDGE_PORT", "8766"))
TOKEN = os.getenv("HERMES_AI_BRIDGE_TOKEN", "")
HERMES_BIN = os.getenv("HERMES_CLI_PATH", "/home/bajo31/.local/bin/hermes")
HERMES_CWD = os.getenv("HERMES_CLI_CWD", "/home/bajo31/.hermes/hermes-agent")
TIMEOUT = int(os.getenv("HERMES_CLI_TIMEOUT", "120"))


class HermesBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_json({"error": "not found"}, status=404)
            return
        self.send_json({"ok": True})

    def do_POST(self) -> None:
        if self.path != "/interpret":
            self.send_json({"error": "not found"}, status=404)
            return
        if TOKEN and self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_json({"error": "unauthorized"}, status=401)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            prompt = payload["prompt"]
            provider = payload.get("provider") or "openai-codex"
            model = payload.get("model") or "gpt-5.5"
            command = [HERMES_BIN, "-z", prompt, "--provider", provider, "--model", model]
            result = subprocess.run(
                command,
                cwd=HERMES_CWD,
                text=True,
                capture_output=True,
                timeout=TIMEOUT,
                check=False,
            )
            if result.returncode != 0:
                self.send_json({"error": (result.stderr or result.stdout or "Hermes CLI failed").strip()}, status=502)
                return
            self.send_json({"output": result.stdout.strip()})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), HermesBridgeHandler)
    print(f"Hermes AI bridge listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
