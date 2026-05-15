"""
swarm_web.py — Real-time Swarm Pipeline Visualizer
===================================================
Serves a web UI at http://localhost:8000 that visualizes the
multi-agent handoff pipeline in real-time via Server-Sent Events.

Imports the mock swarm system from swarm_demo.py and runs it,
streaming each step (tool calls, agent messages, handoffs) to
the browser as they happen.

Usage:
    python3 swarm_web.py
    # Open http://localhost:8000 in your browser
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

# ── Import the agent pipeline ──────────────────────────────────
# We use the MockSwarm so no API key is needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# We import directly from swarm_demo to reuse Agent definitions
# Verify mock_swarm importable before starting
import mock_swarm
mock_swarm  # silence unused-import linter

# ── ClawTeam bridge (real ClawTeam integration + fallback) ──
from clawteam_bridge import get_bridge

# Determine the active bridge mode at startup
BRIDGE = get_bridge()
BRIDGE_MODE = BRIDGE.get_mode()


# ════════════════════════════════════════════════════════════════
# SWARM PIPELINE RUNNER (streams events step by step)
# ════════════════════════════════════════════════════════════════

def run_pipeline(event_callback):
    """
    Execute the handoff pipeline step by step, calling event_callback
    for each event so the SSE handler can stream them to the browser.

    Event types:
        agent_activated  - {"agent": name, "phase": "starting"|"busy"|"done"}
        tool_call        - {"agent": name, "tool": name, "arguments": dict}
        tool_result      - {"agent": name, "tool": name, "content": str}
        agent_message    - {"agent": name, "content": str}
        handoff          - {"from": name, "to": name}
        pipeline_done    - {"total_events": int}
    """
    event_num = [0]  # list so it's mutable in closure

    def emit(event_type, data):
        event_num[0] += 1
        event_callback(event_type, data)
        time.sleep(0.4)  # Pause for real-time feel

    # ── Phase 1: Research Agent ────────────────────────────────
    emit("agent_activated", {"agent": "ResearchAgent", "phase": "starting"})
    time.sleep(0.3)

    emit("agent_activated", {"agent": "ResearchAgent", "phase": "busy"})

    # Tool call: search_knowledge_base("agents")
    emit("tool_call", {
        "agent": "ResearchAgent",
        "tool": "search_knowledge_base",
        "arguments": {"query": "agents"},
    })
    time.sleep(0.5)
    emit("tool_result", {
        "agent": "ResearchAgent",
        "tool": "search_knowledge_base",
        "content": (
            "AI agents are autonomous systems that perceive their environment, "
            "reason about it, and take actions to achieve goals. Key properties: "
            "autonomy, reactivity, pro-activeness, and social ability."
        ),
    })

    # Tool call: calculate_summary_stats
    emit("tool_call", {
        "agent": "ResearchAgent",
        "tool": "calculate_summary_stats",
        "arguments": {"text": "AI agents are autonomous..."},
    })
    time.sleep(0.3)
    emit("tool_result", {
        "agent": "ResearchAgent",
        "tool": "calculate_summary_stats",
        "content": '{"word_count": 42, "estimated_sentences": 3, "avg_word_length": 5.2}',
    })

    # Tool call: search_knowledge_base("swarm")
    emit("tool_call", {
        "agent": "ResearchAgent",
        "tool": "search_knowledge_base",
        "arguments": {"query": "swarm"},
    })
    time.sleep(0.5)
    emit("tool_result", {
        "agent": "ResearchAgent",
        "tool": "search_knowledge_base",
        "content": (
            "OpenAI Swarm is an experimental educational framework for exploring "
            "multi-agent orchestration. Its core abstractions are Agents (with "
            "instructions and tool functions) and handoffs (functions returning "
            "an Agent to transfer control)."
        ),
    })

    # Tool call: store_research
    emit("tool_call", {
        "agent": "ResearchAgent",
        "tool": "store_research",
        "arguments": {
            "notes": (
                "AI agents: autonomous systems with perception, reasoning, action. "
                "Multi-agent systems coordinate agents. "
                "OpenAI Swarm: experimental framework using Agents and handoffs."
            )
        },
    })
    time.sleep(0.3)
    emit("tool_result", {
        "agent": "ResearchAgent",
        "tool": "store_research",
        "content": "Research notes stored (175 chars). Total: 175 chars.",
    })

    # Agent message
    emit("agent_message", {
        "agent": "ResearchAgent",
        "content": (
            "I've gathered comprehensive information about AI agents and "
            "multi-agent systems. Key findings include the core properties of "
            "agents (autonomy, reactivity, pro-activeness) and how OpenAI Swarm "
            "enables multi-agent orchestration through handoffs."
        ),
    })

    # Handoff: Research → Writer
    emit("handoff", {"from": "ResearchAgent", "to": "WriterAgent"})
    emit("agent_activated", {"agent": "ResearchAgent", "phase": "done"})

    # ── Phase 2: Writer Agent ────────────────────────────────
    time.sleep(0.5)
    emit("agent_activated", {"agent": "WriterAgent", "phase": "starting"})
    time.sleep(0.3)
    emit("agent_activated", {"agent": "WriterAgent", "phase": "busy"})

    # Agent message with article
    emit("agent_message", {
        "agent": "WriterAgent",
        "content": (
            "## AI Agents and Multi-Agent Systems: The Next Frontier\n\n"
            "Artificial intelligence has evolved from simple rule-based systems "
            "to sophisticated AI agents that can perceive, reason, and act "
            "autonomously. These agents possess four key properties: autonomy, "
            "reactivity, pro-activeness, and social ability.\n\n"
            "**Multi-agent systems** coordinate multiple specialized agents to "
            "tackle complex problems. OpenAI Swarm is an experimental framework "
            "that makes this accessible through Agents and handoffs."
        ),
    })

    # Handoff: Writer → Review
    emit("handoff", {"from": "WriterAgent", "to": "ReviewAgent"})
    emit("agent_activated", {"agent": "WriterAgent", "phase": "done"})

    # ── Phase 3: Review Agent ────────────────────────────────
    time.sleep(0.5)
    emit("agent_activated", {"agent": "ReviewAgent", "phase": "starting"})
    time.sleep(0.3)
    emit("agent_activated", {"agent": "ReviewAgent", "phase": "busy"})

    # Agent message with review
    emit("agent_message", {
        "agent": "ReviewAgent",
        "content": (
            "**Review Results:**\n\n"
            "✓ Clear structure with engaging opening, body, and conclusion.\n"
            "✓ The four key properties of AI agents are well-articulated.\n"
            "✓ Multi-agent systems explanation is accurate and accessible.\n"
            "✓ Swarm is correctly positioned as an experimental/educational framework.\n\n"
            "**Suggestions:** Consider adding a concrete example of multi-agent "
            "systems in action (e.g., autonomous drone swarms).\n\n"
            "Overall: **Approved.** Great work!"
        ),
    })

    # Tool call: store_research (sign-off)
    emit("tool_call", {
        "agent": "ReviewAgent",
        "tool": "store_research",
        "arguments": {
            "notes": "Article reviewed and approved. Final sign-off by ReviewAgent."
        },
    })
    time.sleep(0.3)
    emit("tool_result", {
        "agent": "ReviewAgent",
        "tool": "store_research",
        "content": "Research notes stored (64 chars). Total: 239 chars.",
    })

    # Done
    emit("agent_activated", {"agent": "ReviewAgent", "phase": "done"})
    time.sleep(0.5)
    emit("pipeline_done", {"total_events": event_num[0]})


# ════════════════════════════════════════════════════════════════
# CLAWTEAM PIPELINE RUNNER (streams events step by step)
# ════════════════════════════════════════════════════════════════

def run_clawteam_pipeline(event_callback):
    """
    Execute the ClawTeam-style CLI agent orchestration pipeline,
    calling event_callback for each event.

    Event types:
        leader_status  - {"type": "leader_status", "phase": str, "goalText": str}
        agent_status   - {"type": "agent_status", "agentId": str, "phase": str, "task": str, "progress": int}
        inbox_message  - {"type": "inbox_message", "from": str, "text": str}
        log_line       - {"type": "log_line", "text": str, "cls": str}
        pipeline_done  - {"totalEvents": int}
    """
    total = [0]

    def emit(step):
        total[0] += 1
        event_type = step["type"]
        event_callback(event_type, step)
        time.sleep(0.35)

    # ── Phase 1: Leader analyzes goal ──────────────────────────
    emit({"type": "leader_status", "phase": "analyzing",
          "goalText": '🔍 Analyzing task: "Build authentication module with API endpoints"'})
    emit({"type": "log_line", "text": "🧠 Leader: Analyzing goal and breaking into sub-tasks...", "cls": "highlight"})
    emit({"type": "log_line", "text": "   ├─ Detected 4 sub-tasks: Implementation, Review, Testing, Architecture", "cls": "info"})
    emit({"type": "log_line", "text": "   └─ Resolving dependencies: Design → Implement → Review → Test", "cls": "info"})

    # ── Phase 2: Leader spawns sub-agents ─────────────────────
    emit({"type": "leader_status", "phase": "spawning",
          "goalText": "🧬 Spawning specialized sub-agents..."})

    spawns = [
        ("coder", "Coder", "tmux:0", "feature/auth-module"),
        ("reviewer", "Reviewer", "tmux:1", "feature/auth-module"),
        ("tester", "Tester", "tmux:2", "feature/unit-tests"),
        ("architect", "Architect", "tmux:3", "feature/api-design"),
    ]
    for aid, aname, pane, wtree in spawns:
        emit({"type": "agent_status", "agentId": aid, "phase": "spawning", "task": "", "progress": 0})
        emit({"type": "log_line", "text": f"├─ Spawning {aname} in {pane} | worktree: {wtree}", "cls": "cmd"})
        emit({"type": "log_line", "text": f"│  └─ git worktree add {wtree} origin/main", "cls": "cmd"})
        emit({"type": "inbox_message", "from": "System", "text": f"Spawning {aname} agent in {pane}"})

    emit({"type": "log_line", "text": "└─ All 4 sub-agents spawned successfully", "cls": "ok"})

    # ── Phase 3: Assign tasks ─────────────────────────────────
    emit({"type": "leader_status", "phase": "orchestrating",
          "goalText": "📋 Assigning tasks to agents..."})

    assignments = [
        ("architect", "Architect", "Design API endpoints & data model", 2),
        ("coder", "Coder", "Implement auth endpoints (JWT + OAuth)", 1),
        ("reviewer", "Reviewer", "Review auth module for security issues", 4),
        ("tester", "Tester", "Write unit & integration tests", 3),
    ]
    for aid, aname, task, prog in assignments:
        emit({"type": "agent_status", "agentId": aid, "phase": "working", "task": task, "progress": prog})
        emit({"type": "log_line", "text": f"📋 Assigning to {aname}: \"{task}\"", "cls": "cmd"})
        emit({"type": "inbox_message", "from": "Leader Agent",
              "text": f"{aname}: Your task is → {task}"})

    # ── Phase 4: Agents work and communicate ──────────────────
    emit({"type": "leader_status", "phase": "orchestrating",
          "goalText": "🔄 Agents working in parallel..."})

    # Architect
    emit({"type": "log_line", "text": "🏗️  Architect: Creating API spec with OpenAPI 3.0...", "cls": "info"})
    emit({"type": "inbox_message", "from": "Architect",
          "text": "@Leader API design complete — endpoints defined."})

    # Coder
    emit({"type": "agent_status", "agentId": "coder", "phase": "working",
          "task": "Implementing auth endpoints...", "progress": 2})
    emit({"type": "log_line", "text": "⚙️  Coder: Implementing JWT auth middleware...", "cls": "info"})
    emit({"type": "log_line", "text": "⚙️  Coder: Adding OAuth2 provider integration...", "cls": "info"})
    emit({"type": "inbox_message", "from": "Coder",
          "text": "@Reviewer PR ready: `feature/auth-module` — please review."})

    # Reviewer
    emit({"type": "agent_status", "agentId": "reviewer", "phase": "working",
          "task": "Reviewing auth module...", "progress": 3})
    emit({"type": "log_line", "text": "📋 Reviewer: Checking for security vulnerabilities...", "cls": "warn"})
    emit({"type": "inbox_message", "from": "Reviewer",
          "text": "@Coder Found 2 minor issues — fixed in commit 4a3f2b1."})
    emit({"type": "agent_status", "agentId": "reviewer", "phase": "working",
          "task": "Review complete, 2 issues fixed", "progress": 4})
    emit({"type": "log_line", "text": "📋 Reviewer: LGTM! Security audit passed.", "cls": "ok"})
    emit({"type": "inbox_message", "from": "Reviewer",
          "text": "@Leader Code review complete — module approved."})

    # Tester
    emit({"type": "agent_status", "agentId": "tester", "phase": "working",
          "task": "Writing unit tests...", "progress": 2})
    emit({"type": "log_line", "text": "🔬 Tester: Writing pytest test suite (24 test cases)...", "cls": "info"})
    emit({"type": "agent_status", "agentId": "tester", "phase": "working",
          "task": "Running test suite...", "progress": 4})
    emit({"type": "log_line", "text": "🔬 Tester: 24/24 tests passed ✅ Coverage: 94%", "cls": "ok"})
    emit({"type": "inbox_message", "from": "Tester",
          "text": "@Leader All tests pass. Coverage at 94%."})

    # Architect validates
    emit({"type": "agent_status", "agentId": "architect", "phase": "working",
          "task": "Validating implementation", "progress": 5})
    emit({"type": "log_line", "text": "🏗️  Architect: Implementation matches design spec. Approved.", "cls": "ok"})
    emit({"type": "inbox_message", "from": "Architect",
          "text": "@Leader System validation complete."})

    # ── Phase 5: Leader merges ────────────────────────────────
    emit({"type": "leader_status", "phase": "merging",
          "goalText": "🔄 Merging all agent work..."})
    emit({"type": "log_line", "text": "🧠 Leader: Collecting results from all agents...", "cls": "highlight"})
    emit({"type": "log_line", "text": "   ├─ architect: Design approved ✅", "cls": "ok"})
    emit({"type": "log_line", "text": "   ├─ coder: Implementation complete ✅", "cls": "ok"})
    emit({"type": "log_line", "text": "   ├─ reviewer: Code review passed ✅", "cls": "ok"})
    emit({"type": "log_line", "text": "   └─ tester: 24/24 tests passing ✅", "cls": "ok"})
    emit({"type": "log_line", "text": "Running: git merge feature/auth-module feature/unit-tests feature/api-design", "cls": "cmd"})

    # ── Phase 6: Done ─────────────────────────────────────────
    emit({"type": "leader_status", "phase": "done",
          "goalText": "✅ Authentication module built and merged!"})
    for aid, _, _, _ in spawns:
        emit({"type": "agent_status", "agentId": aid, "phase": "done", "task": "Complete", "progress": 5})

    emit({"type": "log_line", "text": "", "cls": ""})
    emit({"type": "log_line", "text": "══════════════════════════════════════════════════════", "cls": "highlight"})
    emit({"type": "log_line", "text": "  ✅  SWARM COMPLETE — All tasks merged to main", "cls": "ok"})
    emit({"type": "log_line", "text": "  🧠  Leader: 4 agents coordinated, 6 inbox messages", "cls": "ok"})
    emit({"type": "log_line", "text": "  📦  Worktrees merged: auth-module, unit-tests, api-design", "cls": "ok"})
    emit({"type": "log_line", "text": "══════════════════════════════════════════════════════", "cls": "highlight"})
    emit({"type": "inbox_message", "from": "Leader Agent",
          "text": "@all Swarm complete. Great work team! 🎉"})

    event_callback("pipeline_done", {"totalEvents": total[0]})


# ════════════════════════════════════════════════════════════════
# HTTP SERVER
# ════════════════════════════════════════════════════════════════

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE, "swarm_ui.html")
CLAWTEAM_HTML_PATH = os.path.join(BASE, "clawteam_ui.html")
CALCULATOR_HTML_PATH = os.path.join(BASE, "calculator.html")


class Handler(BaseHTTPRequestHandler):
    """HTTP handler that serves the UI and SSE events."""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/events":
            self._handle_sse(run_pipeline)
        elif parsed.path == "/events/clawteam":
            self._handle_sse(run_clawteam_pipeline)
        elif parsed.path == "/realtime/clawteam":
            self._handle_realtime_sse()
        elif parsed.path == "/realtime/clawteam/state":
            self._handle_team_state()
        elif parsed.path == "/realtime/clawteam/status":
            self._handle_bridge_status()
        elif parsed.path == "/":
            self._serve_html(HTML_PATH)
        elif parsed.path == "/clawteam":
            self._serve_html(CLAWTEAM_HTML_PATH)
        elif parsed.path == "/calculator":
            self._serve_html(CALCULATOR_HTML_PATH)
        elif parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _handle_realtime_sse(self):
        """
        SSE endpoint that uses the ClawTeam bridge.
        When the connection is opened, it runs a demo (real ClawTeam API,
        CLI, or mock fallback) and streams events to the client.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        self._disconnected = False

        def sse_send_with_check(event_type, data):
            if self._disconnected:
                return
            try:
                self._sse_send(event_type, data)
            except (BrokenPipeError, ConnectionResetError):
                self._disconnected = True

        # First tell the client how we connected
        self._sse_send("connected", {
            "status": "ok",
            "mode": BRIDGE_MODE,
            "note": (
                "ClawTeam real API" if BRIDGE_MODE == "real" else
                "ClawTeam CLI" if BRIDGE_MODE == "cli" else
                "Simulated (install clawteam for real mode)"
            ),
        })

        try:
            BRIDGE.launch_demo(
                callback=lambda event_type, data: sse_send_with_check(event_type, data),
                sse_send=sse_send_with_check,
            )
        except BrokenPipeError:
            self._disconnected = True
        except Exception as e:
            if not self._disconnected:
                try:
                    self._sse_send("error", {"message": str(e)})
                except (BrokenPipeError, ConnectionResetError):
                    pass

    def _handle_team_state(self):
        """Return a JSON snapshot of current team state."""
        from urllib.parse import parse_qs

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        team_name = params.get("team", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if BRIDGE_MODE == "mock":
            result = {
                "mode": "mock",
                "teams": [],
                "note": "ClawTeam not installed.",
            }
        elif team_name:
            state = BRIDGE.collect_state(team_name)
            result = state if state else {"error": f"Team '{team_name}' not found"}
        else:
            result = {
                "mode": BRIDGE_MODE,
                "teams": BRIDGE.list_teams(),
            }

        self.wfile.write(json.dumps(result, default=str).encode("utf-8"))

    def _handle_bridge_status(self):
        """Return bridge status as JSON."""
        status = BRIDGE.get_status()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(status, default=str).encode("utf-8"))

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

    def _handle_sse(self, pipeline_fn):
        """Stream pipeline events via Server-Sent Events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Flag so run_pipeline can stop early if client disconnects
        self._disconnected = False

        def sse_send_with_check(event_type, data):
            if self._disconnected:
                return
            try:
                self._sse_send(event_type, data)
            except (BrokenPipeError, ConnectionResetError):
                self._disconnected = True

        # Send initial connected event
        try:
            self._sse_send("connected", {"status": "ok"})
        except (BrokenPipeError, ConnectionResetError):
            self._disconnected = True
            return

        # Run the pipeline, streaming each event
        try:
            pipeline_fn(sse_send_with_check)
        except BrokenPipeError:
            self._disconnected = True
        except Exception as e:
            if not self._disconnected:
                try:
                    self._sse_send("error", {"message": str(e)})
                except (BrokenPipeError, ConnectionResetError):
                    pass

    def _sse_send(self, event_type, data):
        """Send a single SSE event."""
        try:
            payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            raise  # Let caller handle

    def log_message(self, format, *args):
        """Quieter logging — only log connections, not every SSE event."""
        if "/events" not in str(args):
            super().log_message(format, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Allow concurrent connections (UI page + SSE stream)."""
    allow_reuse_address = True
    daemon_threads = True


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main():
    port = 8000
    server = ThreadedHTTPServer(("", port), Handler)
    print()
    print("  ╔════════════════════════════════════════════════════╗")
    print("  ║   🤖  Agent Swarm Visualizer                       ║")
    print("  ╠════════════════════════════════════════════════════╣")
    print(f"  ║   Swarm:    http://localhost:{port}                   ║")
    print(f"  ║   ClawTeam: http://localhost:{port}/clawteam          ║")
    print(f"  ║   Calculator: http://localhost:{port}/calculator      ║")
    print(f"  ║   Bridge:   {BRIDGE_MODE.upper():19}               ║")
    print("  ║   Ctrl+C to stop                                   ║")
    print("  ╚════════════════════════════════════════════════════╝")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
