import pytest

import llm
import nodes
from graph import build_graph


def base_state(**overrides):
    state = {
        "topic": "test topic",
        "format": "blog",
        "research": "some notes",
        "draft": "some draft",
        "final": "",
        "feedback": "",
        "approved": False,
        "revision_count": 0,
        "errors": [],
    }
    state.update(overrides)
    return state


# ---------- Researcher ----------

def test_researcher_survives_search_failure(monkeypatch):
    class BrokenDDGS:
        def text(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(nodes, "DDGS", BrokenDDGS)
    monkeypatch.setattr(nodes, "call_llm", lambda **kwargs: "fake notes")

    out = nodes.researcher(base_state())

    assert out["research"] == "fake notes"
    assert any("Search failed" in e for e in out["errors"])


# ---------- Writer ----------

def test_writer_increments_revision_count(monkeypatch):
    monkeypatch.setattr(nodes, "call_llm", lambda **kwargs: "new draft")

    out = nodes.writer(base_state(revision_count=1))

    assert out["draft"] == "new draft"
    assert out["revision_count"] == 2


def test_writer_uses_editor_feedback(monkeypatch):
    captured = {}

    def fake_llm(**kwargs):
        captured.update(kwargs)
        return "rewritten"

    monkeypatch.setattr(nodes, "call_llm", fake_llm)

    nodes.writer(base_state(feedback="Fix the intro"))

    assert "Fix the intro" in captured["user"]


# ---------- Editor ----------

def test_editor_approves(monkeypatch):
    reply = "VERDICT: APPROVE\nFEEDBACK: none\n---\n# Title\nBody text"
    monkeypatch.setattr(nodes, "call_llm", lambda **kwargs: reply)

    out = nodes.editor(base_state())

    assert out["approved"] is True
    assert out["final"].startswith("# Title")


def test_editor_requests_revision(monkeypatch):
    reply = "VERDICT: REVISE\nFEEDBACK: Shorten it\n---\n# Title"
    monkeypatch.setattr(nodes, "call_llm", lambda **kwargs: reply)

    out = nodes.editor(base_state())

    assert out["approved"] is False
    assert out["feedback"] == "Shorten it"


def test_editor_handles_bad_format(monkeypatch):
    monkeypatch.setattr(nodes, "call_llm", lambda **kwargs: "just some text")

    out = nodes.editor(base_state())

    assert out["approved"] is True
    assert any("not in expected format" in e for e in out["errors"])


# ---------- Router (the traffic light) ----------

@pytest.mark.parametrize(
    "approved, count, expected",
    [
        (True, 1, "end"),       # editor happy: stop
        (False, 1, "revise"),   # not happy, drafts left: loop
        (False, nodes.MAX_DRAFTS, "end"),  # not happy, but limit hit: stop
    ],
)
def test_router(approved, count, expected):
    state = base_state(approved=approved, revision_count=count)
    assert nodes.route_after_editor(state) == expected


# ---------- Whole graph ----------

def test_graph_never_loops_forever(monkeypatch):
    class FakeDDGS:
        def text(self, *args, **kwargs):
            return []

    def fake_llm(**kwargs):
        if "strict editor" in kwargs["system"]:
            return "VERDICT: REVISE\nFEEDBACK: more\n---\n# Title"
        return "some text"

    monkeypatch.setattr(nodes, "DDGS", FakeDDGS)
    monkeypatch.setattr(nodes, "call_llm", fake_llm)

    state = base_state(research="", draft="")
    result = build_graph().invoke(state, {"recursion_limit": 15})

    assert result["revision_count"] == nodes.MAX_DRAFTS
    assert result["approved"] is False


# ---------- LLM retries ----------

def test_llm_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    calls = {"n": 0}

    class FakeResponse:
        content = "ok"

    class FakeLLM:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("temporary problem")
            return FakeResponse()

    monkeypatch.setattr(llm, "ChatGroq", FakeLLM)

    assert llm.call_llm("sys", "user") == "ok"
    assert calls["n"] == 3


def test_llm_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)

    class AlwaysFails:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            raise RuntimeError("down")

    monkeypatch.setattr(llm, "ChatGroq", AlwaysFails)

    with pytest.raises(RuntimeError, match="failed after"):
        llm.call_llm("sys", "user")