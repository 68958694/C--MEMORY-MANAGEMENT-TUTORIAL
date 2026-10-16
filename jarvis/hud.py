"""Web HUD: an Iron Man style interface served on localhost.

The browser handles the microphone (Web Speech API) and the voice, so this mode
needs no audio packages. Use Chrome or Edge for speech recognition.
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jarvis import config, skills
from jarvis.brain import Brain

PAGE = Path(__file__).with_name("hud.html")


def serve(brain: Brain) -> None:
    lock = threading.Lock()  # one conversation, so handle one request at a time
    allowed_hosts = {f"{h}:{config.HUD_PORT}" for h in (config.HUD_HOST, "localhost", "127.0.0.1")}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = PAGE.read_text(encoding="utf-8").replace("{{NAME}}", config.NAME.upper()).replace(
                    "{{TITLE}}", config.USER_TITLE)
                self._send(200, "text/html; charset=utf-8", body.encode("utf-8"))
            elif self.path == "/api/status":
                self._json({"status": skills.system_status(), "ai": brain.use_claude})
            else:
                self._send(404, "text/plain", b"Not found")

        def do_POST(self):
            if self.path != "/api/ask":
                return self._send(404, "text/plain", b"Not found")
            # Only accept JSON from this page: browsers won't let other websites send a
            # JSON POST here without a CORS preflight (which we never approve), and the
            # Host check blocks DNS-rebinding tricks. Stops random sites driving JARVIS.
            if (self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json"
                    or self.headers.get("Host") not in allowed_hosts):
                return self._send(403, "text/plain", b"Forbidden")
            try:
                length = int(self.headers.get("Content-Length", 0))
                text = json.loads(self.rfile.read(length) or b"{}").get("text", "")
            except (ValueError, json.JSONDecodeError):
                return self._json({"error": "bad request"}, 400)
            with lock:
                reply = brain.respond(str(text)[:2000])
            self._json({"reply": reply})

        def _json(self, data, code=200):
            self._send(code, "application/json", json.dumps(data).encode("utf-8"))

        def _send(self, code, ctype, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass  # keep the terminal quiet

    try:
        server = ThreadingHTTPServer((config.HUD_HOST, config.HUD_PORT), Handler)
    except OSError as exc:
        print(f"[hud] Can't start on port {config.HUD_PORT} ({exc.strerror}). Is JARVIS already running?\n"
              "      Pick another port with: JARVIS_HUD_PORT=8800 python -m jarvis --hud")
        return
    url = f"http://{config.HUD_HOST}:{config.HUD_PORT}"
    print(f"[hud] {config.NAME} HUD running at {url}  (Ctrl+C to stop)")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[hud] Shutting down.")
    finally:
        server.server_close()
