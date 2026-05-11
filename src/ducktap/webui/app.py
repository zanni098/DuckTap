"""DuckTap local dashboard.

A FastAPI app that lets you:
- Browse the catalog
- Trigger generation
- View past runs and their scorecards
- Tail logs (via SSE)

Designed to be run locally: `ducktap ui`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ducktap.catalog import get_entry, list_entries
from ducktap.core.pipeline import press
from ducktap.verify.scorecard import score

_STATIC = Path(__file__).parent / "static"
_TPL = Path(__file__).parent / "templates"


def _home_html() -> str:
    entries = list_entries()
    rows = "\n".join(
        f"""<tr>
              <td><b>{e.name}</b></td><td>{e.display_name or e.name}</td>
              <td>{e.category}</td><td>{e.tier}</td>
              <td><form method=post action="/generate" style="display:inline">
                <input type=hidden name=name value="{e.name}"/>
                <button>Print</button></form></td>
            </tr>"""
        for e in entries
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>DuckTap</title>
<style>
 body {{ font-family: ui-sans-serif, system-ui; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color:#222 }}
 h1 {{ font-weight: 800; letter-spacing: -0.02em }}
 table {{ width: 100%; border-collapse: collapse }}
 th, td {{ border-bottom: 1px solid #eee; padding: .6rem .4rem; text-align: left; font-size: .95rem }}
 button {{ padding: .25rem .6rem; cursor: pointer }}
 .pill {{ background: #fef3c7; padding: .15rem .5rem; border-radius: 999px; font-size: .8rem }}
 form.adhoc {{ margin: 1rem 0; padding: 1rem; background: #f8fafc; border-radius: 8px }}
 input[type=text] {{ width: 60%; padding: .4rem }}
</style></head>
<body>
 <h1>DuckTap <span class=pill>v0.1.0</span></h1>
 <p>CLI factory for AI agents. Print a Python CLI, MCP server, and skill from any API or website.</p>

 <form class=adhoc method=post action="/generate">
   <h3>Print a CLI from a source</h3>
   <input type=text name=source placeholder="OpenAPI URL, local file, HAR, or website URL" required/>
   <input type=text name=custom_name placeholder="name (optional)"/>
   <button>Print</button>
 </form>

 <h2>Catalog ({len(entries)})</h2>
 <table><thead><tr>
   <th>Name</th><th>Display</th><th>Category</th><th>Tier</th><th></th>
 </tr></thead><tbody>
 {rows or '<tr><td colspan=5><em>No catalog entries found.</em></td></tr>'}
 </tbody></table>

 <h2>Runs</h2>
 <p>See <code>./out/</code> for generated artifacts.</p>
</body></html>
"""


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

    @app.post("/generate")
    def gen(name: str | None = Form(None),
            source: str | None = Form(None),
            custom_name: str | None = Form(None)) -> Any:
        if name:
            entry = get_entry(name)
            if not entry:
                raise HTTPException(404, f"catalog entry not found: {name}")
            src = entry.source()
            hint = "browser-sniff" if entry.sniff_url else None
            nm = entry.name
        elif source:
            src = source
            hint = None
            nm = custom_name or None
        else:
            raise HTTPException(400, "provide either name or source")
        out_dir = os.environ.get("DUCKTAP_OUT", "./out")
        result = press(src, out_dir, hint=hint, name=nm)
        sc = score(result.spec, out_dir)
        return JSONResponse({
            "spec": {"name": result.spec.name, "operations": len(result.spec.operations)},
            "artifacts": result.artifacts,
            "scorecard": sc.to_dict(),
        })

    return app


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port)
