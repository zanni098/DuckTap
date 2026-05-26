"""DuckTap Library: local registry of community-printed CLIs.

Stores a JSON file at ``~/.ducktap/library.json`` so users can keep track of
CLIs they (or others) have generated and published.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LibraryEntry:
    name: str
    version: str
    description: str = ""
    source_url: str = ""
    pypi_url: str = ""
    github_url: str = ""
    tags: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryEntry:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})


def _library_path() -> Path:
    home = Path(os.environ.get("DUCKTAP_HOME", str(Path.home() / ".ducktap")))
    p = home / "library.json"
    home.mkdir(parents=True, exist_ok=True)
    return p


def _load(path: Path) -> list[LibraryEntry]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [LibraryEntry.from_dict(item) for item in raw]


def _save(path: Path, entries: list[LibraryEntry]) -> None:
    path.write_text(
        json.dumps([e.to_dict() for e in entries], indent=2) + "\n",
        encoding="utf-8",
    )


def list_entries() -> list[LibraryEntry]:
    """Return all registered library entries."""
    return _load(_library_path())


def search(query: str) -> list[LibraryEntry]:
    """Return entries whose name, description, or tags match *query*."""
    q = query.lower()
    return [
        e for e in _load(_library_path())
        if q in e.name.lower()
        or q in e.description.lower()
        or any(q in t.lower() for t in e.tags)
    ]


def add(entry: LibraryEntry) -> None:
    """Register (or update) an entry in the library."""
    path = _library_path()
    entries = _load(path)
    entries = [e for e in entries if e.name != entry.name]
    entries.append(entry)
    _save(path, entries)


def remove(name: str) -> bool:
    """Remove an entry by name. Returns True if it existed."""
    path = _library_path()
    entries = _load(path)
    before = len(entries)
    entries = [e for e in entries if e.name != name]
    _save(path, entries)
    return len(entries) < before
