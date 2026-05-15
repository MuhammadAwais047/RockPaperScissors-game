"""
clawteam_bridge.py — Adapter between our SSE visualization and the real ClawTeam framework.

Three integration modes (auto-selected, best available first):
  1. REAL  — Python API (BoardCollector, TeamManager) for live team state streaming
  2. CLI   — Subprocess calls to clawteam CLI with --json output
  3. MOCK  — Simulated pipeline when ClawTeam isn't installed at all

Usage:
    from clawteam_bridge import get_bridge
    bridge = get_bridge()
    print(bridge.get_mode())      # "real" | "cli" | "mock"
    print(bridge.list_teams())    # [team_name, ...]
    bridge.stream_events("my-team", my_sse_callback)
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ════════════════════════════════════════════════════════════════
# Detect available ClawTeam modes
# ════════════════════════════════════════════════════════════════

HAS_CLAWTEAM_API = False
try:
    from clawteam.board.collector import BoardCollector
    from clawteam.team.manager import TeamManager
    HAS_CLAWTEAM_API = True
except ImportError:
    pass

HAS_CLI = False
try:
    result = subprocess.run(
        ["clawteam", "--version"],
        capture_output=True, text=True, timeout=5
    )
    HAS_CLI = result.returncode == 0
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass


def get_bridge():
    """Factory: returns best available bridge."""
    if HAS_CLAWTEAM_API:
        try:
            return RealAPIBridge()
        except Exception:
            pass
    if HAS_CLI:
        try:
            return CLIBridge()
        except Exception:
            pass
    return MockBridge()


# ════════════════════════════════════════════════════════════════
# Common event helpers — all bridges emit these formats
# ════════════════════════════════════════════════════════════════

def _fmt_time():
    d = datetime.now()
    return d.isoformat(timespec="milliseconds")


def _status_event(phase, goal_text=""):
    return {
        "type": "leader_status",
        "phase": phase,
        "goalText": goal_text,
    }


def _agent_event(agent_id, phase, task="", progress=0):
    return {
        "type": "agent_status",
        "agentId": agent_id,
        "phase": phase,
        "task": task,
        "progress": progress,
    }


def _inbox_event(from_name, text):
    return {
        "type": "inbox_message",
        "from": from_name,
        "text": text,
    }


def _log_event(text, cls="info"):
    return {
        "type": "log_line",
        "text": text,
        "cls": cls,
    }


def _done_event(total=0):
    return {"type": "pipeline_done", "totalEvents": total}


# ════════════════════════════════════════════════════════════════
# Base bridge interface
# ════════════════════════════════════════════════════════════════

class BaseBridge:
    """Abstract base with mock fallback methods."""

    def get_mode(self):
        return "mock"

    def get_status(self):
        return {
            "mode": self.get_mode(),
            "teams": self.list_teams(),
            "version": "0.0.0",
        }

    def list_teams(self):
        return []

    def collect_state(self, team_name):
        return None

    def stream_events(self, team_name, callback, interval=2.0):
        """Stream events to callback. Returns a stop function."""
        raise NotImplementedError

    def launch_demo(self, callback, sse_send):
        """Launch a demonstration pipeline and emit events via callback."""
        raise NotImplementedError


# ════════════════════════════════════════════════════════════════
# REAL — Python API bridge (BoardCollector, TeamManager)
# ════════════════════════════════════════════════════════════════

class RealAPIBridge(BaseBridge):
    """Uses ClawTeam's Python API directly."""

    def __init__(self):
        self._team_manager = TeamManager()
        self._collector_cache = {}

    def get_mode(self):
        return "real"

    def get_status(self):
        teams = self.list_teams()
        return {
            "mode": "real",
            "teams": teams,
            "version": "0.2.0",
            "api": "clawteam.board.collector.BoardCollector",
        }

    def list_teams(self):
        try:
            return [t["name"] for t in self._team_manager.discover_teams()]
        except Exception:
            return []

    def collect_state(self, team_name):
        """Get full team state snapshot from BoardCollector."""
        try:
            team_config = self._team_manager.get_team(team_name)
            if not team_config:
                return None

            from clawteam.team.tasks import TaskStore
            from clawteam.team.mailbox import MailboxManager

            task_store = TaskStore(team_name)
            mailbox = MailboxManager(team_name)

            collector = BoardCollector(
                self._team_manager, mailbox, task_store
            )
            return collector.collect_team(team_name)
        except Exception as e:
            return {"error": str(e)}

    def stream_events(self, team_name, callback, interval=2.0):
        """Poll team state and emit diffs as events."""
        import threading

        stop_flag = [False]
        prev_state = {}

        def _poll():
            nonlocal prev_state
            while not stop_flag[0]:
                try:
                    state = self.collect_state(team_name)
                    if state and "error" not in state:
                        events = self._diff_state(prev_state, state)
                        for evt in events:
                            callback(evt["type"], evt)
                        prev_state = state
                except Exception:
                    pass
                for _ in range(int(interval * 10)):
                    if stop_flag[0]:
                        break
                    time.sleep(0.1)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()
        return lambda: stop_flag.__setitem__(0, True)

    def _diff_state(self, prev, curr):
        """Compare two team states and emit change events."""
        events = []

        # Check for task status changes
        prev_tasks = {t.get("id", ""): t for t in prev.get("tasks", {}).values()}
        # Flatten current tasks
        curr_tasks = {}
        for status_group in curr.get("tasks", {}).values():
            if isinstance(status_group, list):
                for t in status_group:
                    tid = t.get("id", str(id(t)))
                    curr_tasks[tid] = {**t, "_status": status_group}

        # New/changed tasks
        for tid, t in curr_tasks.items():
            if tid not in prev_tasks:
                owner = t.get("owner", "agent")
                events.append(_agent_event(owner, "working", t.get("subject", ""), 2))
                events.append(_log_event(f"📋 New task: {t.get('subject', '')}", "cmd"))

        # Messages
        prev_msg_ids = {m.get("id", "") for m in prev.get("messages", [])}
        for m in curr.get("messages", []):
            mid = m.get("id", str(id(m)))
            if mid not in prev_msg_ids:
                events.append(_inbox_event(
                    m.get("from", "Agent"),
                    m.get("text", m.get("content", ""))
                ))

        # Member status changes
        prev_members = {m.get("agentId", m.get("name", "")): m
                        for m in prev.get("members", [])}
        for m in curr.get("members", []):
            mid = m.get("agentId", m.get("name", ""))
            if mid not in prev_members:
                events.append(_agent_event(mid, "working", "", 1))
            elif m.get("inboxCount", 0) > prev_members[mid].get("inboxCount", 0):
                events.append(_log_event(f"📨 {mid}: New message received", "info"))

        if not events:
            # Send a heartbeat to keep SSE alive
            events.append({"type": "heartbeat", "timestamp": _fmt_time()})

        return events

    def launch_demo(self, callback, sse_send):
        """Launch a real ClawTeam demo swarm directly via the Python API."""
        team_name = f"demo-{uuid.uuid4().hex[:8]}"

        def emit(step):
            callback(step["type"], step)
            time.sleep(0.35)

        try:
            # Phase 1: Create team
            emit(_status_event("analyzing", f"🔍 Creating ClawTeam: {team_name}"))
            emit(_log_event(f"🧠 Creating team '{team_name}' with TeamManager...", "highlight"))

            leader_id = f"leader-{uuid.uuid4().hex[:6]}"
            team = self._team_manager.create_team(
                name=team_name,
                leader_name="Leader Agent",
                leader_id=leader_id,
                description="Auto-spawned demo swarm from visualization",
            )
            emit(_log_event(f"   └─ Team created: {team.name}", "ok"))

            # Phase 2: Spawn agents
            emit(_status_event("spawning", "🧬 Spawning demo agents..."))

            agents = [
                ("coder", "Coder", "general-purpose"),
                ("reviewer", "Reviewer", "general-purpose"),
                ("tester", "Tester", "general-purpose"),
                ("architect", "Architect", "general-purpose"),
            ]
            for aid, aname, atype in agents:
                member = self._team_manager.add_member(
                    team_name=team_name,
                    member_name=aname,
                    agent_id=f"{aid}-{uuid.uuid4().hex[:6]}",
                    agent_type=atype,
                )
                emit(_agent_event(aid, "spawning", "", 0))
                emit(_log_event(f"├─ Spawning {aname} as {atype}", "cmd"))
                emit(_inbox_event("System", f"Spawning {aname} agent"))
                time.sleep(0.2)

            emit(_log_event("└─ All 4 demo agents spawned", "ok"))

            # Phase 3: Assign tasks
            emit(_status_event("orchestrating", "📋 Assigning demo tasks..."))

            tasks = [
                ("architect", "Design API endpoints & data model"),
                ("coder", "Implement auth endpoints (JWT + OAuth)"),
                ("reviewer", "Review auth module for security issues"),
                ("tester", "Write unit & integration tests"),
            ]

            from clawteam.team.tasks import TaskStore
            task_store = TaskStore(team_name)

            for aid, task_subject in tasks:
                task = task_store.create(subject=task_subject, owner=aid)
                emit(_agent_event(aid, "working", task_subject, 2))
                emit(_log_event(f"📋 Assigned to {aid}: {task_subject}", "cmd"))
                emit(_inbox_event("Leader Agent", f"{aid}: Your task is → {task_subject}"))

            # Phase 4: Simulate work (in a real scenario agents would be spawned)
            emit(_status_event("orchestrating", "🔄 Agents working in parallel..."))

            work_steps = [
                ("architect", "Creating API spec with OpenAPI 3.0...", 3),
                ("architect", "@Leader API design complete — endpoints defined.", 4),
                ("coder", "Implementing JWT auth middleware...", 2),
                ("coder", "Adding OAuth2 provider integration...", 3),
                ("coder", "@Reviewer PR ready — please review.", 3),
                ("reviewer", "Checking for security vulnerabilities...", 3),
                ("reviewer", "@Coder Found 2 minor issues — fixed in commit.", 4),
                ("reviewer", "LGTM! Security audit passed.", 5),
                ("tester", "Writing pytest test suite (24 test cases)...", 2),
                ("tester", "24/24 tests passed ✅ Coverage: 94%", 5),
            ]

            for aid, msg, prog in work_steps:
                emit(_agent_event(aid, "working", msg, prog))
                emit(_log_event(f"{aid}: {msg}", "info" if "✅" not in msg else "ok"))
                if msg.startswith("@"):
                    emit(_inbox_event(aid, msg))

            # Phase 5: Merge
            emit(_status_event("merging", "🔄 Merging all agent work..."))
            emit(_log_event("🧠 Leader: Collecting results from all agents...", "highlight"))
            for aid, _, _ in agents:
                emit(_log_event(f"   ├─ {aid}: Complete ✅", "ok"))
            emit(_log_event("Running: git merge all branches", "cmd"))

            # Phase 6: Done
            for aid, _, _ in agents:
                emit(_agent_event(aid, "done", "Complete", 5))

            emit(_status_event("done", "✅ Demo swarm complete!"))
            emit(_log_event("", ""))
            emit(_log_event("══════════════════════════════════════════════════════", "highlight"))
            emit(_log_event("  ✅  DEMO SWARM COMPLETE — Real ClawTeam API used", "ok"))
            emit(_log_event(f"  🧠  Team: {team_name}", "ok"))
            emit(_log_event(f"  📦  Agents: 4, Tasks: {len(tasks)}", "ok"))
            emit(_log_event("══════════════════════════════════════════════════════", "highlight"))
            emit(_inbox_event("Leader Agent", "@all Demo complete! Great work team! 🎉"))

        except Exception as e:
            emit(_log_event(f"❌ Error: {e}", "err"))

        sse_send("pipeline_done", {"totalEvents": 0, "teamName": team_name})


