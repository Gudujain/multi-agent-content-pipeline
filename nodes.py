from ddgs import DDGS
from llm import call_llm

MAX_DRAFTS = 3  # first draft + 2 revisions


def researcher(state):
    """Worker 1: search the web, then summarize into notes."""
    errors = list(state["errors"])
    lines = []

    try:
        results = DDGS().text(state["topic"], max_results=5)
        for r in results:
            lines.append(f"- {r.get('title', '')}: {r.get('body', '')} ({r.get('href', '')})")
    except Exception as e:
        # Error handling: search failed, so we record it and keep going.
        errors.append(f"Search failed: {e}")

    raw = "\n".join(lines)
    if not raw:
        raw = "No web results found. Use general knowledge and say clearly that sources are missing."

    notes = call_llm(
        system="You are a careful research assistant. Produce 6-8 short bullet points of key facts. Keep source URLs when given. Do not invent facts.",
        user=f"Topic: {state['topic']}\n\nSearch results:\n{raw}",
    )
    return {"research": notes, "errors": errors}


def writer(state):
    """Worker 2: write (or rewrite) the draft."""
    kind = "a blog post of about 500 words" if state["format"] == "blog" else "a Twitter/X thread of 6-8 numbered tweets, each under 280 characters"

    user = f"Write {kind} about: {state['topic']}\n\nUse ONLY these research notes:\n{state['research']}"
    if state["feedback"]:
        user += f"\n\nYour previous draft:\n{state['draft']}\n\nEditor feedback to fix:\n{state['feedback']}"

    draft = call_llm(
        system="You are a clear, friendly writer. Use simple language and a strong hook.",
        user=user,
        temperature=0.7,
    )
    return {"draft": draft, "revision_count": state["revision_count"] + 1}


def editor(state):
    """Worker 3: judge, polish, and format as markdown."""
    reply = call_llm(
        system=(
            "You are a strict editor. Reply in EXACTLY this layout:\n"
            "Line 1: VERDICT: APPROVE or VERDICT: REVISE\n"
            "Line 2: FEEDBACK: one sentence on what to improve (or 'none')\n"
            "Line 3: ---\n"
            "Then the full polished version in clean markdown "
            "(title as # heading, short paragraphs, fix grammar)."
        ),
        user=f"Format: {state['format']}\n\nDraft:\n{state['draft']}",
    )

    approved = False
    feedback = ""
    final = reply

    try:
        header, body = reply.split("\n---\n", 1)
        approved = "VERDICT: APPROVE" in header.upper()
        for line in header.splitlines():
            if line.upper().startswith("FEEDBACK:"):
                feedback = line.split(":", 1)[1].strip()
        final = body.strip()
    except ValueError:
        # Editor ignored our layout. Accept the text instead of crashing.
        approved = True
        errors = list(state["errors"]) + ["Editor output not in expected format; auto-approved."]
        return {"final": reply.strip(), "approved": True, "feedback": "", "errors": errors}

    return {"final": final, "approved": approved, "feedback": feedback}


def route_after_editor(state):
    """The traffic light: stop, or go back to the Writer?"""
    if state["approved"]:
        return "end"
    if state["revision_count"] >= MAX_DRAFTS:
        return "end"  # looping constraint: never loop forever
    return "revise"