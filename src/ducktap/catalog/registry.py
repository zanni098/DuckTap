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
    here = Path(__file__).resolve().parents[3] / "catalog"
    extra = os.environ.get("DUCKTAP_CATALOG")
    dirs = [here]
    if extra:
        dirs.append(Path(extra))
    return [d for d in dirs if d.exists()]


def load_catalog() -> dict[str, CatalogEntry]:
    out: dict[str, CatalogEntry] = {}
    for d in _catalog_dirs():
        # Recurse one level into category subdirs (library layout),
        # plus top-level YAMLs (built-in layout).
        for p in list(d.glob("*.yaml")) + list(d.glob("*/*.yaml")):
            if any(part.startswith(".") for part in p.relative_to(d).parts):
                continue
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                e = CatalogEntry(**data)
                out[e.name] = e
            except Exception:
                continue
    return out


def list_entries() -> list[CatalogEntry]:
    return sorted(load_catalog().values(), key=lambda e: (e.category, e.name))


def get_entry(name: str) -> CatalogEntry | None:
    return load_catalog().get(name)
