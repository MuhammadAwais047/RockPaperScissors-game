"""
OpenAI Swarm Demo — Proper Agent Handoff
=========================================
Demonstrates Swarm's core feature: automatic agent handoff via
tool functions returning Agent objects.

Agents form a research → write → review pipeline:
  ResearchAgent  ──handoff──▶  WriterAgent  ──handoff──▶  ReviewAgent

Two modes:
  1. LIVE:  OPENAI_API_KEY=sk-... python3 swarm_demo.py        (real API)
  2. MOCK:  python3 swarm_demo.py                               (simulated, no API key)
"""

import json
import os
import sys

# ── Choose backend: real Swarm or MockSwarm ────────────────────
if os.getenv("OPENAI_API_KEY"):
    from swarm import Swarm, Agent
    print("  🔌  Using REAL Swarm (OpenAI API)")
else:
    from mock_swarm import MockSwarm as Swarm, Agent
    print("  🎭  Using MOCK Swarm (simulated — no API key needed)")


# ════════════════════════════════════════════════════════════════
# TOOL FUNCTIONS
# ════════════════════════════════════════════════════════════════

def search_knowledge_base(query: str) -> str:
    """Search a knowledge base for information on a topic."""
    data = {
        "python": (
            "Python is a high-level, interpreted language created by Guido van Rossum "
            "in 1991. Known for readability, extensive standard library, and strong "
            "community. Widely used in web dev, data science, and AI."
        ),
        "swarm": (
            "Swarm is an experimental multi-agent orchestration framework by OpenAI. "
            "It uses Agents (with instructions + functions) as core abstractions and "
            "handoffs (a function returning another Agent) to transfer control."
        ),
        "agents": (
            "AI agents are autonomous systems that perceive their environment, make "
            "decisions, and take actions to achieve goals. Multi-agent systems "
            "coordinate multiple agents to solve complex problems collaboratively."
        ),
    }
    for key, value in data.items():
        if key.lower() in query.lower():
            return value
    return f"No specific info found about '{query}'."


def calculate_summary_stats(text: str) -> str:
    """Calculate basic statistics on a piece of text."""
    words = text.split()
    sentences = text.count(".") + text.count("!") + text.count("?")
    return json.dumps({
        "word_count": len(words),
        "estimated_sentences": max(sentences, 1),
        "avg_word_length": round(
            sum(len(w) for w in words) / max(len(words), 1), 2
        ),
    })


def store_research(notes: str, context_variables: dict) -> str:
    """Save research findings into the shared context.

    This enables passing structured data between agents during a handoff.
    """
    context_variables["research_notes"] = (
        context_variables.get("research_notes", "") + notes + "\n\n"
    )
    return f"Research notes stored ({len(notes)} chars). Total: {len(context_variables['research_notes'])} chars."


# ════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ════════════════════════════════════════════════════════════════

WRITER_AGENT = None  # Forward declaration — assigned below


def handoff_to_writer():
    """Hand off to the Writer Agent to compose the final article."""
    return WRITER_AGENT


RESEARCH_INSTRUCTIONS = """\
You are a Research Agent.
Your job:
1. Search the knowledge base with search_knowledge_base() for the user's topic.
   Try multiple angles (e.g. search "agents", "swarm", "python").
2. Use calculate_summary_stats() on the results.
3. Call store_research() to persist your findings in context_variables.
4. When you've gathered enough, call handoff_to_writer() to hand off.

Be thorough — search for at least two different queries."""

research_agent = Agent(
    name="ResearchAgent",
    instructions=RESEARCH_INSTRUCTIONS,
    functions=[
        search_knowledge_base,
        calculate_summary_stats,
        store_research,
        handoff_to_writer,
    ],
)


# ── Writer Agent ────────────────────────────────────────────────

def handoff_to_reviewer():
    """Hand off to the Review Agent to proofread and polish the article."""
    return review_agent


