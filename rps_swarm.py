"""
rps_swarm.py — Rock Paper Scissors Swarm Agents
================================================
Multi-agent system for an RPS game using the Orchestrator
pattern from mock_swarm.py.

Uses:
  - Agent from mock_swarm for each specialist
  - Orchestrator for lifecycle management
  - EventBus for event emissions
  - RetryHandler for resilient tool execution
  - ContextSchema for typed game state
  - AgentRegistry for agent discovery & tracking

Agents:
  - GameMaster:     Orchestrates rounds, validates moves, manages state
  - BotStrategist:  Analyzes player patterns, makes intelligent bot moves
  - ScoreAnalyst:   Tracks statistics, provides round-by-round insights
  - Narrator:       Provides thematic flavor text for the game

Usage:
    # Direct Python usage
    python3 rps_swarm.py

    # Via server
    from rps_swarm import create_engine
"""

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from mock_swarm import (
    Agent,
    AgentRegistry,
    ContextField,
    ContextSchema,
    Event,
    EventBus,
    EventHook,
    Orchestrator,
    ParallelTask,
    RetryHandler,
    ToolResult,
    ToolResultStatus,
)


# ════════════════════════════════════════════════════════════════
# RPS Game Types
# ════════════════════════════════════════════════════════════════

CHOICES = ["rock", "paper", "scissors"]
CHOICE_EMOJI = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
CHOICE_NAME = {"rock": "Rock", "paper": "Paper", "scissors": "Scissors"}
CHOICE_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


# ── Typed Game State Schema ────────────────────────────────────

class GamePhase(str):
    WELCOME = "welcome"
    PLAYING = "playing"
    ROUND_RESULT = "round_result"
    GAME_OVER = "game_over"


RPS_CONTEXT_SCHEMA = ContextSchema([
    ContextField("best_of", int, default=5, description="Number of rounds in the match"),
    ContextField("max_rounds", int, default=5, description="Maximum rounds to play"),
    ContextField("current_round", int, default=0, description="Current round number"),
    ContextField("player_score", int, default=0, description="Player's score"),
    ContextField("bot_score", int, default=0, description="Bot's score"),
    ContextField("wins", int, default=0, description="Player wins count"),
    ContextField("losses", int, default=0, description="Player losses count"),
    ContextField("draws", int, default=0, description="Draw count"),
    ContextField("phase", str, default=GamePhase.WELCOME, description="Current game phase"),
    ContextField("player_history", list, factory=list, description="Player's move history"),
    ContextField("bot_history", list, factory=list, description="Bot's move history"),
    ContextField("rounds", list, factory=list, description="All rounds played"),
    ContextField("last_strategy", str, default="", description="Last bot strategy used"),
    ContextField("last_commentary", str, default="", description="Last narrators comment"),
])


# ════════════════════════════════════════════════════════════════
# TOOL FUNCTIONS (registered with Agent instances)
# ════════════════════════════════════════════════════════════════

STRATEGY_NAMES = {
    "random": "🎲 Random Guess",
    "counter": "🔄 Counter Move",
    "pattern": "📊 Pattern Recognition",
    "adaptive": "🧠 Adaptive Strategy",
}


def _counter(choice: str) -> str:
    """Return the choice that beats the given choice."""
    for beats, loses in CHOICE_BEATS.items():
        if loses == choice:
            return beats
    return random.choice(CHOICES)


# ── BotStrategist Tools ────────────────────────────────────────

def choose_bot_move(context_variables: dict) -> str:
    """
    Analyze player history and choose the bot's next move.
    Uses strategy: random → counter → pattern detection → adaptive.

    Returns JSON with choice and strategy info.
    """
    history = context_variables.get("player_history", [])

    if not history:
        choice = random.choice(CHOICES)
        strategy = "random"
    elif len(history) == 1:
        choice = _counter(history[0])
        strategy = "counter"
    else:
        last = history[-1]
        second_last = history[-2]

        if last == second_last:
            # Player repeats — counter it
            choice = _counter(last)
            strategy = "pattern"
        elif len(history) >= 3:
            p3 = history[-3]
            if p3 == last and second_last != last:
                # A-B-A pattern — counter B
                choice = _counter(second_last)
                strategy = "pattern"
            elif history[-3:] == ["rock", "paper", "scissors"]:
                choice = "rock"
                strategy = "pattern"
            else:
                choice = _counter(last)
                strategy = "adaptive"
        else:
            choice = _counter(last)
            strategy = "adaptive"

    return json.dumps({
        "choice": choice,
        "strategy": strategy,
        "strategy_name": STRATEGY_NAMES.get(strategy, strategy),
    })


