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
    categories = sorted({e.category for e in entries})
    tiers = sorted({e.tier for e in entries})
    rows = "\n".join(
        f"""<tr data-name="{e.name}" data-category="{e.category}" data-tier="{e.tier}">
              <td><b>{e.name}</b><span>{e.display_name or e.name}</span></td>
              <td>{e.category}</td><td>{e.tier}</td>
              <td>{(e.source() or "")[:72]}</td>
              <td><button class="icon-btn print-entry" data-name="{e.name}" title="Print {e.name}">Print</button></td>
            </tr>"""
        for e in entries
    )
    category_options = "\n".join(f"<option value=\"{c}\">{c}</option>" for c in categories)
    tier_options = "\n".join(f"<option value=\"{t}\">{t}</option>" for t in tiers)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DuckTap Workbench</title>
<style>
 :root {{ color-scheme: light; --ink:#17201b; --muted:#68746d; --line:#d9e2dc; --panel:#f7faf8; --accent:#0f7a5f; --accent-2:#335c9d; --warn:#a15c10; }}
 * {{ box-sizing: border-box }}
 body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; color:var(--ink); background:#eef3f0; }}
 .shell {{ min-height:100vh; display:grid; grid-template-columns: 280px 1fr; }}
 aside {{ padding:24px; background:#17201b; color:#f5fbf7; }}
 main {{ padding:28px; max-width:1280px; width:100%; }}
 h1, h2, h3 {{ margin:0; letter-spacing:0 }}
 .brand {{ display:flex; align-items:center; gap:12px; margin-bottom:28px }}
 .mark {{ width:42px; height:42px; display:grid; place-items:center; background:#f6c84c; color:#17201b; font-weight:900; border-radius:8px }}
 .brand small, .muted {{ color:var(--muted) }}
 aside .muted {{ color:#b7c8be }}
 .status-grid {{ display:grid; gap:12px; margin:24px 0 }}
 .stat {{ border:1px solid rgba(255,255,255,.16); padding:14px; border-radius:8px; background:rgba(255,255,255,.05) }}
 .stat b {{ display:block; font-size:26px }}
 .toolbar {{ display:flex; justify-content:space-between; gap:16px; align-items:end; margin-bottom:18px }}
 .grid {{ display:grid; grid-template-columns:minmax(340px, .8fr) minmax(520px, 1.2fr); gap:18px; align-items:start }}
 .panel {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; box-shadow:0 10px 24px rgba(23,32,27,.06) }}
 .panel h2 {{ font-size:18px; margin-bottom:12px }}
 label {{ display:block; font-size:13px; font-weight:700; margin:12px 0 6px }}
 input, select {{ width:100%; border:1px solid var(--line); border-radius:6px; padding:10px 11px; font:inherit; background:#fff }}
 button {{ border:0; border-radius:6px; padding:10px 13px; font-weight:800; cursor:pointer; background:var(--accent); color:white }}
 button.secondary {{ background:#e9f0ec; color:var(--ink) }}
 .inline {{ display:grid; grid-template-columns:1fr 1fr; gap:10px }}
 .filters {{ display:grid; grid-template-columns:1.2fr .8fr .8fr; gap:10px; margin-bottom:12px }}
 table {{ width:100%; border-collapse:collapse }}
 th, td {{ border-bottom:1px solid var(--line); padding:11px 8px; text-align:left; vertical-align:top; font-size:14px }}
 td:nth-child(4) {{ word-break: break-word; max-width: 280px }}
 th {{ color:var(--muted); font-size:12px; text-transform:uppercase }}
 td span {{ display:block; color:var(--muted); margin-top:3px }}
 .icon-btn {{ padding:7px 10px; background:var(--accent-2) }}
 pre {{ min-height:180px; overflow:auto; background:#101713; color:#e7fff2; padding:14px; border-radius:8px; font-size:13px }}
 .scorecard-panel {{ margin-top:18px }}
 .recent-runs {{ margin-top:18px }}
 .empty {{ color:var(--muted); padding:18px; border:1px dashed var(--line); border-radius:8px; background:var(--panel) }}
 @media (max-width: 920px) {{ .shell {{ grid-template-columns:1fr }} aside {{ padding:18px }} main {{ padding:18px }} .grid, .filters {{ grid-template-columns:1fr }} }}
</style></head>
<body>
 <div class="shell">
  <aside>
   <div class="brand"><div class="mark">DT</div><div><h1>DuckTap Workbench</h1><small>local factory console</small></div></div>
   <p class="muted">Press CLIs, MCP servers, and skills from specs, HAR files, websites, or catalog recipes.</p>
   <div class="status-grid">
    <div class="stat"><b>{len(entries)}</b><span>catalog recipes</span></div>
    <div class="stat"><b>{len(categories)}</b><span>categories</span></div>
    <div class="stat"><b>3</b><span>artifact targets</span></div>
   </div>
   <p class="muted">Output directory follows <code>DUCKTAP_OUT</code>, defaulting to <code>./out</code>.</p>
  </aside>
  <main>
   <div class="toolbar">
    <div><h2>Press Console</h2><p class="muted">Generate and inspect artifacts without leaving the browser.</p></div>
    <button class="secondary" id="refresh-catalog">Refresh catalog</button>
   </div>
   <div class="grid">
    <section class="panel">
     <h2>Print From Source</h2>
     <form id="source-form" class="source-form">
      <label for="source">Source</label>
      <input id="source" name="source" type="text" placeholder="OpenAPI URL, HAR, file, or site" required>
      <div class="inline">
       <div><label for="custom_name">Name</label><input id="custom_name" name="custom_name" type="text" placeholder="optional slug"></div>
       <div><label for="target_hint">Mode</label><select id="target_hint" disabled><option>auto-detect</option></select></div>
      </div>
      <label>&nbsp;</label><button type="submit">Print artifacts</button>
     </form>
     <section id="scorecard-panel" class="scorecard-panel">
      <h2>Latest Result</h2>
      <pre id="result-output">Waiting for a run...</pre>
     </section>
    </section>
    <section class="panel">
     <h2>Catalog</h2>
     <div class="filters">
      <input id="catalog-search" type="text" placeholder="Search recipes">
      <select id="category-filter"><option value="">All categories</option>{category_options}</select>
      <select id="tier-filter"><option value="">All tiers</option>{tier_options}</select>
     </div>
     <table><thead><tr>
       <th>Name</th><th>Category</th><th>Tier</th><th>Source</th><th></th>
     </tr></thead><tbody id="catalog-body">
     {rows or '<tr><td colspan=5><em>No catalog entries found.</em></td></tr>'}
     </tbody></table>
    </section>
   </div>
   <section id="recent-runs" class="recent-runs panel">
    <h2>Recent Runs</h2>
    <div class="empty">Runs appear here after this page prints a catalog entry or source.</div>
   </section>
  </main>
 </div>
 <script>
 const result = document.getElementById('result-output');
 const runs = document.getElementById('recent-runs');
 const search = document.getElementById('catalog-search');
 const category = document.getElementById('category-filter');
 const tier = document.getElementById('tier-filter');

 function filterCatalog() {{
   const q = search.value.toLowerCase();
   document.querySelectorAll('#catalog-body tr').forEach(row => {{
     const matchesText = row.innerText.toLowerCase().includes(q);
     const matchesCategory = !category.value || row.dataset.category === category.value;
     const matchesTier = !tier.value || row.dataset.tier === tier.value;
     row.style.display = matchesText && matchesCategory && matchesTier ? '' : 'none';
   }});
 }}
 [search, category, tier].forEach(el => el.addEventListener('input', filterCatalog));

 async function submitGenerate(body) {{
   result.textContent = 'Pressing artifacts...';
   const res = await fetch('/generate', {{ method:'POST', body }});
   const json = await res.json();
   result.textContent = JSON.stringify(json, null, 2);
   if (res.ok) {{
     runs.innerHTML = '<h2>Recent Runs</h2><pre>' + JSON.stringify(json.spec, null, 2) + '</pre>';
   }}
 }}

 document.getElementById('source-form').addEventListener('submit', event => {{
   event.preventDefault();
   submitGenerate(new FormData(event.currentTarget));
 }});
 document.querySelectorAll('.print-entry').forEach(button => button.addEventListener('click', () => {{
   const body = new FormData();
   body.append('name', button.dataset.name);
   submitGenerate(body);
 }}));
 document.getElementById('refresh-catalog').addEventListener('click', async () => {{
   const res = await fetch('/api/catalog');
   result.textContent = JSON.stringify(await res.json(), null, 2);
 }});
 </script>
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
