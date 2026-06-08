import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.app.agent import handle_chat


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "http://localhost:3000"))
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "server": "stdlib-dev"})
            return
        self._send_json(404, {"detail": "Not found"})

    def do_POST(self):
        if self.path != "/chat":
            self._send_json(404, {"detail": "Not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = handle_chat(payload.get("messages", []), payload.get("current_flow"))
            self._send_json(200, result.to_dict())
        except Exception as exc:
            self._send_json(500, {"role": "assistant", "content": str(exc), "flow": "error", "sources": [], "suggested_replies": []})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("PartSelect stdlib dev server running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
