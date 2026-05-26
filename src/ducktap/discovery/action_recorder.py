"""Smart action recording for browser sniff.

Records user interactions (clicks, fills, scrolls, navigation) during a
browser-sniff session and emits a replayable action script.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecordedAction:
    action: str
    selector: str = ""
    value: str = ""
    ms: int = 0
    dy: int = 0
    url: str = ""
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def to_replay_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"action": self.action}
        if self.selector:
            d["selector"] = self.selector
        if self.value:
            d["value"] = self.value
        if self.ms:
            d["ms"] = self.ms
        if self.dy:
            d["dy"] = self.dy
        if self.url:
            d["url"] = self.url
        return d


class ActionRecorder:
    """Records and replays browser interactions."""

    def __init__(self) -> None:
        self.actions: list[RecordedAction] = []

    # Recording helpers --------------------------------------------------

    def click(self, selector: str) -> None:
        self.actions.append(RecordedAction(action="click", selector=selector))

    def fill(self, selector: str, value: str) -> None:
        self.actions.append(RecordedAction(action="fill", selector=selector, value=value))

    def wait(self, ms: int = 1000) -> None:
        self.actions.append(RecordedAction(action="wait", ms=ms))

    def scroll(self, dy: int = 2000) -> None:
        self.actions.append(RecordedAction(action="scroll", dy=dy))

    def navigate(self, url: str) -> None:
        self.actions.append(RecordedAction(action="navigate", url=url))

    # Persistence ----------------------------------------------------------

    def save(self, path: str) -> None:
        payload = {"version": 1, "actions": [a.to_replay_dict() for a in self.actions]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load(self, path: str) -> list[dict[str, Any]]:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        raw = payload.get("actions", [])
        self.actions = [RecordedAction(**a) for a in raw]
        return raw

    def to_replay_list(self) -> list[dict[str, Any]]:
        return [a.to_replay_dict() for a in self.actions]

    def __len__(self) -> int:
        return len(self.actions)
