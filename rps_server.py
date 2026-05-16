"""
rps_server.py — RPS Swarm Arena Server
=======================================
Serves the RPS game at http://localhost:8000 with optional
Python swarm backend API endpoints.

Routes:
  /              — RPS game HTML (rps_app.html)
  /api/start     — Start a new game (POST)
  /api/move      — Play a move (POST)
  /api/state     — Get current game state (GET)
  /api/events    — SSE stream of swarm agent events (GET)
  /api/stats     — Game statistics (GET)

Usage:
    python3 rps_server.py
    # Open http://localhost:8000 in your browser
"""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

# ── Import the RPS swarm engine ────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rps_swarm import create_engine
from mock_swarm import EventHook

BASE = os.path.dirname(os.path.abspath(__file__))
RPS_HTML_PATH = os.path.join(BASE, "rps_app.html")


# ════════════════════════════════════════════════════════════════
# SWARM ENGINE (singleton with SSE streaming)
# ════════════════════════════════════════════════════════════════

class RpsGameServer:
    """Manages the RPS game session and streams events to SSE clients."""

    def __init__(self):
        self.engine = None
        self._lock = threading.Lock()
        self._sse_clients = []
        self._event_queue = []

    def reset(self, best_of: int = 5):
        """Reset the game with a new engine instance."""
        self._event_queue = []
        new_engine = create_engine(best_of=best_of)

        # Wire up event hook to capture all events
        def capture_event(event_type: str, data: dict):
            event = {"type": event_type, "data": data, "timestamp": time.time()}
            self._event_queue.append(event)
            # Forward to SSE clients (thread-safe)
            with self._lock:
                clients = list(self._sse_clients)
            dead_clients = []
            for client in clients:
                try:
                    client(event_type, data)
                except Exception:
                    dead_clients.append(client)
            if dead_clients:
                with self._lock:
                    for dc in dead_clients:
                        if dc in self._sse_clients:
                            self._sse_clients.remove(dc)

        new_engine.on_event(capture_event)
        self.engine = new_engine

    def register_sse(self, callback):
        """Register an SSE client callback."""
        with self._lock:
            self._sse_clients.append(callback)

    def unregister_sse(self, callback):
        """Unregister an SSE client."""
        with self._lock:
            if callback in self._sse_clients:
                self._sse_clients.remove(callback)


GAME_SERVER = RpsGameServer()