def get_bot_analysis(context_variables: dict) -> str:
    """Generate analysis of player patterns."""
    history = context_variables.get("player_history", [])

    if not history:
        return json.dumps({"analysis": "No data yet — watching your moves."})

    total = len(history)
    counts = {c: history.count(c) for c in CHOICES}
    fav = max(counts, key=counts.get)
    fav_pct = round((counts[fav] / total) * 100)

    player_score = context_variables.get("player_score", 0)
    bot_score = context_variables.get("bot_score", 0)

    if player_score > bot_score:
        momentum = "You're ahead! I need to adapt."
    elif bot_score > player_score:
        momentum = "I'm reading your patterns."
    else:
        momentum = f"It's tied {player_score}-{bot_score}."

    return json.dumps({
        "analysis": f"After {total} round{'s' if total != 1 else ''}: "
                    f"You favor {CHOICE_EMOJI[fav]} {fav.title()} ({fav_pct}%). {momentum}",
    })


# ── ScoreAnalyst Tools ─────────────────────────────────────────

def get_round_stats(context_variables: dict) -> str:
    """Calculate current game statistics and predictions."""
    total = len(context_variables.get("rounds", []))
    wins = context_variables.get("wins", 0)
    losses = context_variables.get("losses", 0)
    draws = context_variables.get("draws", 0)
    player_score = context_variables.get("player_score", 0)
    bot_score = context_variables.get("bot_score", 0)
    best_of = context_variables.get("best_of", 5)

    if total == 0:
        return json.dumps({
            "total_rounds": 0,
            "player_win_rate": 0,
            "bot_win_rate": 0,
            "draw_rate": 0,
            "prediction": "Game just started!",
        })

    player_win_rate = round((wins / total) * 100, 1)
    bot_win_rate = round((losses / total) * 100, 1)
    draw_rate = round((draws / total) * 100, 1)

    # Calculate streak
    rounds = context_variables.get("rounds", [])
    streak = 0
    for r in reversed(rounds):
        w = r["winner"] if isinstance(r, dict) else r.winner
        if w == "player":
            if streak >= 0:
                streak += 1
            else:
                break
        elif w == "bot":
            if streak <= 0:
                streak -= 1
            else:
                break
        else:
            break

    # Prediction
    if player_score > bot_score:
        prediction = f"Leading {player_score}-{bot_score}"
    elif bot_score > player_score:
        prediction = f"Trailing {player_score}-{bot_score}"
    else:
        prediction = f"Tied at {player_score}"

    thresh = (best_of // 2) + 1
    is_game_over = player_score >= thresh or bot_score >= thresh

    if is_game_over:
        if player_score > bot_score:
            prediction += " — Player wins the match! 🎉"
        elif bot_score > player_score:
            prediction += " — Bot wins the match! 🤖"
        else:
            prediction += " — It's a tie! 🤝"

    return json.dumps({
        "total_rounds": total,
        "player_win_rate": player_win_rate,
        "bot_win_rate": bot_win_rate,
        "draw_rate": draw_rate,
        "streak": streak,
        "prediction": prediction,
    })


def get_match_summary(context_variables: dict) -> str:
    """Generate a full match summary."""
    stats = json.loads(get_round_stats(context_variables))
    player_score = context_variables.get("player_score", 0)
    bot_score = context_variables.get("bot_score", 0)
    best_of = context_variables.get("best_of", 5)

    return json.dumps({
        "summary": (
            f"Match Summary (Best of {best_of})\n"
            f"  Score: You {player_score} — {bot_score} Bot\n"
            f"  Rounds played: {stats['total_rounds']}\n"
            f"  Win rate: {stats['player_win_rate']}%\n"
            f"  Bot win rate: {stats['bot_win_rate']}%\n"
            f"  Draw rate: {stats['draw_rate']}%\n"
            f"  Best streak: {abs(stats['streak'])} round(s)\n"
        ),
    })


# ── Narrator Tools ─────────────────────────────────────────────

ROUND_OPENERS = [
    "The crowd holds their breath...",
    "A new challenger approaches!",
    "The arena awaits your move...",
    "Fortune favors the bold!",
    "The tension builds...",
    "Choose wisely, champion!",
    "The digital realm watches...",
    "Your move sets destiny in motion!",
]

PLAYER_WIN_COMMENTS = [
    "A brilliant move! The crowd erupts!",
    "Outplayed! The bot didn't see that coming!",
    "Flawless victory! You're a natural!",
    "The bot reels from that decisive blow!",
    "Masterful strategy! One for the highlight reel!",
    "You read the bot like an open book!",
    "Textbook play! Absolutely textbook!",
]

BOT_WIN_COMMENTS = [
    "The bot counters brilliantly!",
    "A sly move from the machine mind!",
    "Calculated. Precise. Deadly.",
    "The algorithm strikes back!",
    "A cold, logical choice from the bot.",
    "The silicon strikes again!",
    "You've been out-computed!",
]

DRAW_COMMENTS = [
    "Great minds think alike!",
    "A perfect mirror! Both chose the same!",
    "Neither blinks first! A stalemate!",
    "Symmetry in the arena!",
    "The universe seeks balance...",
    "Two minds, one thought!",
]

GAME_OVER_WIN = [
    "CHAMPION! You've conquered the arena! 🏆",
    "Victory is yours! The bot concedes!",
    "You've beaten the algorithm! Humanity prevails!",
    "Legendary performance! You are the RPS master!",
]

GAME_OVER_LOSE = [
    "The bot claims victory today. But tomorrow is another day!",
    "Defeated by logic! Try again, champion!",
    "The machine wins this round. Can you win the war?",
    "A setback, not a defeat. Every loss is a lesson!",
]

GAME_OVER_DRAW = [
    "A tie! The universe is in perfect balance. One more game?",
    "Neither side yields! A fair match to the end!",
    "Evenly matched! You and the bot are equals!",
]

STRATEGY_REVEALS = {
    "random": "🎲 The bot goes with a wild guess!",
    "counter": "🔄 The bot studied your last move...",
    "pattern": "📊 Pattern recognized! Machine learning in action!",
    "adaptive": "🧠 The bot adapts its strategy...",
}


def narrate_round_opener(context_variables: dict) -> str:
    """Generate opening narration for a round."""
    return json.dumps({"text": random.choice(ROUND_OPENERS)})


def narrate_result(context_variables: dict) -> str:
    """Generate result commentary based on the last round."""
    rounds_data = context_variables.get("rounds", [])
    if not rounds_data:
        return json.dumps({"text": "The arena is silent..."})

    last_round = rounds_data[-1]
    winner = last_round["winner"] if isinstance(last_round, dict) else last_round.winner

    pools = {
        "player": PLAYER_WIN_COMMENTS,
        "bot": BOT_WIN_COMMENTS,
        "draw": DRAW_COMMENTS,
    }
    comment = random.choice(pools.get(winner, DRAW_COMMENTS))
    return json.dumps({"text": comment})


def narrate_game_over(context_variables: dict) -> str:
    """Generate game over narration."""
    player_score = context_variables.get("player_score", 0)
    bot_score = context_variables.get("bot_score", 0)

    if player_score > bot_score:
        comment = random.choice(GAME_OVER_WIN)
    elif bot_score > player_score:
        comment = random.choice(GAME_OVER_LOSE)
    else:
        comment = random.choice(GAME_OVER_DRAW)

    return json.dumps({"text": comment})


def narrate_strategy(context_variables: dict) -> str:
    """Reveal the bot's strategy."""
    strategy = context_variables.get("last_strategy", "adaptive")
    reveal = STRATEGY_REVEALS.get(strategy, f"The bot uses {strategy} strategy.")
    return json.dumps({"text": reveal})


# ── GameMaster Tools ───────────────────────────────────────────

def validate_move(context_variables: dict, choice: str) -> str:
    """Validate a player's move."""
    if choice not in CHOICES:
        return json.dumps({"valid": False, "error": f"Invalid choice: {choice}"})
    return json.dumps({"valid": True})


def resolve_round(context_variables: dict, player_choice: str, bot_choice: str) -> str:
    """Resolve a round and return the winner."""
    if player_choice == bot_choice:
        winner = "draw"
    elif CHOICE_BEATS[player_choice] == bot_choice:
        winner = "player"
    else:
        winner = "bot"

    return json.dumps({
        "winner": winner,
        "player_choice": player_choice,
        "bot_choice": bot_choice,
        "player_emoji": CHOICE_EMOJI[player_choice],
        "bot_emoji": CHOICE_EMOJI[bot_choice],
    })


# ════════════════════════════════════════════════════════════════
# SWARM AGENT DEFINITIONS
# ════════════════════════════════════════════════════════════════

BOT_STRATEGIST_AGENT = Agent(
    name="BotStrategist",
    instructions=(
        "You are a strategic RPS bot that analyzes player patterns. "
        "Use choose_bot_move to make your move, and get_bot_analysis "
        "to provide pattern insights."
    ),
    functions=[choose_bot_move, get_bot_analysis],
    max_retries=2,
)

SCORE_ANALYST_AGENT = Agent(
    name="ScoreAnalyst",
    instructions=(
        "You are a statistics analyst for RPS games. Use get_round_stats "
        "to calculate current stats and get_match_summary for full analysis."
    ),
    functions=[get_round_stats, get_match_summary],
    max_retries=2,
)

NARRATOR_AGENT = Agent(
    name="Narrator",
    instructions=(
        "You are the game narrator providing engaging commentary. "
        "Use narrate_round_opener, narrate_result, narrate_game_over, "
        "and narrate_strategy to provide flavor text."
    ),
    functions=[
        narrate_round_opener,
        narrate_result,
        narrate_game_over,
        narrate_strategy,
    ],
    max_retries=1,
)

GAME_MASTER_AGENT = Agent(
    name="GameMaster",
    instructions=(
        "You are the GameMaster who validates moves and resolves rounds. "
        "Use validate_move to check moves and resolve_round to determine winners."
    ),
    functions=[validate_move, resolve_round],
    max_retries=2,
)


# ════════════════════════════════════════════════════════════════
# RPS SWARM ENGINE (uses Orchestrator infrastructure)
# ════════════════════════════════════════════════════════════════

def create_engine(
    best_of: int = 5,
    retry_handler: Optional[RetryHandler] = None,
    parallel_executor=None,
    event_bus: Optional[EventBus] = None,
) -> "RpsSwarmEngine":
    """
    Create an RpsSwarmEngine configured with mock_swarm.py infrastructure.

    Args:
        best_of: Number of rounds in a match.
        retry_handler: Custom RetryHandler (default: 2 retries, 0.3s base delay).
        event_bus: Custom EventBus for monitoring.

    Returns a configured RpsSwarmEngine.
    """
    orchestrator = Orchestrator(
        retry_handler=retry_handler or RetryHandler(
            max_retries=2,
            base_delay=0.3,
            max_delay=4.0,
        ),
        context_schema=RPS_CONTEXT_SCHEMA,
        event_bus=event_bus or EventBus(),
    )

    registry = AgentRegistry(BOT_STRATEGIST_AGENT)
    # Manually register all agents since they don't handoff to each other
    for agent in [SCORE_ANALYST_AGENT, NARRATOR_AGENT, GAME_MASTER_AGENT]:
        if agent.name not in registry._agents:
            registry._agents[agent.name] = agent
            registry._lifecycle[agent.name] = "idle"

    return RpsSwarmEngine(
        best_of=best_of,
        orchestrator=orchestrator,
        registry=registry,
    )


class RpsSwarmEngine:
    """
    Orchestrates the RPS game using the swarm agent pattern from mock_swarm.py.

    Each round runs through:
      1. BotStrategist — analyzes patterns and chooses move
      2. GameMaster — validates and resolves the round
      3. ScoreAnalyst — computes statistics
      4. Narrator — adds flavor commentary

    Uses Orchestrator's EventBus for observability and RetryHandler
    for resilient tool execution.
    """

    def __init__(
        self,
        best_of: int = 5,
        orchestrator: Optional[Orchestrator] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        self.state = RPS_CONTEXT_SCHEMA.merge_defaults({
            "best_of": best_of,
            "max_rounds": best_of,
            "phase": GamePhase.WELCOME,
        })

        self.orchestrator = orchestrator or Orchestrator(
            retry_handler=RetryHandler(max_retries=2, base_delay=0.3),
            context_schema=RPS_CONTEXT_SCHEMA,
        )

        self.registry = registry or self._build_registry()
        self.event_bus = self.orchestrator.event_bus

    def _build_registry(self) -> AgentRegistry:
        """Build agent registry with all RPS agents."""
        registry = AgentRegistry(BOT_STRATEGIST_AGENT)
        for agent in [SCORE_ANALYST_AGENT, NARRATOR_AGENT, GAME_MASTER_AGENT]:
            if agent.name not in registry._agents:
                registry._agents[agent.name] = agent
                registry._lifecycle[agent.name] = "idle"
        return registry

    def on_event(self, callback: Callable[[str, dict], None]):
        """Subscribe to all game events via EventBus."""
        def wrapper(event: Event):
            try:
                callback(event.hook.value, event.data)
            except Exception:
                pass
        self.event_bus.subscribe_all(wrapper)

    def _emit(self, hook: EventHook, data: dict):
        """Emit an event via EventBus using a valid EventHook enum."""
        self.event_bus.emit(hook, data=data)

    def start_game(self, best_of: int = None) -> dict:
        """Start a new game, resetting state."""
        if best_of:
            self.state["best_of"] = best_of
            self.state["max_rounds"] = best_of

        # Reset state with defaults
        self.state = RPS_CONTEXT_SCHEMA.merge_defaults({
            "best_of": self.state.get("best_of", 5),
            "max_rounds": self.state.get("max_rounds", 5),
            "phase": GamePhase.PLAYING,
        })

        self._emit(EventHook.AGENT_ACTIVATED, {"agent": "GameMaster", "phase": "working"})
        self._emit(EventHook.AGENT_DONE, {"agent": "GameMaster", "phase": "done"})
        self._emit(EventHook.PIPELINE_START, {"type": "game_start", "state": dict(self.state)})
        self._emit(EventHook.TOOL_RESULT, {"agent": "Narrator", "type": "round_opener", "text": random.choice(ROUND_OPENERS)})

        return dict(self.state)

    def player_move(self, choice: str) -> dict:
        """
        Process a player's move through the swarm pipeline:
        1. BotStrategist analyzes and chooses bot move
        2. GameMaster resolves the round
        3. ScoreAnalyst computes stats
        4. Narrator adds flavor text

        Uses EventBus for step tracking and RetryHandler
        for resilient function execution.
        """
        if self.state.get("phase") not in ("playing", "round_result") or self._is_game_over():
            return dict(self.state)

        if choice not in CHOICES:
            return {"error": f"Invalid choice: {choice}"}

        # ── Step 1: BotStrategist chooses move ────────────────
        self._emit(EventHook.AGENT_ACTIVATED, {"agent": "BotStrategist", "phase": "working"})
        self.registry.set_phase("BotStrategist", "active")

        result = self.orchestrator.retry_handler.execute(
            choose_bot_move,
            context_variables=self.state,
            is_idempotent=True,
        )
        if result.status == ToolResultStatus.SUCCESS:
            bot_data = json.loads(result.content)
            bot_choice = bot_data["choice"]
            strategy = bot_data["strategy"]
            strategy_name = bot_data["strategy_name"]
        else:
            bot_choice = random.choice(CHOICES)
            strategy = "random"
            strategy_name = "🎲 Random (fallback)"

        self.state["last_strategy"] = strategy
        self.registry.set_phase("BotStrategist", "done")
        self._emit(EventHook.AGENT_DONE, {"agent": "BotStrategist"})

        # ── Step 2: GameMaster resolves round ────────────────
        self._emit(EventHook.AGENT_ACTIVATED, {"agent": "GameMaster", "phase": "working"})
        self.registry.set_phase("GameMaster", "active")

        self.state["current_round"] += 1

        # Determine winner
        if choice == bot_choice:
            winner = "draw"
        elif CHOICE_BEATS[choice] == bot_choice:
            winner = "player"
        else:
            winner = "bot"

        # Update scores
        if winner == "player":
            self.state["player_score"] += 1
            self.state["wins"] += 1
        elif winner == "bot":
            self.state["bot_score"] += 1
            self.state["losses"] += 1
        else:
            self.state["draws"] += 1

        # Record the round
        round_record = {
            "round_num": self.state["current_round"],
            "player_choice": choice,
            "bot_choice": bot_choice,
            "winner": winner,
        }
        self.state["rounds"].append(round_record)
        self.state["player_history"].append(choice)
        self.state["bot_history"].append(bot_choice)

        game_over = self._is_game_over()
        if game_over:
            self.state["phase"] = GamePhase.GAME_OVER
        else:
            self.state["phase"] = GamePhase.ROUND_RESULT

        self.registry.set_phase("GameMaster", "done")
        self._emit(EventHook.AGENT_DONE, {"agent": "GameMaster"})

        # ── Step 3: ScoreAnalyst computes stats ──────────────
        self._emit(EventHook.AGENT_ACTIVATED, {"agent": "ScoreAnalyst", "phase": "working"})
        self.registry.set_phase("ScoreAnalyst", "active")

        stats_result = self.orchestrator.retry_handler.execute(
            get_round_stats,
            context_variables=self.state,
            is_idempotent=True,
        )
        stats = json.loads(stats_result.content) if stats_result.status == ToolResultStatus.SUCCESS else {}

        self.registry.set_phase("ScoreAnalyst", "done")
        self._emit(EventHook.AGENT_DONE, {"agent": "ScoreAnalyst"})

        # ── Step 4: Narrator adds flavor ─────────────────────
        self._emit(EventHook.AGENT_ACTIVATED, {"agent": "Narrator", "phase": "working"})

        result_comment_data = json.loads(
            self.orchestrator.retry_handler.execute(
                narrate_result, context_variables=self.state, is_idempotent=True,
            ).content or '{"text": ""}'
        )
        self._emit(EventHook.TOOL_RESULT, {"agent": "Narrator", "type": "result_comment", "text": result_comment_data.get("text", "")})

        strategy_reveal_data = json.loads(
            self.orchestrator.retry_handler.execute(
                narrate_strategy, context_variables=self.state, is_idempotent=True,
            ).content or '{"text": ""}'
        )
        self._emit(EventHook.TOOL_RESULT, {"agent": "Narrator", "type": "strategy_reveal", "text": strategy_reveal_data.get("text", "")})

        if game_over:
            go_data = json.loads(
                self.orchestrator.retry_handler.execute(
                    narrate_game_over, context_variables=self.state, is_idempotent=True,
                ).content or '{"text": ""}'
            )
            self._emit(EventHook.TOOL_RESULT, {"agent": "Narrator", "type": "game_over", "text": go_data.get("text", "")})

        self.registry.set_phase("Narrator", "done")
        self.event_bus.emit(EventHook.AGENT_DONE, {"agent": "Narrator"})

        # ── Build result ──────────────────────────────────────
        result_obj = {
            "round": self.state["current_round"],
            "player_choice": choice,
            "bot_choice": bot_choice,
            "player_emoji": CHOICE_EMOJI[choice],
            "bot_emoji": CHOICE_EMOJI[bot_choice],
            "winner": winner,
            "strategy": strategy,
            "strategy_name": strategy_name,
            "game_over": game_over,
            "state": dict(self.state),
            "stats": stats,
            "comment": result_comment_data.get("text", ""),
            "strategy_reveal": strategy_reveal_data.get("text", ""),
        }

        self._emit(EventHook.TOOL_RESULT, {"agent": "RpsSwarmEngine", "type": "round_result", "result": result_obj})

        if game_over:
            summary_result = self.orchestrator.retry_handler.execute(
                get_match_summary, context_variables=self.state, is_idempotent=True,
            )
            if summary_result.status == ToolResultStatus.SUCCESS:
                summary_data = json.loads(summary_result.content)
                self._emit(EventHook.PIPELINE_DONE, {
                    "type": "match_summary",
                    "summary": summary_data.get("summary", ""),
                    "stats": stats,
                })

        return result_obj

    def _is_game_over(self) -> bool:
        """Check if the game has reached a terminal state."""
        thresh = (self.state["best_of"] // 2) + 1
        return (
            self.state["player_score"] >= thresh
            or self.state["bot_score"] >= thresh
            or self.state["current_round"] >= self.state["max_rounds"]
        )

    def get_state(self) -> dict:
        """Get current game state."""
        return dict(self.state)

    def get_stats(self) -> dict:
        """Get current round statistics."""
        stats_result = self.orchestrator.retry_handler.execute(
            get_round_stats,
            context_variables=self.state,
            is_idempotent=True,
        )
        if stats_result.status == ToolResultStatus.SUCCESS:
            return json.loads(stats_result.content)
        return {}

    def get_summary(self) -> str:
        """Get match summary text."""
        summary_result = self.orchestrator.retry_handler.execute(
            get_match_summary,
            context_variables=self.state,
            is_idempotent=True,
        )
        if summary_result.status == ToolResultStatus.SUCCESS:
            data = json.loads(summary_result.content)
            return data.get("summary", "")
        return ""


# ════════════════════════════════════════════════════════════════
# DEMO
# ════════════════════════════════════════════════════════════════

def demo():
    """Run a demo game using the swarm engine with Orchestrator infrastructure."""
    print("\n  ╔════════════════════════════════════════════╗")
    print("  ║   🎮 RPS Swarm Engine — Demo              ║")
    print("  ╠════════════════════════════════════════════╣")
    print("  ║   Uses mock_swarm.py:                      ║")
    print("  ║     • Orchestrator  • EventBus             ║")
    print("  ║     • RetryHandler  • AgentRegistry        ║")
    print("  ║     • ContextSchema • Agent                ║")
    print("  ╚════════════════════════════════════════════╝\n")

    engine = create_engine(best_of=3)
    agent_names = [a.name for a in engine.registry.all().values()]
    print(f"  🧠 Registered agents: {', '.join(agent_names)}\n")

    def on_event(event_type, data):
        if event_type == EventHook.AGENT_ACTIVATED.value:
            phase_icon = {"working": "⚙️", "done": "✅"}
            icon = phase_icon.get(data.get("phase", ""), "🔄")
            print(f"  {icon} {data.get('agent', '?')} → {data.get('phase', '?')}")
        elif event_type == EventHook.AGENT_DONE.value:
            phase_icon = {"working": "⚙️", "done": "✅"}
            print(f"  ✅ {data.get('agent', '?')} done")
        elif event_type == EventHook.TOOL_RESULT.value:
            subtype = data.get("type", "")
            if subtype == "result_comment":
                print(f"  💬 {data.get('text', '')}")
            elif subtype == "strategy_reveal":
                print(f"  🤖 {data.get('text', '')}")
            elif subtype == "game_over":
                print(f"  🏁 {data.get('text', '')}")
            elif subtype == "round_opener":
                print(f"  📖 {data.get('text', '')}")
            elif subtype == "round_result":
                r = data["result"]
                result_text = {"player": "You win! 🎉", "bot": "Bot wins! 🤖", "draw": "Draw! 🤝"}
                print(f"\n  🤝 Round {r['round']}:")
                print(f"     You: {r['player_emoji']}  Bot: {r['bot_emoji']}")
                print(f"     {result_text.get(r['winner'], '?')}")
                print(f"     Bot used: {r['strategy_name']}")
                print(f"     Score: You {r['state']['player_score']} — {r['state']['bot_score']} Bot")
        elif event_type == EventHook.PIPELINE_START.value and data.get("type") == "game_start":
            print(f"  🎮 Best of {data.get('state', {}).get('best_of', '?')} — Let the games begin!\n")
        elif event_type == EventHook.PIPELINE_DONE.value and data.get("type") == "match_summary":
            print(f"\n  {data.get('summary', '')}")

    engine.on_event(on_event)

    # Play some rounds with pattern-seeking moves
    moves = ["rock", "paper", "scissors", "rock", "paper"]
    engine.start_game()

    for move in moves:
        result = engine.player_move(move)
        if isinstance(result, dict) and result.get("game_over"):
            print(f"\n  🏁 Game Over!")
            break
        time.sleep(0.4)

    print()


if __name__ == "__main__":
    demo()
