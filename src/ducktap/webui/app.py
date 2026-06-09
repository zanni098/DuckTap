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
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ducktap import __version__
from ducktap.catalog import get_entry, list_entries
from ducktap.core.archetype import ARCHETYPES
from ducktap.core.pipeline import press
from ducktap.verify.scorecard import score

_STATIC = Path(__file__).parent / "static"

_TARGETS = [
    ("python-cli", "Python CLI", True),
    ("mcp-server", "MCP server", True),
    ("skill", "Agent skill", True),
    ("go-cli", "Go CLI", False),
    ("rust-cli", "Rust CLI", False),
    ("typescript-cli", "TypeScript CLI", False),
]


def _home_html() -> str:
    entries = list_entries()
    categories = sorted({e.category for e in entries})
    tiers = sorted({e.tier for e in entries})
    rows = "\n".join(
        f"""<tr data-name="{e.name}" data-category="{e.category}" data-tier="{e.tier}">
              <td><b>{e.name}</b><span>{e.display_name or e.name}</span></td>
              <td><span class="chip">{e.category}</span></td>
              <td><span class="chip chip-{e.tier}">{e.tier}</span></td>
              <td class="src">{(e.source() or "")[:64]}</td>
              <td><button class="icon-btn print-entry" data-name="{e.name}">Press ›</button></td>
            </tr>"""
        for e in entries
    )
    category_options = "\n".join(f'<option value="{c}">{c}</option>' for c in categories)
    tier_options = "\n".join(f'<option value="{t}">{t}</option>' for t in tiers)
    target_boxes = "\n".join(
        f"""<label class="tgt"><input type="checkbox" name="target" value="{val}" {"checked" if on else ""}>
              <span>{label}</span></label>"""
        for val, label, on in _TARGETS
    )
    archetype_options = "\n".join(
        f'<option value="{a}">{a.replace("_", " ")}</option>' for a in ARCHETYPES
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DuckTap Workbench</title>
<style>
 :root {{
   --bg:#0b0f0d; --bg-2:#10171300; --panel:#121a16; --panel-2:#0e1411;
   --ink:#eaf3ee; --muted:#8aa093; --line:#1f2c25; --line-2:#27362e;
   --accent:#2fd39a; --accent-2:#4f9cff; --gold:#f6c84c;
   --good:#2fd39a; --warn:#f6c84c; --bad:#ff6b6b;
   --radius:14px; --shadow:0 16px 40px rgba(0,0,0,.45);
 }}
 * {{ box-sizing:border-box }}
 html,body {{ margin:0; height:100% }}
 body {{ font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
   color:var(--ink); background:radial-gradient(1200px 700px at 80% -10%, #14241d 0%, var(--bg) 55%); }}
 a {{ color:var(--accent) }}
 .shell {{ min-height:100vh; display:grid; grid-template-columns:288px 1fr }}
 aside {{ padding:26px 22px; background:linear-gradient(180deg,#0e1612,#0a0f0c);
   border-right:1px solid var(--line); position:sticky; top:0; height:100vh }}
 main {{ padding:30px 34px; max-width:1320px; width:100% }}
 h1,h2,h3 {{ margin:0; letter-spacing:-.01em }}
 .brand {{ display:flex; align-items:center; gap:13px; margin-bottom:8px }}
 .mark {{ width:46px; height:46px; display:grid; place-items:center; border-radius:12px;
   background:linear-gradient(135deg,var(--gold),#e0a93a); color:#10171a; font-weight:900; font-size:20px;
   box-shadow:0 8px 20px rgba(246,200,76,.25) }}
 .brand h1 {{ font-size:19px }}
 .brand small {{ color:var(--muted); font-weight:600 }}
 .tag {{ color:var(--muted); font-size:13px; line-height:1.5; margin:14px 0 22px }}
 .stat {{ border:1px solid var(--line); padding:14px; border-radius:12px; margin-bottom:11px;
   background:linear-gradient(180deg,rgba(47,211,154,.05),transparent) }}
 .stat b {{ display:block; font-size:24px; font-weight:800 }}
 .stat span {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em }}
 .side-foot {{ position:absolute; bottom:22px; left:22px; right:22px; color:var(--muted); font-size:12px }}
 .side-foot code {{ color:var(--accent) }}
 .topbar {{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:22px; gap:18px }}
 .topbar p {{ color:var(--muted); margin:6px 0 0 }}
 .pill {{ display:inline-flex; align-items:center; gap:7px; padding:6px 12px; border-radius:999px;
   border:1px solid var(--line-2); background:var(--panel); font-size:12px; font-weight:700; color:var(--muted) }}
 .dot {{ width:8px; height:8px; border-radius:50%; background:var(--good); box-shadow:0 0 10px var(--good) }}
 .grid {{ display:grid; grid-template-columns:minmax(360px,.85fr) minmax(440px,1.15fr); gap:18px; align-items:start }}
 .panel {{ background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--line);
   border-radius:var(--radius); padding:20px; box-shadow:var(--shadow) }}
 .panel h2 {{ font-size:16px; margin-bottom:4px }}
 .panel .hint {{ color:var(--muted); font-size:12.5px; margin:0 0 14px }}
 label.fld {{ display:block; font-size:12px; font-weight:800; color:var(--muted); text-transform:uppercase;
   letter-spacing:.05em; margin:14px 0 6px }}
 input[type=text], select {{ width:100%; border:1px solid var(--line-2); border-radius:10px; padding:11px 12px;
   font:inherit; background:#0c1310; color:var(--ink); outline:none; transition:border .15s,box-shadow .15s }}
 input[type=text]:focus, select:focus {{ border-color:var(--accent); box-shadow:0 0 0 3px rgba(47,211,154,.15) }}
 .inline {{ display:grid; grid-template-columns:1fr 1fr; gap:11px }}
 .targets {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:6px }}
 .tgt {{ display:flex; align-items:center; gap:8px; padding:9px 11px; border:1px solid var(--line-2);
   border-radius:10px; font-size:13px; font-weight:600; cursor:pointer; background:#0c1310 }}
 .tgt input {{ accent-color:var(--accent) }}
 .row {{ display:flex; align-items:center; gap:10px; margin-top:12px }}
 .switch {{ display:flex; align-items:center; gap:8px; font-size:13px; color:var(--muted) }}
 button {{ border:0; border-radius:10px; padding:12px 16px; font-weight:800; cursor:pointer;
   background:linear-gradient(135deg,var(--accent),#1fae7f); color:#06120d; transition:transform .08s,filter .15s }}
 button:hover {{ filter:brightness(1.07) }} button:active {{ transform:translateY(1px) }}
 button.secondary {{ background:#16211b; color:var(--ink); border:1px solid var(--line-2) }}
 button.block {{ width:100%; margin-top:16px; font-size:15px }}
 .icon-btn {{ padding:7px 11px; font-size:12px; background:#16211b; color:var(--accent); border:1px solid var(--line-2) }}
 .filters {{ display:grid; grid-template-columns:1.3fr .85fr .85fr; gap:9px; margin-bottom:12px }}
 table {{ width:100%; border-collapse:collapse }}
 th,td {{ border-bottom:1px solid var(--line); padding:10px 8px; text-align:left; vertical-align:middle; font-size:13.5px }}
 th {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.06em }}
 td b {{ font-weight:700 }} td span.sub, td span {{ color:var(--muted) }}
 td.src {{ color:var(--muted); font-family:ui-monospace,monospace; font-size:12px; word-break:break-all; max-width:240px }}
 .chip {{ display:inline-block; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700;
   background:#16211b; color:var(--muted); border:1px solid var(--line-2) }}
 .chip-official {{ color:var(--accent); border-color:rgba(47,211,154,.3) }}
 .tablewrap {{ max-height:430px; overflow:auto }}
 /* result */
 #result {{ margin-top:16px }}
 .result-empty {{ color:var(--muted); padding:26px; border:1px dashed var(--line-2); border-radius:12px; text-align:center }}
 .badges {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:12px }}
 .badge {{ padding:5px 12px; border-radius:999px; font-size:12px; font-weight:800 }}
 .badge-arch {{ background:rgba(79,156,255,.14); color:#8cc0ff; border:1px solid rgba(79,156,255,.3) }}
 .badge-grade {{ background:rgba(47,211,154,.15); color:var(--accent); border:1px solid rgba(47,211,154,.35) }}
 .grade-A {{ color:#2fd39a }} .grade-B {{ color:#9fe27a }} .grade-C {{ color:var(--gold) }}
 .grade-D,.grade-F {{ color:var(--bad) }}
 .noi {{ border-left:3px solid var(--gold); padding:11px 14px; background:rgba(246,200,76,.06);
   border-radius:0 10px 10px 0; font-size:14px; line-height:1.55; margin:4px 0 16px }}
 .bars {{ display:grid; gap:9px; margin:6px 0 14px }}
 .bar {{ display:grid; grid-template-columns:128px 1fr 38px; align-items:center; gap:10px; font-size:12.5px }}
 .bar .track {{ height:8px; border-radius:999px; background:#0c1310; border:1px solid var(--line-2); overflow:hidden }}
 .bar .fill {{ height:100%; border-radius:999px; background:linear-gradient(90deg,var(--accent),#1fae7f);
   width:0; transition:width .7s cubic-bezier(.2,.8,.2,1) }}
 .bar .dim {{ color:var(--muted) }} .bar .val {{ text-align:right; font-weight:700 }}
 .arts {{ display:grid; gap:6px; margin:6px 0 12px }}
 .art {{ display:flex; justify-content:space-between; padding:8px 11px; border:1px solid var(--line-2);
   border-radius:9px; font-size:13px; background:#0c1310 }}
 .art b {{ color:var(--accent) }}
 .prov {{ font-family:ui-monospace,monospace; font-size:11.5px; color:var(--muted); margin-top:10px;
   border-top:1px solid var(--line); padding-top:10px; word-break:break-all }}
 .runs {{ display:grid; gap:8px }}
 .run {{ display:flex; justify-content:space-between; align-items:center; padding:10px 13px;
   border:1px solid var(--line-2); border-radius:10px; background:#0c1310; font-size:13px }}
 .spin {{ display:inline-block; width:15px; height:15px; border:2px solid var(--line-2);
   border-top-color:var(--accent); border-radius:50%; animation:spin .7s linear infinite; vertical-align:-2px }}
 @keyframes spin {{ to {{ transform:rotate(360deg) }} }}
 .toast {{ position:fixed; right:22px; bottom:22px; background:var(--panel); border:1px solid var(--line-2);
   color:var(--ink); padding:12px 16px; border-radius:11px; box-shadow:var(--shadow); opacity:0;
   transform:translateY(10px); transition:.25s; font-size:13px; font-weight:600 }}
 .toast.show {{ opacity:1; transform:none }}
 @media (max-width:980px) {{ .shell {{ grid-template-columns:1fr }} aside {{ position:static; height:auto }}
   .grid,.filters,.targets,.inline {{ grid-template-columns:1fr }} }}
</style></head>
<body>
 <div class="shell">
  <aside>
   <div class="brand"><div class="mark">DT</div>
     <div><h1>DuckTap</h1><small>Workbench v{__version__}</small></div></div>
   <p class="tag">Tape any API to your agent. Press agent-native CLIs, MCP servers &amp; skills
     from a spec, HAR, or website — deterministically.</p>
   <div class="status-grid">
    <div class="stat"><b>{len(entries)}</b><span>catalog recipes</span></div>
    <div class="stat"><b>{len(categories)}</b><span>categories</span></div>
    <div class="stat"><b>{len(ARCHETYPES)}</b><span>domain archetypes</span></div>
    <div class="stat"><b>6</b><span>output targets</span></div>
   </div>
   <div class="side-foot">Output dir: <code>${{DUCKTAP_OUT:-./out}}</code><br>Deterministic · no API key required</div>
  </aside>
  <main>
   <div class="topbar">
    <div><h2 style="font-size:24px">Press Console</h2>
      <p>Generate and inspect artifacts — archetype, insight, scorecard &amp; provenance.</p></div>
    <span class="pill"><span class="dot"></span> ready</span>
   </div>
   <div class="grid">
    <section class="panel">
     <h2>Print from source</h2>
     <p class="hint">An OpenAPI URL/file, a HAR capture, or a website to sniff.</p>
     <form id="source-form" class="source-form" autocomplete="off">
      <label class="fld" for="source">Source</label>
      <input id="source" name="source" type="text" placeholder="https://api.example.com/openapi.yaml" required>
      <div class="inline">
       <div><label class="fld" for="custom_name">Name</label>
         <input id="custom_name" name="custom_name" type="text" placeholder="optional slug"></div>
       <div><label class="fld" for="archetype">Archetype</label>
         <select id="archetype" name="archetype"><option value="">auto-detect</option>{archetype_options}</select></div>
      </div>
      <label class="fld">Targets</label>
      <div class="targets">{target_boxes}</div>
      <div class="row"><label class="switch"><input type="checkbox" id="no_llm" name="no_llm" checked> deterministic (no LLM)</label></div>
      <button type="submit" class="block" id="press-btn">Press artifacts</button>
     </form>
    </section>
    <section class="panel" id="scorecard-panel">
     <h2>Result</h2>
     <p class="hint">Archetype, Non-Obvious Insight, scorecard and provenance appear here.</p>
     <div id="result"><div class="result-empty">Press a source or a catalog recipe to see results.</div></div>
    </section>
   </div>

   <section class="panel" style="margin-top:18px">
    <div class="topbar" style="margin-bottom:14px">
     <div><h2>Catalog</h2><p style="margin-top:4px">{len(entries)} ready-to-press recipes.</p></div>
     <button class="secondary" id="refresh-catalog">Refresh</button>
    </div>
    <div class="filters">
     <input id="catalog-search" type="text" placeholder="Search recipes…">
     <select id="category-filter"><option value="">All categories</option>{category_options}</select>
     <select id="tier-filter"><option value="">All tiers</option>{tier_options}</select>
    </div>
    <div class="tablewrap">
     <table><thead><tr><th>Name</th><th>Category</th><th>Tier</th><th>Source</th><th></th></tr></thead>
     <tbody id="catalog-body">
     {rows or '<tr><td colspan=5><em>No catalog entries found.</em></td></tr>'}
     </tbody></table>
    </div>
   </section>

   <section class="panel recent-runs" id="recent-runs" style="margin-top:18px">
    <h2>Recent runs</h2>
    <p class="hint">Presses from this session.</p>
    <div class="runs" id="runs-list"><div class="result-empty">No runs yet.</div></div>
   </section>
  </main>
 </div>
 <div class="toast" id="toast"></div>
 <script>
 const $ = s => document.querySelector(s);
 const result = $('#result'), runsList = $('#runs-list');
 const search = $('#catalog-search'), category = $('#category-filter'), tier = $('#tier-filter');
 const history = [];

 function toast(msg) {{ const t=$('#toast'); t.textContent=msg; t.classList.add('show');
   setTimeout(()=>t.classList.remove('show'),2600); }}

 function filterCatalog() {{
   const q = search.value.toLowerCase();
   document.querySelectorAll('#catalog-body tr').forEach(row => {{
     const okText = row.innerText.toLowerCase().includes(q);
     const okCat = !category.value || row.dataset.category === category.value;
     const okTier = !tier.value || row.dataset.tier === tier.value;
     row.style.display = (okText && okCat && okTier) ? '' : 'none';
   }});
 }}
 [search, category, tier].forEach(el => el.addEventListener('input', filterCatalog));

 function gradeClass(g) {{ return 'grade-' + (g || 'C'); }}

 function renderResult(j) {{
   if (j.error) {{ result.innerHTML = '<div class="result-empty" style="color:var(--bad)">'+j.error+'</div>'; return; }}
   const sc = j.scorecard || {{}};
   const bars = (sc.scores || []).map(s => `
     <div class="bar"><span class="dim">${{s.dimension}}</span>
       <span class="track"><span class="fill" data-w="${{s.score}}"></span></span>
       <span class="val">${{s.score}}</span></div>`).join('');
   const arts = Object.entries(j.artifacts || {{}}).map(([k,v]) =>
     `<div class="art"><span>${{k}}</span><b>${{v.length}} files</b></div>`).join('');
   const m = j.manifest || {{}};
   result.innerHTML = `
     <div class="badges">
       <span class="badge badge-arch">◆ ${{j.archetype || 'unknown'}}</span>
       <span class="badge badge-grade ${{gradeClass(sc.grade)}}">${{sc.overall ?? '–'}}/100 · ${{sc.grade || '–'}}</span>
       <span class="chip">${{j.operations}} operations</span>
     </div>
     ${{j.insight ? '<div class="noi">“'+j.insight+'”</div>' : ''}}
     <div class="bars">${{bars}}</div>
     <div class="arts">${{arts}}</div>
     <div class="prov">manifest · v${{m.ducktap_version || ''}} · ${{m.spec_checksum || ''}}</div>`;
   requestAnimationFrame(()=>document.querySelectorAll('.fill').forEach(f=>f.style.width=f.dataset.w+'%'));
 }}

 function renderRuns() {{
   if (!history.length) {{ runsList.innerHTML = '<div class="result-empty">No runs yet.</div>'; return; }}
   runsList.innerHTML = history.map(h => `
     <div class="run"><span><b>${{h.name}}</b> · ${{h.archetype}} · ${{h.operations}} ops</span>
       <span class="badge badge-grade ${{gradeClass(h.grade)}}">${{h.overall}}/100 ${{h.grade}}</span></div>`).join('');
 }}

 async function submitGenerate(body, label) {{
   $('#press-btn').disabled = true;
   result.innerHTML = '<div class="result-empty"><span class="spin"></span> Pressing '+(label||'')+'…</div>';
   try {{
     const res = await fetch('/generate', {{ method:'POST', body }});
     const j = await res.json();
     renderResult(j);
     if (res.ok && !j.error) {{
       const sc = j.scorecard || {{}};
       history.unshift({{ name:j.name, archetype:j.archetype, operations:j.operations,
         overall:sc.overall, grade:sc.grade }});
       renderRuns();
       toast('Pressed ' + j.name + ' — ' + (sc.grade||'') + ' (' + (sc.overall||0) + '/100)');
     }} else {{ toast('Press failed'); }}
   }} catch (e) {{ result.innerHTML = '<div class="result-empty" style="color:var(--bad)">'+e+'</div>'; }}
   $('#press-btn').disabled = false;
 }}

 $('#source-form').addEventListener('submit', e => {{
   e.preventDefault();
   const f = new FormData(e.currentTarget);
   if (!document.querySelector('input[name=target]:checked')) {{ toast('Pick at least one target'); return; }}
   submitGenerate(f, f.get('source'));
 }});
 document.querySelectorAll('.print-entry').forEach(b => b.addEventListener('click', () => {{
   const body = new FormData(); body.append('name', b.dataset.name);
   document.querySelectorAll('input[name=target]:checked').forEach(t => body.append('target', t.value));
   if ($('#no_llm').checked) body.append('no_llm', 'on');
   submitGenerate(body, b.dataset.name);
 }}));
 $('#refresh-catalog').addEventListener('click', async () => {{
   const r = await fetch('/api/catalog'); toast('Catalog: ' + (await r.json()).length + ' recipes');
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
            no_llm: str | None = Form(None),
            target: list[str] | None = Form(None)) -> Any:
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
                           use_llm=not no_llm)
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
