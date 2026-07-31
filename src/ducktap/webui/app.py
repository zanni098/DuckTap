"""DuckTap local dashboard.

A FastAPI app — `ducktap ui` — that turns the press pipeline into a polished
visual workbench:

- Press CLIs / MCP servers / skills from a spec, HAR, website, or catalog recipe
- Pick output targets (Python / Go / Rust / TypeScript / MCP / skill)
- See the detected **archetype**, the generated **Non-Obvious Insight**, the
  **scorecard** (animated per-dimension bars + grade), the artifact tree, and the
  **provenance manifest** (.ducktap.json) — all without leaving the browser
- Browse and filter the catalog; re-run from history
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from ducktap import __version__
from ducktap.catalog import get_entry, list_entries
from ducktap.core.archetype import ARCHETYPES
from ducktap.core.pipeline import press
from ducktap.verify.scorecard import score

_STATIC = Path(__file__).parent / "static"
_TEMPLATES = Path(__file__).parent / "templates"

_TARGETS = [
    ("python-cli", "Python CLI", True),
    ("mcp-server", "MCP server", True),
    ("skill", "Agent skill", True),
    ("go-cli", "Go CLI", False),
    ("rust-cli", "Rust CLI", False),
    ("typescript-cli", "TypeScript CLI", False),
]

# `/generate` fetches a URL of the caller's choosing and writes files to disk.
# The dashboard listens on localhost, which a page in the user's browser can
# reach: without these checks any site could drive the local DuckTap install
# via a cross-origin form POST. The token defends against that, and the
# Sec-Fetch-Site header rejects the cross-site attempt outright on browsers
# that send it.
_CSRF_TOKEN = secrets.token_urlsafe(32)


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(["html"]),
    )


def _home_html() -> str:
    """Render the dashboard.

    Catalog entries come from YAML on disk (including any directory named by
    DUCKTAP_CATALOG), so the template autoescapes rather than trusting them.
    """
    entries = list_entries()
    return _env().get_template("index.html").render(
        version=__version__,
        entries=entries,
        categories=sorted({e.category for e in entries}),
        tiers=sorted({e.tier for e in entries}),
        targets=_TARGETS,
        archetypes=list(ARCHETYPES),
        out_dir=os.environ.get("DUCKTAP_OUT", "./out"),
        csrf_token=_CSRF_TOKEN,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="DuckTap")

    if _STATIC.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return _home_html()

    @app.get("/api/catalog")
    def api_catalog() -> JSONResponse:
        return JSONResponse([e.model_dump() for e in list_entries()])

    @app.get("/api/health")
    def api_health() -> JSONResponse:
        return JSONResponse({
            "ok": True, "version": __version__,
            "archetypes": list(ARCHETYPES),
            "targets": [t[0] for t in _TARGETS],
            "catalog": len(list_entries()),
        })

    @app.post("/generate")
    def gen(name: str | None = Form(None),
            source: str | None = Form(None),
            custom_name: str | None = Form(None),
            archetype: str | None = Form(None),
            use_llm: str | None = Form(None),
            csrf_token: str | None = Form(None),
            target: list[str] | None = Form(None),
            sec_fetch_site: str | None = Header(None)) -> Any:
        if sec_fetch_site is not None and sec_fetch_site not in ("same-origin", "none"):
            raise HTTPException(403, "cross-site requests are not accepted")
        if not csrf_token or not secrets.compare_digest(csrf_token, _CSRF_TOKEN):
            raise HTTPException(403, "missing or invalid CSRF token")
        if name:
            entry = get_entry(name)
            if not entry:
                raise HTTPException(404, f"catalog entry not found: {name}")
            src = entry.source()
            hint = "browser-sniff" if entry.sniff_url else None
            nm: str | None = entry.name
        elif source:
            src = source
            hint = None
            nm = custom_name or None
        else:
            raise HTTPException(400, "provide either name or source")
        out_dir = os.environ.get("DUCKTAP_OUT", "./out")
        targets = target or ["python-cli", "mcp-server", "skill"]
        try:
            result = press(src, out_dir, hint=hint, name=nm,
                           targets=targets, archetype=archetype or None,
                           use_llm=bool(use_llm))
        except Exception as e:  # surface generation errors to the UI
            return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)
        sc = score(result.spec, out_dir)
        return JSONResponse({
            "name": result.spec.name,
            "display_name": result.spec.display_name or result.spec.name,
            "operations": len(result.spec.operations),
            "archetype": result.spec.archetype,
            "insight": result.spec.insight,
            "artifacts": result.artifacts,
            "scorecard": sc.to_dict(),
            "manifest": result.manifest,
        })

    return app


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port)
