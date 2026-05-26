"""Tests for action_recorder.py"""
from __future__ import annotations

import tempfile

from ducktap.discovery.action_recorder import ActionRecorder


def test_record_click() -> None:
    r = ActionRecorder()
    r.click("#submit")
    assert len(r) == 1
    assert r.actions[0].action == "click"
    assert r.actions[0].selector == "#submit"


def test_record_fill() -> None:
    r = ActionRecorder()
    r.fill("input[name=email]", "test@example.com")
    assert len(r) == 1
    assert r.actions[0].action == "fill"
    assert r.actions[0].selector == "input[name=email]"
    assert r.actions[0].value == "test@example.com"


def test_record_wait_and_scroll() -> None:
    r = ActionRecorder()
    r.wait(500)
    r.scroll(800)
    assert len(r) == 2
    assert r.actions[0].action == "wait"
    assert r.actions[0].ms == 500
    assert r.actions[1].action == "scroll"
    assert r.actions[1].dy == 800


def test_save_and_load_roundtrip() -> None:
    r = ActionRecorder()
    r.click("#btn")
    r.fill("#name", "Ada")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    r.save(path)
    r2 = ActionRecorder()
    loaded = r2.load(path)
    assert len(loaded) == 2
    assert loaded[0]["action"] == "click"
    assert loaded[1]["action"] == "fill"
    assert len(r2) == 2


def test_to_replay_list() -> None:
    r = ActionRecorder()
    r.navigate("https://example.com/login")
    replay = r.to_replay_list()
    assert replay == [{"action": "navigate", "url": "https://example.com/login"}]