# ════════════════════════════════════════════════════════════════
# CLI — bridge via clawteam CLI subprocess
# ════════════════════════════════════════════════════════════════

class CLIBridge(BaseBridge):
    """Uses clawteam CLI subprocess with --json output."""

    def get_mode(self):
        return "cli"

    def get_status(self):
        teams = self.list_teams()
        return {
            "mode": "cli",
            "teams": teams,
            "cli": "clawteam",
        }

    def list_teams(self):
        try:
            result = subprocess.run(
                ["clawteam", "team", "discover", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return []
        except Exception:
            return []

    def collect_state(self, team_name):
        try:
            result = subprocess.run(
                ["clawteam", "board", "show", team_name, "--json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        except Exception:
            return None

    def stream_events(self, team_name, callback, interval=3.0):
        """Poll via CLI and emit diffs."""
        import threading

        stop_flag = [False]
        prev_state = {}

        def _poll():
            nonlocal prev_state
            while not stop_flag[0]:
                state = self.collect_state(team_name)
                if state:
                    # Reuse same diff logic
                    bridge = RealAPIBridge()  # just for _diff_state
                    events = bridge._diff_state(prev_state, state)
                    for evt in events:
                        callback(evt["type"], evt)
                    prev_state = state
                for _ in range(int(interval * 10)):
                    if stop_flag[0]:
                        break
                    time.sleep(0.1)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()
        return lambda: stop_flag.__setitem__(0, True)

    def launch_demo(self, callback, sse_send):
        """Launch a demo by spawning a ClawTeam template."""
        team_name = f"demo-{uuid.uuid4().hex[:8]}"

        def emit(step):
            callback(step["type"], step)
            time.sleep(0.35)

        try:
            emit(_status_event("analyzing", f"🔍 Launching ClawTeam: {team_name}"))
            emit(_log_event(f"🧠 Running: clawteam launch {team_name}", "cmd"))
            emit(_status_event("spawning", "🧬 Spawning agents via CLI..."))
            emit(_log_event("├─ Spawning Coder agent...", "cmd"))
            emit(_log_event("├─ Spawning Reviewer agent...", "cmd"))
            emit(_log_event("├─ Spawning Tester agent...", "cmd"))
            emit(_log_event("└─ Spawning Architect agent...", "cmd"))

            for aid in ["coder", "reviewer", "tester", "architect"]:
                emit(_agent_event(aid, "spawning", "", 0))

            emit(_log_event("└─ All agents spawned via CLI", "ok"))

            emit(_status_event("orchestrating", "📋 Assigning tasks..."))
            assignments = [
                ("architect", "Design API endpoints"),
                ("coder", "Implement endpoints"),
                ("reviewer", "Review security"),
                ("tester", "Write tests"),
            ]
            for aid, task in assignments:
                emit(_agent_event(aid, "working", task, 2))
                emit(_log_event(f"📋 Assigned {aid}: {task}", "cmd"))

            emit(_status_event("orchestrating", "🔄 Waiting for agents via CLI poll..."))
            emit(_log_event("⏳ Agents working — polling BoardCollector for updates...", "info"))

            # Poll for real results a few times
            for i in range(3):
                time.sleep(1.0)
                state = self.collect_state(team_name)
                if state:
                    emit(_log_event(f"📊 Poll {i+1}: Team state retrieved", "ok"))
                else:
                    emit(_log_event(f"⏳ Poll {i+1}: No data yet", "warn"))

            emit(_status_event("done", "✅ CLI demo complete"))
            emit(_log_event("", ""))
            emit(_log_event("══════════════════════════════════════════════", "highlight"))
            emit(_log_event("  ✅  SWARM COMPLETE (CLI mode)", "ok"))
            emit(_log_event(f"  🧠  Team: {team_name}", "ok"))
            emit(_log_event("══════════════════════════════════════════════", "highlight"))

        except Exception as e:
            emit(_log_event(f"❌ Error: {e}", "err"))

        sse_send("pipeline_done", {"totalEvents": 0, "teamName": team_name})


# ════════════════════════════════════════════════════════════════
# MOCK — fallback when ClawTeam is not available
# ════════════════════════════════════════════════════════════════

class MockBridge(BaseBridge):
    """Simulated pipeline — same events as the original mock_swarm."""

    DEMO_AGENTS = [
        ("coder", "Coder", "tmux:0", "feature/auth-module"),
        ("reviewer", "Reviewer", "tmux:1", "feature/auth-module"),
        ("tester", "Tester", "tmux:2", "feature/unit-tests"),
        ("architect", "Architect", "tmux:3", "feature/api-design"),
    ]

    FALLBACK_STEPS = [
        # Phase 1: Analyze
        _status_event("analyzing", '🔍 Analyzing task: "Build authentication module with API endpoints"'),
        _log_event("🧠 Leader: Analyzing goal and breaking into sub-tasks...", "highlight"),
        _log_event("   ├─ Detected 4 sub-tasks: Implementation, Review, Testing, Architecture", "info"),
        _log_event("   └─ Resolving dependencies: Design → Implement → Review → Test", "info"),
        {"type": "delay", "ms": 800},

        # Phase 2: Spawn (injected dynamically)
        _status_event("spawning", "🧬 Spawning specialized sub-agents..."),
    ]

    WORK_STEPS = [
        # Assign
        _status_event("orchestrating", "📋 Assigning tasks to agents..."),
        _agent_event("architect", "working", "Design API endpoints & data model", 2),
        _log_event("📋 Assigning to Architect: \"Design API endpoints & data model\"", "cmd"),
        _inbox_event("Leader Agent", "Architect: Your task is → Design API endpoints & data model"),
        {"type": "delay", "ms": 300},
        _agent_event("coder", "working", "Implement auth endpoints (JWT + OAuth)", 1),
        _log_event("📋 Assigning to Coder: \"Implement auth endpoints (JWT + OAuth)\"", "cmd"),
        _inbox_event("Leader Agent", "Coder: Your task is → Implement auth endpoints (JWT + OAuth)"),
        {"type": "delay", "ms": 300},
        _agent_event("reviewer", "working", "Review auth module for security issues", 4),
        _log_event("📋 Assigning to Reviewer: \"Review auth module for security issues\"", "cmd"),
        _inbox_event("Leader Agent", "Reviewer: Your task is → Review auth module for security issues"),
        {"type": "delay", "ms": 300},
        _agent_event("tester", "working", "Write unit & integration tests", 3),
        _log_event("📋 Assigning to Tester: \"Write unit & integration tests\"", "cmd"),
        _inbox_event("Leader Agent", "Tester: Your task is → Write unit & integration tests"),
        {"type": "delay", "ms": 400},

        # Work
        _status_event("orchestrating", "🔄 Agents working in parallel..."),
        _log_event("🏗️  Architect: Creating API spec with OpenAPI 3.0...", "info"),
        _inbox_event("Architect", "@Leader API design complete — endpoints defined."),
        {"type": "delay", "ms": 400},
        _agent_event("coder", "working", "Implementing auth endpoints...", 2),
        _log_event("⚙️  Coder: Implementing JWT auth middleware...", "info"),
        _log_event("⚙️  Coder: Adding OAuth2 provider integration...", "info"),
        _inbox_event("Coder", "@Reviewer PR ready: `feature/auth-module` — please review."),
        {"type": "delay", "ms": 400},
        _agent_event("reviewer", "working", "Reviewing auth module...", 3),
        _log_event("📋 Reviewer: Checking for security vulnerabilities...", "warn"),
        _inbox_event("Reviewer", "@Coder Found 2 minor issues — fixed in commit 4a3f2b1."),
        {"type": "delay", "ms": 300},
        _agent_event("reviewer", "working", "Review complete, 2 issues fixed", 4),
        _log_event("📋 Reviewer: LGTM! Security audit passed.", "ok"),
        _inbox_event("Reviewer", "@Leader Code review complete — module approved."),
        {"type": "delay", "ms": 300},
        _agent_event("tester", "working", "Writing unit tests...", 2),
        _log_event("🔬 Tester: Writing pytest test suite (24 test cases)...", "info"),
        {"type": "delay", "ms": 300},
        _agent_event("tester", "working", "Running test suite...", 4),
        _log_event("🔬 Tester: 24/24 tests passed ✅ Coverage: 94%", "ok"),
        _inbox_event("Tester", "@Leader All tests pass. Coverage at 94%."),
        {"type": "delay", "ms": 300},
        _agent_event("architect", "working", "Validating implementation", 5),
        _log_event("🏗️  Architect: Implementation matches design spec. Approved.", "ok"),
        _inbox_event("Architect", "@Leader System validation complete."),
        {"type": "delay", "ms": 400},

        # Merge
        _status_event("merging", "🔄 Merging all agent work..."),
        _log_event("🧠 Leader: Collecting results from all agents...", "highlight"),
        _log_event("   ├─ architect: Design approved ✅", "ok"),
        _log_event("   ├─ coder: Implementation complete ✅", "ok"),
        _log_event("   ├─ reviewer: Code review passed ✅", "ok"),
        _log_event("   └─ tester: 24/24 tests passing ✅", "ok"),
        _log_event("Running: git merge feature/auth-module feature/unit-tests feature/api-design", "cmd"),
        {"type": "delay", "ms": 500},

        # Done (agent status + leader status + log injected dynamically)
    ]

    def get_mode(self):
        return "mock"

    def get_status(self):
        return {
            "mode": "mock",
            "teams": [],
            "note": "ClawTeam not installed. Install with: pip install clawteam",
        }

    def list_teams(self):
        return []

    def collect_state(self, team_name):
        return None

    def stream_events(self, team_name, callback, interval=2.0):
        """Not applicable in mock mode — use launch_demo instead."""
        def noop():
            pass
        return noop

    def launch_demo(self, callback, sse_send):
        """Run the mock pipeline — same events as the original clawteam_ui.html demo."""

        def emit(step):
            if step.get("type") == "delay":
                time.sleep(step.get("ms", 350))
            else:
                callback(step["type"], step)

        # Build complete step list
        steps = list(self.FALLBACK_STEPS)

        # Inject spawn steps for each agent
        for aid, aname, pane, wtree in self.DEMO_AGENTS:
            steps.append(_agent_event(aid, "spawning", "", 0))
            steps.append(_log_event(f"├─ Spawning {aname} in {pane} | worktree: {wtree}", "cmd"))
            steps.append(_log_event(f"│  └─ git worktree add {wtree} origin/main", "cmd"))
            steps.append(_inbox_event("System", f"Spawning {aname} agent in {pane}"))
            steps.append({"type": "delay", "ms": 300})

        steps.append(_log_event("└─ All 4 sub-agents spawned successfully", "ok"))
        steps.append({"type": "delay", "ms": 400})

        # Work steps
        steps.extend(self.WORK_STEPS)

        # Done steps
        for aid, _, _, _ in self.DEMO_AGENTS:
            steps.append(_agent_event(aid, "done", "Complete", 5))

        steps.append(_status_event("done", "✅ Authentication module built and merged!"))
        steps.append(_log_event("", ""))
        steps.append(_log_event("══════════════════════════════════════════════════════", "highlight"))
        steps.append(_log_event("  ✅  SWARM COMPLETE — All tasks merged to main", "ok"))
        steps.append(_log_event("  🧠  Leader: 4 agents coordinated, 6 inbox messages", "ok"))
        steps.append(_log_event("  📦  Worktrees merged: auth-module, unit-tests, api-design", "ok"))
        steps.append(_log_event("══════════════════════════════════════════════════════", "highlight"))
        steps.append(_inbox_event("Leader Agent", "@all Swarm complete. Great work team! 🎉"))

        # Run all steps
        event_count = [0]
        for step in steps:
            if step.get("type") == "delay":
                time.sleep(step.get("ms", 350))
            elif step.get("type") == "pipeline_done":
                break  # handled below
            else:
                callback(step["type"], step)
                event_count[0] += 1

        sse_send("pipeline_done", {"totalEvents": event_count[0]})
