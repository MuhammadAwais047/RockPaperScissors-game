"""
mock_swarm.py — Simulated OpenAI Swarm for offline demo
========================================================
Mimics the Swarm API (Agent, Response, Swarm.run()) so the
demo works without an API key.

The simulation runs through a scripted conversation that matches
the exact agent/tool definitions in swarm_demo.py.
"""

import inspect
import json
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


# ════════════════════════════════════════════════════════════════
# DATA STRUCTURES (mirroring swarm/types.py)
# ════════════════════════════════════════════════════════════════

AgentFunction = Callable


@dataclass
class Agent:
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: str = "You are a helpful agent."
    functions: List[AgentFunction] = field(default_factory=list)
    tool_choice: Optional[str] = None
    parallel_tool_calls: bool = True


@dataclass
class Response:
    messages: list = field(default_factory=list)
    agent: Optional[Agent] = None
    context_variables: dict = field(default_factory=dict)


@dataclass
class Result:
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════
# SIMULATED KNOWLEDGE BASE
# ════════════════════════════════════════════════════════════════

KNOWLEDGE_BASE = {
    "python": (
        "Python is a high-level, interpreted language created by Guido van Rossum "
        "in 1991. Known for readability, extensive standard library, dynamic typing, "
        "and strong community support. Widely used in web development, data science, "
        "AI/ML, automation, and scientific computing."
    ),
    "swarm": (
        "OpenAI Swarm is an experimental educational framework for exploring "
        "multi-agent orchestration. Its core abstractions are Agents (which have "
        "instructions and can call functions) and handoffs (where a function returns "
        "another Agent, automatically transferring control). Swarm is stateless and "
        "built on top of the Chat Completions API."
    ),
    "agents": (
        "AI agents are autonomous systems that perceive their environment, reason "
        "about it, and take actions to achieve goals. Key properties: autonomy, "
        "reactivity, pro-activeness, and social ability. Multi-agent systems "
        "involve multiple agents that coordinate, communicate, and collaborate "
        "to solve problems that are beyond the capability of any single agent."
    ),
}


def _search_kb(query: str) -> str:
    """Mock implementation of search_knowledge_base."""
    for key, value in KNOWLEDGE_BASE.items():
        if key.lower() in query.lower():
            return value
    return f"No specific information found about '{query}'."


def _calc_stats(text: str) -> str:
    """Mock implementation of calculate_summary_stats."""
    words = text.split()
    sentences = text.count(".") + text.count("!") + text.count("?")
    return json.dumps({
        "word_count": len(words),
        "estimated_sentences": max(sentences, 1),
        "avg_word_length": round(
            sum(len(w) for w in words) / max(len(words), 1), 2
        ),
    })


# ════════════════════════════════════════════════════════════════
# SCRIPTED CONVERSATION
# ════════════════════════════════════════════════════════════════

