"""Catalog: load YAML recipes from the catalog/ directory."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CatalogEntry(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    category: str = "uncategorized"
    spec_url: str | None = None
    spec_path: str | None = None
    spec_format: str = "yaml"   # json|yaml|har|sniff
    sniff_url: str | None = None
    sniff_actions: list[dict[str, Any]] = Field(default_factory=list)
    homepage: str | None = None
    tier: str = "community"
    notes: str = ""

    def source(self) -> str:
        return self.spec_url or self.spec_path or self.sniff_url or ""


def _catalog_dirs() -> list[Path]:
    dirs: list[Path] = []
    # 1. Recipes bundled inside the installed package (wheel/sdist). This is what
    #    a `pip install ducktap` ships -- see the force-include in pyproject.toml.
    dirs.append(Path(__file__).resolve().parent / "_recipes")
    # 2. Repo-root catalog/ for editable installs and source checkouts.
    dirs.append(Path(__file__).resolve().parents[3] / "catalog")
    # 3. User-supplied extra catalog directory.
    extra = os.environ.get("DUCKTAP_CATALOG")
    if extra:
        dirs.append(Path(extra))
    return [d for d in dirs if d.exists()]


def _recipe_files() -> list[Path]:
    files: list[tuple[Path, Path]] = []
    for d in _catalog_dirs():
        # Recurse one level into category subdirs (library layout),
        # plus top-level YAMLs (built-in layout).
        for p in list(d.glob("*.yaml")) + list(d.glob("*/*.yaml")):
            if any(part.startswith(".") for part in p.relative_to(d).parts):
                continue
            files.append((d, p))
    return [p for _, p in files]


# Parsing ~30 YAML files on every lookup is the dashboard's hottest path: a
# single page render calls list_entries() several times, and get_entry() used
# to re-read the whole catalog to answer one question. Cache the parse and
# invalidate on mtime, which costs one stat per recipe instead.
_cache: tuple[tuple[tuple[str, int], ...], dict[str, CatalogEntry]] | None = None


def _signature(files: list[Path]) -> tuple[tuple[str, int], ...]:
    sig: list[tuple[str, int]] = []
    for p in files:
        try:
            sig.append((str(p), p.stat().st_mtime_ns))
        except OSError:
            continue
    return tuple(sorted(sig))


def load_catalog() -> dict[str, CatalogEntry]:
    global _cache
    files = _recipe_files()
    signature = _signature(files)
    if _cache is not None and _cache[0] == signature:
        return _cache[1]

    out: dict[str, CatalogEntry] = {}
    for p in files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            e = CatalogEntry(**data)
            out[e.name] = e
        except Exception:
            continue
    _cache = (signature, out)
    return out


def list_entries() -> list[CatalogEntry]:
    return sorted(load_catalog().values(), key=lambda e: (e.category, e.name))


def get_entry(name: str) -> CatalogEntry | None:
    return load_catalog().get(name)
