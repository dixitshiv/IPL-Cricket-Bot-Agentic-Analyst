"""Offline tests for the agent code path — no network, no live model, no API key.

A fake OpenAI client replays a scripted list of responses, driving
``server.agent_events`` (and the ``/api/ask`` SSE handler) through its tool-loop.
This locks the plumbing that the live model sits on top of:

* a run_sql tool call really executes against the read-only views,
* the streamed event shapes ({type:"sql"|"answer"|"error"|"done"}) stay stable,
* a bad query surfaces as an error event instead of crashing the loop,
* the missing-OPENROUTER_API_KEY guard holds,
* a session remembers one user+assistant turn for follow-ups.

None of this calls OpenRouter, so it runs anywhere the DuckDB build exists.
"""
import json

from fastapi.testclient import TestClient

import server


# ── a fake OpenAI client that replays scripted chat-completion responses ──
class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = _Fn(name, arguments)


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=False):
        d = {"role": "assistant", "content": self.content, "tool_calls": self.tool_calls}
        return {k: v for k, v in d.items() if v is not None} if exclude_none else d


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, message):
        self.choices = [_Choice(message)]


class _Completions:
    def __init__(self, script):
        self._script, self._i = script, 0

    def create(self, **_kwargs):
        assert self._i < len(self._script), "agent requested more model turns than scripted"
        resp = self._script[self._i]
        self._i += 1
        return resp


class _FakeClient:
    def __init__(self, script):
        self.chat = type("Chat", (), {"completions": _Completions(script)})()


def fake_client_factory(script):
    """Return a zero-arg callable (matching ask.client) that yields a fake client."""
    return lambda: _FakeClient(script)


def tool_call(call_id, query):
    return _Resp(_Msg(tool_calls=[_ToolCall(call_id, "run_sql", json.dumps({"query": query}))]))


def answer(text):
    return _Resp(_Msg(content=text))


# ── tests ──
def test_agent_loop_runs_sql_then_answers(monkeypatch):
    script = [
        tool_call("c1", "SELECT COUNT(*) AS n FROM v_deliveries WHERE season = '2026'"),
        answer("There are plenty of balls in 2026."),
    ]
    monkeypatch.setattr(server, "client", fake_client_factory(script))
    messages = [{"role": "system", "content": "x"}, {"role": "user", "content": "count balls"}]

    events = list(server.agent_events(messages))

    assert events[0]["type"] == "sql"
    assert events[0]["columns"] == ["n"]
    assert events[0]["rows"][0]["n"] > 0
    assert "error" not in events[0]
    assert events[-1]["type"] == "answer"
    assert "plenty" in events[-1]["text"]


def test_agent_surfaces_sql_errors(monkeypatch):
    script = [
        tool_call("c1", "SELECT * FROM table_that_does_not_exist"),
        answer("I hit an error and recovered."),
    ]
    monkeypatch.setattr(server, "client", fake_client_factory(script))
    messages = [{"role": "system", "content": "x"}, {"role": "user", "content": "boom"}]

    events = list(server.agent_events(messages))

    assert events[0]["type"] == "sql"
    assert events[0].get("error")           # non-empty error string
    assert events[-1]["type"] == "answer"   # loop kept going after the error


def test_ask_endpoint_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with TestClient(server.app) as c:
        body = c.get("/api/ask", params={"q": "hi"}).text
    assert "OPENROUTER_API_KEY" in body
    assert '"type": "error"' in body


def test_ask_endpoint_streams_and_remembers(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    script = [
        tool_call("c1", "SELECT COUNT(*) AS n FROM v_deliveries WHERE season = '2026'"),
        answer("Done."),
    ]
    monkeypatch.setattr(server, "client", fake_client_factory(script))
    server.SESSIONS.pop("sess-test", None)

    with TestClient(server.app) as c:
        body = c.get("/api/ask", params={"q": "count balls", "sid": "sess-test"}).text

    types = [json.loads(line[6:])["type"] for line in body.splitlines() if line.startswith("data: ")]
    assert "sql" in types and "answer" in types and "done" in types
    # the session remembered exactly one user+assistant turn for follow-ups
    assert len(server.SESSIONS.get("sess-test", [])) == 2