def _build_conversation(initial_messages, initial_cv, agents_map):
    """
    Build a simulated conversation matching the swarm_demo.py agent definitions.

    Returns (messages, final_context_variables).
    """
    messages = list(initial_messages)
    cv = dict(initial_cv)

    # Helper to run a tool function and return its result
    def run_tool(fn, args_str):
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {}

        # Discover the function by name from the agent's tool list
        fn_name = fn
        func_obj = None
        for agent in agents_map.values():
            for f in agent.functions:
                if f.__name__ == fn_name:
                    func_obj = f
                    break
            if func_obj:
                break

        if func_obj is None:
            return json.dumps({"error": f"Function '{fn_name}' not found"})

        # Build kwargs: inject context_variables if the function accepts it
        sig = inspect.signature(func_obj)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "context_variables":
                kwargs["context_variables"] = cv
            elif param_name in args:
                kwargs[param_name] = args[param_name]

        result = func_obj(**kwargs)

        # If the function returned an Agent, capture it for handoff
        if isinstance(result, Agent):
            return {"__handoff__": result.name}

        # If the function modified context_variables (mutable dict), capture changes
        return str(result)

    # ── Phase 1: Research Agent ──────────────────────────────
    research_steps = [
        # Step 1: Model decides to search knowledge base
        {
            "role": "assistant",
            "name": "ResearchAgent",
            "content": None,
            "tool_calls": [{
                "id": "call_research_1",
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "arguments": json.dumps({"query": "agents"}),
                },
            }],
        },
        # Tool result
        {
            "role": "tool",
            "tool_call_id": "call_research_1",
            "content": _search_kb("agents"),
        },
        # Step 2: Get stats
        {
            "role": "assistant",
            "name": "ResearchAgent",
            "content": None,
            "tool_calls": [{
                "id": "call_research_2",
                "type": "function",
                "function": {
                    "name": "calculate_summary_stats",
                    "arguments": json.dumps({"text": _search_kb("agents")}),
                },
            }],
        },
        # Tool result
        {
            "role": "tool",
            "tool_call_id": "call_research_2",
            "content": _calc_stats(_search_kb("agents")),
        },
        # Step 3: Search swarm
        {
            "role": "assistant",
            "name": "ResearchAgent",
            "content": None,
            "tool_calls": [{
                "id": "call_research_3",
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "arguments": json.dumps({"query": "swarm"}),
                },
            }],
        },
        # Tool result
        {
            "role": "tool",
            "tool_call_id": "call_research_3",
            "content": _search_kb("swarm"),
        },
        # Step 4: Store research notes
        {
            "role": "assistant",
            "name": "ResearchAgent",
            "content": None,
            "tool_calls": [{
                "id": "call_research_4",
                "type": "function",
                "function": {
                    "name": "store_research",
                    "arguments": json.dumps({
                        "notes": "AI agents are autonomous systems with perception, reasoning, and action capabilities. "
                                 "Multi-agent systems coordinate multiple agents for complex problem-solving. "
                                 "OpenAI Swarm is an experimental framework for multi-agent orchestration using Agents and handoffs."
                    }),
                },
            }],
        },
        # Tool result — store_research writes to cv
    ]

    # Execute tool for step 4
    store_result = None
    for step in research_steps:
        messages.append(step)
        if step["role"] == "assistant" and step.get("tool_calls"):
            pass  # Just record in messages
        elif step["role"] == "tool":
            pass  # Just record in messages

    # Actually run store_research to update cv
    store_result_str = run_tool("store_research", json.dumps({
        "notes": "AI agents are autonomous systems with perception, reasoning, and action capabilities. "
                 "Multi-agent systems coordinate multiple agents for complex problem-solving. "
                 "OpenAI Swarm is an experimental framework for multi-agent orchestration using Agents and handoffs."
    }))
    messages.append({
        "role": "tool",
        "tool_call_id": "call_research_4",
        "content": store_result_str,
    })

    # Step 5: ResearchAgent reflects on findings
    messages.append({
        "role": "assistant",
        "name": "ResearchAgent",
        "content": (
            "I've gathered comprehensive information about AI agents and multi-agent systems. "
            "Key findings:\n"
            "1. **AI Agents**: Autonomous systems with perception, reasoning, and goal-directed action.\n"
            "2. **Multi-Agent Systems**: Multiple agents coordinating to solve complex problems.\n"
            "3. **OpenAI Swarm**: Experimental framework using Agents and handoffs for orchestration.\n\n"
            "Let me hand this off to the Writer Agent for article composition."
        ),
        "tool_calls": [{
            "id": "call_handoff_1",
            "type": "function",
            "function": {
                "name": "handoff_to_writer",
                "arguments": "{}",
            },
        }],
    })

    # Execute handoff — returns Agent
    handoff_result = run_tool("handoff_to_writer", "{}")

    # Try to parse handoff result (may be string or dict with __handoff__)
    try:
        hf = json.loads(handoff_result) if isinstance(handoff_result, str) else handoff_result
        if isinstance(hf, dict) and hf.get("__handoff__") == "WriterAgent":
            pass  # Handoff recognized
    except (json.JSONDecodeError, TypeError):
        pass

    messages.append({
        "role": "tool",
        "tool_call_id": "call_handoff_1",
        "content": "Handing off to Writer Agent",
    })

    # ── Phase 2: Writer Agent ────────────────────────────────
    messages.append({
        "role": "assistant",
        "name": "WriterAgent",
        "content": (
            "I have the research notes about AI agents, multi-agent systems, and OpenAI Swarm. "
            "Let me compose a well-structured article.\n\n"
            "---\n\n"
            "## AI Agents and Multi-Agent Systems: The Next Frontier\n\n"
            "Artificial intelligence has evolved from simple rule-based systems to sophisticated "
            "AI agents that can perceive their environment, reason about complex situations, and "
            "take autonomous actions to achieve specific goals. These agents possess four key "
            "properties: autonomy, reactivity, pro-activeness, and the ability to interact with "
            "other agents and humans.\n\n"
            "**Multi-agent systems** represent the next evolution—instead of a single monolithic "
            "agent, multiple specialized agents work together to tackle problems that would be "
            "impossible for any one agent alone. These systems involve coordination, communication, "
            "and collaboration, enabling applications like distributed problem-solving, "
            "autonomous trading, and complex robotic coordination.\n\n"
            "**OpenAI Swarm** is an experimental framework that makes multi-agent orchestration "
            "accessible. Its core abstractions are Agents (self-contained units with instructions "
            "and tool-calling capabilities) and handoffs (where one agent can seamlessly transfer "
            "control to another). Built on top of the Chat Completions API, Swarm provides a "
            "lightweight foundation for exploring multi-agent patterns without heavy infrastructure.\n\n"
            "The future of AI is not a single super-intelligence, but rather ecosystems of "
            "specialized agents working together—and frameworks like Swarm are paving the way."
        ),
        "tool_calls": [{
            "id": "call_handoff_2",
            "type": "function",
            "function": {
                "name": "handoff_to_reviewer",
                "arguments": "{}",
            },
        }],
    })

    # Execute handoff
    run_tool("handoff_to_reviewer", "{}")
    messages.append({
        "role": "tool",
        "tool_call_id": "call_handoff_2",
        "content": "Handing off to Review Agent",
    })

    # ── Phase 3: Review Agent ────────────────────────────────
    messages.append({
        "role": "assistant",
        "name": "ReviewAgent",
        "content": (
            "Let me review the article for clarity, grammar, and factual accuracy.\n\n"
            "**What's working well:**\n"
            "✓ The article has a clear structure with an engaging opening, body, and conclusion.\n"
            "✓ The four key properties of AI agents are well-articulated.\n"
            "✓ The explanation of multi-agent systems is accurate and accessible.\n"
            "✓ The section on OpenAI Swarm correctly positions it as an experimental/educational framework.\n"
            "✓ The concluding paragraph about 'ecosystems of specialized agents' is compelling.\n\n"
            "**Minor suggestions:**\n"
            "- Consider adding a concrete example of multi-agent systems in action "
            "(e.g., autonomous drone swarms, AI research teams).\n"
            "- The transition between multi-agent systems and Swarm could be smoother.\n\n"
            "Overall this is a solid, publication-ready article. Signing off."
        ),
        "tool_calls": [{
            "id": "call_handoff_3",
            "type": "function",
            "function": {
                "name": "store_research",
                "arguments": json.dumps({
                    "notes": "Article reviewed and approved. Final sign-off by ReviewAgent."
                }),
            },
        }],
    })

    # Execute store_research for review sign-off
    run_tool("store_research", json.dumps({
        "notes": "Article reviewed and approved. Final sign-off by ReviewAgent."
    }))
    messages.append({
        "role": "tool",
        "tool_call_id": "call_handoff_3",
        "content": "Article reviewed and approved. Final sign-off by ReviewAgent.",
    })

    return messages, cv