WRITER_INSTRUCTIONS = """\
You are a Writer Agent.
Your job:
1. Read the research from context_variables['research_notes'] and from
   the conversation history.
2. Compose a well-structured short article (2–3 paragraphs).
3. Use a clear, engaging, professional tone — like a tech blog post.
4. When done, call handoff_to_reviewer() to hand off for proofreading.

If you need more research, call handoff_to_writer() to go back."""

WRITER_AGENT = Agent(
    name="WriterAgent",
    instructions=WRITER_INSTRUCTIONS,
    functions=[handoff_to_reviewer],
)


# ── Review Agent ────────────────────────────────────────────────

def handoff_to_writer_for_revision(feedback: str):
    """Send revision feedback back to the Writer for improvements."""
    return WRITER_AGENT


REVIEW_INSTRUCTIONS = """\
You are a Review Agent.
Your job:
1. Read the article written by the Writer Agent from the conversation.
2. Check for clarity, grammar, and factual accuracy.
3. If it needs changes, call handoff_to_writer_for_revision() with
   specific feedback.
4. If it looks good, give it a final sign-off and call store_research()
   to mark it as reviewed.
Always acknowledge what's working before offering improvements."""

review_agent = Agent(
    name="ReviewAgent",
    instructions=REVIEW_INSTRUCTIONS,
    functions=[handoff_to_writer_for_revision, store_research],
)


# ════════════════════════════════════════════════════════════════
# RUNNER — single client.run() with automatic handoffs
# ════════════════════════════════════════════════════════════════

def demo():
    print("=" * 62)
    print("  🧠  OpenAI Swarm Demo — Automatic Agent Handoffs")
    print("=" * 62)
    print()
    print("  Agents in this pipeline:")
    print("    ResearchAgent  ──handoff──▶  WriterAgent  ──handoff──▶  ReviewAgent")
    print()

    client = Swarm()

    messages = [{
        "role": "user",
        "content": (
            "Research the topic of 'AI agents' and write a short article "
            "about what they are and how multi-agent systems work."
        ),
    }]

    context_variables = {"research_notes": ""}

    # ── Single run with automatic handoffs ───────────────────
    print("─" * 62)
    print("  Starting agent pipeline...")
    print("─" * 62)

    response = client.run(
        agent=research_agent,
        messages=messages,
        context_variables=context_variables,
        max_turns=15,  # Allow the full pipeline to run
        debug=False,
    )

    # ── Display results ─────────────────────────────────────
    print()
    print("═" * 62)
    print("  📝  FULL CONVERSATION RECORD")
    print("═" * 62)

    for msg in response.messages:
        role = msg["role"].upper()
        agent_name = msg.get("name", "")

        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc["function"]["name"]
                args = tc["function"]["arguments"]
                if len(args) > 50:
                    args = args[:50] + "..."
                print(f"\n  [{role}] ⚡ {fn}({args})")

        elif msg.get("role") == "tool":
            result = (msg.get("content") or "")[:100]
            if result:
                print(f"  [{role}] 📦 {result}...")

        elif msg.get("content"):
            content = msg["content"]
            # Print first 150 chars per message
            preview = content[:150]
            if agent_name:
                print(f"\n  [{role}/{agent_name}] 🗣️  {preview}")
            else:
                print(f"\n  [{role}] 🗣️  {preview}")

            if len(content) > 150:
                print(f"  {'─' * 4}  (+{len(content) - 150} more chars)")

    # ── Final state ──────────────────────────────────────────
    final_cv = response.context_variables
    print()
    print("═" * 62)
    print("  ✅  PIPELINE COMPLETE")
    print("═" * 62)

    last_assistant = [m for m in response.messages
                      if m["role"] == "assistant" and m.get("content")][-1]
    print(f"\n  Last agent in conversation: {last_assistant.get('name', '(unnamed)')}")
    print(f"  Total messages exchanged:  {len(response.messages)}")
    print()
    print("  Final context_variables:")
    for key, val in final_cv.items():
        print(f"    {key}: {str(val)[:100]}")

    print()
    print("  ── Writer's final output ──")
    print()
    print(last_assistant["content"])

    print()
    print("=" * 62)
    print("  Demo complete! ✨")
    print("=" * 62)


if __name__ == "__main__":
    demo()