# ════════════════════════════════════════════════════════════════
# HTTP SERVER
# ════════════════════════════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    """HTTP handler that serves the RPS game UI and API endpoints."""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._serve_html(RPS_HTML_PATH)
        elif parsed.path == "/api/state":
            self._handle_get_state()
        elif parsed.path == "/api/stats":
            self._handle_get_stats()
        elif parsed.path == "/api/events":
            self._handle_sse()
        elif parsed.path == "/api/agents":
            self._handle_list_agents()
        elif parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/start":
            self._handle_start_game()
        elif parsed.path == "/api/move":
            self._handle_player_move()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_body(self) -> dict:
        """Read and parse JSON request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _serve_html(self, path):
        """Serve an HTML file."""
        if not os.path.exists(path):
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"UI file not found at {path}".encode())
            return

        with open(path, "r") as f:
            html = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    # ── API Handlers ──────────────────────────────────────────

    def _handle_start_game(self):
        """POST /api/start — Start a new game."""
        body = self._read_body()
        best_of = body.get("best_of", 5)
        GAME_SERVER.reset(best_of=best_of)

        if GAME_SERVER.engine:
            state = GAME_SERVER.engine.start_game()
            self._send_json({"status": "ok", "state": state})
        else:
            self._send_json({"status": "error", "message": "Engine failed to initialize"}, 500)

    def _handle_player_move(self):
        """POST /api/move — Play a move."""
        body = self._read_body()
        choice = body.get("choice", "")
        agent_hints = body.get("agent_hints", {})

        if not GAME_SERVER.engine:
            self._send_json({"status": "error", "message": "No game in progress. Call /api/start first."}, 400)
            return

        result = GAME_SERVER.engine.player_move(choice)
        if isinstance(result, dict) and "error" in result:
            self._send_json({"status": "error", "message": result["error"]}, 400)
        else:
            self._send_json({"status": "ok", "result": result})

    def _handle_get_state(self):
        """GET /api/state — Get current game state."""
        if not GAME_SERVER.engine:
            self._send_json({"status": "error", "message": "No game in progress."}, 400)
            return

        state = GAME_SERVER.engine.get_state()
        self._send_json({"status": "ok", "state": state})

    def _handle_get_stats(self):
        """GET /api/stats — Get current game statistics."""
        if not GAME_SERVER.engine:
            self._send_json({"status": "error", "message": "No game in progress."}, 400)
            return

        stats = GAME_SERVER.engine.get_stats()
        summary = GAME_SERVER.engine.get_summary()
        self._send_json({"status": "ok", "stats": stats, "summary": summary})

    def _handle_list_agents(self):
        """GET /api/agents — List registered swarm agents from the live engine."""
        if not GAME_SERVER.engine or not GAME_SERVER.engine.registry:
            self._send_json({"status": "ok", "agents": []})
            return

        registry = GAME_SERVER.engine.registry
        agents = []
        for name, agent in registry.all().items():
            agents.append({
                "name": name,
                "instructions": agent.instructions[:80],
                "tool_count": len(agent.functions),
                "tools": [f.__name__ for f in agent.functions],
                "phase": registry.get_phase(name),
            })

        self._send_json({"status": "ok", "agents": agents})

    def _handle_sse(self):
        """GET /api/events — SSE stream of swarm agent events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors_headers()
        self.end_headers()

        disconnected = [False]

        def send(event_type, data):
            if disconnected[0]:
                return
            try:
                payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                disconnected[0] = True

        # Register client
        GAME_SERVER.register_sse(send)

        # Send connected event with current state
        if GAME_SERVER.engine:
            send("connected", {
                "status": "ok",
                "agents": len(GAME_SERVER.engine.registry.all()) if GAME_SERVER.engine.registry else 0,
            })

            # Replay recent events
            for ev in GAME_SERVER._event_queue[-20:]:
                if disconnected[0]:
                    break
                send(ev["type"], ev["data"])

        # Keep connection alive and wait for events
        try:
            while not disconnected[0]:
                time.sleep(1)
                # Send keepalive
                send("keepalive", {"timestamp": time.time()})
        except (BrokenPipeError, ConnectionResetError):
            disconnected[0] = True
        finally:
            GAME_SERVER.unregister_sse(send)
            # Keep draining the socket on close
            try:
                self.connection.close()
            except Exception:
                pass

    def log_message(self, format, *args):
        """Quiet logging — only log non-SSE requests."""
        path = str(args[0]) if args else ""
        if "/api/events" not in path and "keepalive" not in path:
            super().log_message(format, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Allow concurrent connections (UI page + SSE stream + API calls)."""
    allow_reuse_address = True
    daemon_threads = True


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main():
    port = 8000
    server = ThreadedHTTPServer(("", port), Handler)
    html_exists = os.path.exists(RPS_HTML_PATH)

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║   🎮  RPS Swarm Arena Server                     ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print(f"  ║   Game:      http://localhost:{port}                  ║")
    print(f"  ║   Agents:    http://localhost:{port}/api/agents        ║")
    print(f"  ║   Events:    http://localhost:{port}/api/events        ║")
    print(f"  ║   State:     http://localhost:{port}/api/state         ║")
    print(f"  ║   Stats:     http://localhost:{port}/api/stats         ║")
    print(f"  ║   HTML file: {'✅' if html_exists else '❌'} rps_app.html                        ║")
    print("  ║   Ctrl+C to stop                                 ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    # Initialize a default game so API is ready
    GAME_SERVER.reset(best_of=5)
    if GAME_SERVER.engine:
        GAME_SERVER.engine.start_game()
        print("  🎮 Default game initialized (Best of 5)")
        print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