# ════════════════════════════════════════════════════════════════
# MOCK SWARM
# ════════════════════════════════════════════════════════════════

class MockSwarm:
    """Simulates OpenAI Swarm's client.run() with scripted responses."""

    def run(
        self,
        agent: Agent,
        messages: list,
        context_variables: dict = None,
        model_override: str = None,
        stream: bool = False,
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        """Simulate a full multi-agent conversation."""

        if context_variables is None:
            context_variables = {}

        # Build a map of agent names to Agent objects
        # We walk through the conversation and collect agents
        # Collect all agents: the starting agent and any that functions reference
        agents_map = {agent.name: agent}

        def _discover_agents(a):
            for fn in a.functions:
                try:
                    result = fn()
                    if isinstance(result, Agent) and result.name not in agents_map:
                        agents_map[result.name] = result
                        _discover_agents(result)  # recurse
                except Exception:
                    pass

        _discover_agents(agent)

        # Build the simulated conversation
        sim_messages, final_cv = _build_conversation(
            messages, context_variables, agents_map
        )

        # Find the last agent in the conversation
        final_agent = None
        for msg in reversed(sim_messages):
            name = msg.get("name", "")
            if name and name in agents_map:
                final_agent = agents_map[name]
                break

        # Add a brief delay to make it feel realistic
        for i in range(3):
            print(f"  Simulating agent reasoning{'.' * (i + 1)}", end="\r")
            time.sleep(0.3)
        print("  " + " " * 30, end="\r")

        return Response(
            messages=sim_messages,
            agent=final_agent or agent,
            context_variables=final_cv,
        )
