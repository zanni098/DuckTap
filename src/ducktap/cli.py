"""Top-level `ducktap` command line."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from ducktap import __version__
from ducktap.catalog import get_entry, list_entries
from ducktap.core import plugins
from ducktap.core.pipeline import discover, press
from ducktap.crowd_sniff import crowd_sniff
from ducktap.library import LibraryEntry
from ducktap.library import add as library_add
from ducktap.library import list_entries as library_list
from ducktap.library import remove as library_remove
from ducktap.library import search as library_search
from ducktap.macros import Macro, list_macros, run_macro
from ducktap.polish import polish, rename
from ducktap.publish import publish as publish_cli
from ducktap.verify.scorecard import score
from ducktap.verify.shipcheck import shipcheck

app = typer.Typer(
    name="ducktap",
    help=(
        "DuckTap -- print agent-native CLIs, MCP servers, and skills from any "
        "API or website."
    ),
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ducktap {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


@app.command("press")
def press_cmd(
    source: str = typer.Argument(..., help="OpenAPI URL/file, HAR file, or website URL"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Output directory"),
    name: str | None = typer.Option(None, "--name", "-n", help="Override CLI name"),
    hint: str | None = typer.Option(None, "--from",
                                       help="Force discoverer: openapi | har | browser-sniff"),
    targets: str = typer.Option(
        "python-cli,mcp-server,skill", "--targets", "-t",
        help="Comma-separated targets to generate.",
    ),
    archetype: str | None = typer.Option(
        None, "--archetype", help="Override the detected domain archetype."),
    insight: str | None = typer.Option(
        None, "--insight", help="Supply the Non-Obvious Insight instead of generating one."),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="Skip LLM steps; use the deterministic NOI only."),
) -> None:
    """One-shot: discover and generate (the default `printing-press` flow)."""
    tgts = [t.strip() for t in targets.split(",") if t.strip()]
    result = press(source, str(out), hint=hint, targets=tgts, name=name,
                   archetype=archetype, insight=insight, use_llm=not no_llm)
    sc = score(result.spec, str(out))
    console.print(f"[bold green]Pressed[/] [bold]{result.spec.name}[/] "
                  f"({len(result.spec.operations)} operations) -> [cyan]{out}[/]")
    console.print(f"  [magenta]archetype[/]: {result.spec.archetype}")
    console.print(f"  [magenta]insight[/]: {result.spec.insight}")
    for tgt, files in result.artifacts.items():
        console.print(f"  [yellow]{tgt}[/]: {len(files)} files")
    console.print(f"\n[bold]Scorecard[/]: {sc.overall}/100 ({sc.grade})")
    for s in sc.scores:
        console.print(f"  - {s.dimension}: {s.score} -- {s.notes}")
    console.print("[dim]Wrote provenance manifest -> "
                  f"{Path(out) / '.ducktap.json'}[/]")


# (no alias needed; the command is named "press" directly)


@app.command()
def research(
    source: str = typer.Argument(...),
    hint: str | None = typer.Option(None, "--from"),
    name: str | None = typer.Option(None, "--name", "-n"),
    out_json: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Run discovery only; emit the normalized APISpec as JSON."""
    spec = discover(source, hint=hint, name=name)
    data = spec.model_dump(by_alias=True)
    text = json.dumps(data, indent=2, default=str)
    if out_json:
        out_json.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote[/] {out_json}")
    else:
        typer.echo(text)


@app.command()
def insight(
    source: str = typer.Argument(..., help="OpenAPI URL/file, HAR file, or .apispec.json"),
    name: str | None = typer.Option(None, "--name", "-n"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Deterministic NOI only."),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model override"),
) -> None:
    """Generate a one-sentence Non-Obvious Insight (NOI) for an API."""
    from ducktap.core.archetype import detect_archetype
    from ducktap.insight import generate_noi
    if source.endswith(".json") and Path(source).exists():
        from ducktap.core.spec import APISpec
        spec = APISpec.model_validate_json(Path(source).read_text(encoding="utf-8"))
    else:
        spec = discover(source, name=name)
    spec.archetype = detect_archetype(spec)
    noi = generate_noi(spec, model=model, use_llm=not no_llm)
    console.print(f"[magenta]archetype[/]: {spec.archetype}")
    console.print(f"[bold]{noi}[/]")


@app.command()
def absorb(
    api_name: str = typer.Argument(..., help="API or service name to research"),
    out: Path | None = typer.Option(None, "--out", "-o",
                                    help="Write the absorb manifest JSON here."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Deterministic baseline only."),
    check: Path | None = typer.Option(None, "--check",
                                      help="Verify a generated CLI dir against must_match features."),
    name: str | None = typer.Option(None, "--name", help="CLI slug for --check (defaults to api_name)."),
    model: str | None = typer.Option(None, "--model"),
) -> None:
    """Catalog the agent-CLI features an API should have (the absorb gate)."""
    from ducktap.absorb import absorb_check, build_absorb_manifest
    manifest = build_absorb_manifest(api_name, model=model, use_llm=not no_llm)
    must = [f["feature"] for f in manifest["features"] if f["priority"] == "must_match"]
    console.print(f"[bold]{api_name}[/] absorb manifest: "
                  f"{len(manifest['features'])} features ({len(must)} must_match)")
    table = Table(title="Expected features")
    table.add_column("feature")
    table.add_column("priority")
    for f in manifest["features"]:
        table.add_row(f["feature"], f["priority"])
    console.print(table)
    if out:
        out.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        console.print(f"[green]Wrote[/] {out}")
    if check is not None:
        result = absorb_check(str(check), name or api_name, manifest)
        if result["passed"]:
            console.print(f"[green]absorb gate PASSED[/] -- matched all "
                          f"{len(result['matched'])} must_match features")
        else:
            console.print(f"[red]absorb gate FAILED[/] -- missing: "
                          f"{', '.join(result['missing'])}")
            raise typer.Exit(5)


@app.command()
def info(
    out_dir: Path = typer.Option(Path("./out"), "--out-dir", "-o",
                                 help="Directory containing a .ducktap.json manifest."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw manifest JSON."),
) -> None:
    """Read and pretty-print the provenance manifest from a press run."""
    from ducktap.manifest import read_manifest
    manifest = read_manifest(str(out_dir))
    if manifest is None:
        console.print(f"[red]No .ducktap.json found in {out_dir}[/]")
        raise typer.Exit(10)
    if json_out:
        typer.echo(json.dumps(manifest, indent=2, default=str))
        return
    console.print(f"[bold]{manifest.get('display_name', manifest['name'])}[/] "
                  f"([cyan]{manifest['name']}[/])")
    console.print(f"  archetype:      {manifest.get('archetype')}")
    console.print(f"  insight:        {manifest.get('insight')}")
    console.print(f"  ducktap:        v{manifest.get('ducktap_version')}")
    console.print(f"  operations:     {manifest.get('operation_count')}")
    console.print(f"  targets:        {', '.join(manifest.get('targets', []))}")
    console.print(f"  spec checksum:  {manifest.get('spec_checksum')}")
    sc = manifest.get("scorecard") or {}
    console.print(f"  scorecard:      {sc.get('overall')}/100 ({sc.get('grade')})")
    console.print(f"  generated at:   {manifest.get('generated_at')}")


@app.command()
def scorecard(
    source: str = typer.Argument(..., help="APISpec JSON file or original source"),
    out_dir: Path = typer.Option(Path("./out"), "--out-dir"),
    fail_under: int = typer.Option(
        0, "--fail-under",
        help="Exit non-zero if overall score is below this threshold (0 = never).",
    ),
) -> None:
    """Score a spec / generated CLI."""
    if source.endswith(".json") and Path(source).exists():
        from ducktap.core.spec import APISpec
        spec = APISpec.model_validate_json(Path(source).read_text(encoding="utf-8"))
    else:
        spec = discover(source)
    sc = score(spec, str(out_dir))
    typer.echo(json.dumps(sc.to_dict(), indent=2))
    if fail_under and sc.overall < fail_under:
        Console(stderr=True).print(
            f"[red]scorecard {sc.overall} < --fail-under {fail_under}[/]"
        )
        raise typer.Exit(2)


@app.command(name="shipcheck")
def shipcheck_cmd(
    name: str = typer.Argument(..., help="CLI slug, e.g. petstore"),
    out_dir: Path = typer.Option(Path("./out"), "--out-dir"),
) -> None:
    """Run structural & runtime sanity checks on a generated CLI."""
    results = shipcheck(str(out_dir), name)
    table = Table(title=f"shipcheck: {name}")
    table.add_column("check")
    table.add_column("pass")
    table.add_column("detail")
    failed = 0
    for r in results:
        table.add_row(r.name,
                      "[green]OK[/]" if r.passed else "[red]FAIL[/]",
                      r.detail[:80])
        if not r.passed:
            failed += 1
    console.print(table)
    if failed:
        raise typer.Exit(1)


catalog_app = typer.Typer(help="Browse and install from the DuckTap catalog.")
app.add_typer(catalog_app, name="catalog")


@catalog_app.command("list")
def catalog_list() -> None:
    """List catalog entries."""
    table = Table(title="DuckTap catalog")
    for col in ("name", "category", "tier", "source"):
        table.add_column(col)
    for e in list_entries():
        table.add_row(e.name, e.category, e.tier, (e.source() or "")[:60])
    console.print(table)


@catalog_app.command("print")
def catalog_print(
    name: str,
    out: Path = typer.Option(Path("./out"), "--out", "-o"),
) -> None:
    """Print a catalog entry's CLI."""
    e = get_entry(name)
    if not e:
        raise typer.BadParameter(f"unknown catalog entry: {name}")
    src = e.source()
    hint = "browser-sniff" if e.sniff_url else None
    result = press(src, str(out), hint=hint, name=e.name)
    console.print(f"[green]Pressed[/] {e.name} -> {out}")
    for tgt, files in result.artifacts.items():
        console.print(f"  {tgt}: {len(files)} files")


plugins_app = typer.Typer(help="Inspect installed DuckTap plugins.")
app.add_typer(plugins_app, name="plugins")


@plugins_app.command("list")
def plugins_list() -> None:
    plugins.autoload_builtins()
    table = Table(title="DuckTap plugins")
    table.add_column("kind")
    table.add_column("name")
    table.add_column("module")
    for n, d in plugins.get_discoverers().items():
        table.add_row("discoverer", n, type(d).__module__)
    for n, g in plugins.get_generators().items():
        table.add_row("generator", n, type(g).__module__)
    console.print(table)


@app.command()
def ui(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Launch the local DuckTap dashboard."""
    from ducktap.webui.app import run
    console.print(f"[bold]DuckTap UI[/] running at http://{host}:{port}")
    run(host=host, port=port)


@app.command()
def sniff(
    url: str = typer.Argument(..., help="Website URL to sniff"),
    out: Path = typer.Option(Path("./out"), "--out", "-o"),
    name: str | None = typer.Option(None, "--name", "-n"),
    wait_ms: int = typer.Option(8000, "--wait-ms"),
    headless: bool = typer.Option(True, "--headless/--headed"),
) -> None:
    """Drive a headless browser, capture network calls, generate a CLI."""
    result = press(url, str(out), hint="browser-sniff", name=name,
                   wait_ms=wait_ms, headless=headless)
    console.print(f"[green]Sniffed[/] {url} -> [cyan]{out}[/] "
                  f"({len(result.spec.operations)} ops)")




@app.command()
def polish_cmd(
    source: str = typer.Argument(..., help="OpenAPI URL/file, HAR file, or existing .apispec.json"),
    out: Path = typer.Option(Path("./polished.json"), "--out", "-o", help="Output APISpec JSON path"),
    descriptions_only: bool = typer.Option(False, "--descriptions-only",
                                            help="Only polish descriptions, leave summaries untouched."),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model override"),
) -> None:
    """LLM-assisted rewrite of operation summaries and descriptions."""
    console.print(f"[bold]Polishing[/] {source} ...")
    spec = polish(source, out_json=out, descriptions_only=descriptions_only, model=model)
    console.print(f"[green]Polished[/] {len(spec.operations)} operations -> {out}")


@app.command()
def rename_cmd(
    source: str = typer.Argument(..., help="OpenAPI URL/file, HAR file, or existing .apispec.json"),
    out: Path = typer.Option(Path("./renamed.json"), "--out", "-o", help="Output APISpec JSON path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show renames without writing"),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model override"),
) -> None:
    """LLM-assisted renaming of unwieldy operation IDs."""
    console.print(f"[bold]Renaming[/] {source} ...")
    mapping = rename(source, out_json=out, dry_run=dry_run, model=model)
    if not mapping:
        console.print("[yellow]No changes suggested.[/]")
        return
    table = Table(title=f"rename suggestions ({len(mapping)} operations)")
    table.add_column("old")
    table.add_column("new")
    for old, new in mapping.items():
        table.add_row(old, new)
    console.print(table)
    if dry_run:
        console.print("[dim]Use without --dry-run to apply.[/]")
    else:
        console.print(f"[green]Wrote[/] renamed spec -> {out}")


@app.command()
def crowd_sniff_cmd(
    api_name: str = typer.Argument(..., help="API or service name to research"),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model override"),
) -> None:
    """Study existing community CLIs and MCP servers via web search."""
    console.print(f"[bold]Crowd-sniffing[/] {api_name} ...")
    result = crowd_sniff(api_name, model=model)
    console.print(f"[green]Found[/] {result['results_found']} unique sources")
    if result['sources']:
        table = Table(title="Sources")
        table.add_column("Title")
        table.add_column("URL")
        for s in result['sources']:
            table.add_row(s['title'], s['url'])
        console.print(table)
    console.print(result['summary'])


@app.command()
def publish_cmd(
    name: str = typer.Argument(..., help="CLI slug, e.g. petstore"),
    out_dir: Path = typer.Option(Path("./out"), "--out-dir", "-o"),
    github: bool = typer.Option(True, "--github/--no-github"),
    pypi: bool = typer.Option(True, "--pypi/--no-pypi"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    private: bool = typer.Option(False, "--private"),
    skip_shipcheck: bool = typer.Option(False, "--skip-shipcheck"),
) -> None:
    """Publish a generated CLI to GitHub and PyPI."""
    result = publish_cli(
        name=name,
        out_dir=str(out_dir),
        github=github,
        pypi=pypi,
        dry_run=dry_run,
        private=private,
        skip_shipcheck=skip_shipcheck,
    )
    for step in result.steps:
        colour = "green" if step.ok else "red"
        status = "OK" if step.ok else "FAIL"
        console.print(f"  [{colour}]{step.name}[/] {status}")
        if step.stderr:
            console.print(f"    [dim]{step.stderr[:200]}[/]")
    if result.success:
        console.print(f"[bold green]{result.message}[/]")
    else:
        console.print(f"[bold red]{result.message}[/]")
        raise typer.Exit(1)


@app.command()
def smoke(
    source: str = typer.Argument(..., help="OpenAPI URL/file or existing .apispec.json"),
    base_url: str = typer.Option("", "--base-url", help="Override API base URL"),
    auth_token: str = typer.Option("", "--auth-token", help="Bearer token or API key"),
    operation: str = typer.Option("", "--operation", "-o", help="Specific operation to test"),
) -> None:
    """Run a live API smoke test against the first parameter-free GET endpoint."""
    import httpx
    if source.endswith('.json') and Path(source).exists():
        from ducktap.core.spec import APISpec
        spec = APISpec.model_validate_json(Path(source).read_text(encoding='utf-8'))
    else:
        spec = discover(source)

    target = base_url or spec.base_url
    if not target:
        console.print("[red]No base_url configured. Use --base-url.[/]")
        raise typer.Exit(10)

    test_ops = [op for op in spec.operations if op.method == 'GET' and '{' not in op.path]
    if operation:
        test_ops = [op for op in test_ops if op.operation_id == operation]

    if not test_ops:
        console.print("[yellow]No suitable GET endpoint without path params found.[/]")
        raise typer.Exit(10)

    client = httpx.Client(base_url=target, headers={}, timeout=15)
    if auth_token:
        client.headers['Authorization'] = f'Bearer {auth_token}'

    results = []
    for op in test_ops[:3]:
        try:
            r = client.get(op.path)
            status = r.status_code
            ok = status < 400
            results.append({
                'operation': op.operation_id,
                'path': op.path,
                'status': status,
                'ok': ok,
                'elapsed_ms': int(r.elapsed.total_seconds() * 1000),
            })
            colour = 'green' if ok else 'yellow'
            console.print(f'  [{colour}]{op.operation_id}[/] {op.path} -> {status}')
        except Exception as e:
            results.append({
                'operation': op.operation_id,
                'path': op.path,
                'status': 0,
                'ok': False,
                'error': str(e),
            })
            console.print(f'  [red]{op.operation_id}[/] {op.path} -> ERROR: {e}')

    passed = sum(1 for r in results if r['ok'])
    total = len(results)
    console.print(f"[bold]{passed}/{total} smoke tests passed[/]")
    if passed < total:
        raise typer.Exit(5)


@app.command()
def emboss_cmd(
    name: str = typer.Argument(..., help="CLI slug, e.g. petstore"),
    out_dir: Path = typer.Option(Path("./out"), "--out-dir", "-o"),
    brand_name: str = typer.Option("", "--brand-name", help="Override project name"),
    description: str = typer.Option("", "--description", "-d", help="Override description"),
    author: str = typer.Option("", "--author", "-a"),
    license_: str = typer.Option("MIT", "--license"),
    homepage: str = typer.Option("", "--homepage"),
) -> None:
    """Apply a brand stamp to a generated CLI."""
    from ducktap.emboss import BrandStamp, emboss
    stamp = BrandStamp(
        name=brand_name,
        description=description,
        author=author,
        license=license_,
        homepage=homepage,
    )
    modified = emboss(str(out_dir), name, stamp)
    for p in modified:
        console.print(f"[green]Stamped[/] {p}")


@app.command()
def vision_cmd(
    url: str = typer.Argument(..., help="Website URL to screenshot and read"),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model override"),
) -> None:
    """Capture a screenshot and use an LLM to describe the API docs."""
    from ducktap.vision import screenshot_to_text
    console.print(f"[bold]Capturing[/] {url} ...")
    result = screenshot_to_text(url, model=model)
    console.print(result)


library_app = typer.Typer(help="Local registry of printed CLIs.")
app.add_typer(library_app, name="library")


@library_app.command("list")
def library_list_cmd() -> None:
    """List registered CLIs in the local DuckTap Library."""
    entries = library_list()
    if not entries:
        console.print("[yellow]Library is empty. Use 'ducktap library add' to register a CLI.[/]")
        return
    table = Table(title="DuckTap Library")
    table.add_column("name")
    table.add_column("version")
    table.add_column("description")
    table.add_column("tags")
    for e in entries:
        table.add_row(e.name, e.version, e.description[:40], ", ".join(e.tags))
    console.print(table)


@library_app.command("search")
def library_search_cmd(
    query: str = typer.Argument(..., help="Keyword to search")
) -> None:
    """Search the local library by name, description, or tags."""
    entries = library_search(query)
    if not entries:
        console.print(f"[yellow]No results for '{query}'[/]")
        return
    table = Table(title=f"Library search: {query}")
    table.add_column("name")
    table.add_column("version")
    table.add_column("description")
    for e in entries:
        table.add_row(e.name, e.version, e.description[:50])
    console.print(table)


@library_app.command("add")
def library_add_cmd(
    name: str = typer.Argument(..., help="CLI name"),
    version: str = typer.Argument(..., help="Version string"),
    description: str = typer.Option("", "--description", "-d"),
    source_url: str = typer.Option("", "--source-url"),
    pypi_url: str = typer.Option("", "--pypi-url"),
    github_url: str = typer.Option("", "--github-url"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
) -> None:
    """Register a CLI in the local DuckTap Library."""
    import datetime
    entry = LibraryEntry(
        name=name,
        version=version,
        description=description,
        source_url=source_url,
        pypi_url=pypi_url,
        github_url=github_url,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
    )
    library_add(entry)
    console.print(f"[green]Added[/] {name} v{version} to DuckTap Library")


@library_app.command("remove")
def library_remove_cmd(
    name: str = typer.Argument(..., help="CLI name to remove")
) -> None:
    """Remove a CLI from the local DuckTap Library."""
    if library_remove(name):
        console.print(f"[green]Removed[/] {name} from DuckTap Library")
    else:
        console.print(f"[yellow]{name} was not in the library[/]")


macro_app = typer.Typer(help="Run and manage compound command macros.")
app.add_typer(macro_app, name="macro")


@macro_app.command("list")
def macro_list(
    macro_dir: Path = typer.Option(Path("./macros"), "--dir", "-d", help="Directory containing .yaml macro files"),
) -> None:
    """List available macro recipes."""
    macros = list_macros(str(macro_dir))
    if not macros:
        console.print(f"[yellow]No macros found in {macro_dir}[/]")
        return
    table = Table(title=f"Macros in {macro_dir}")
    table.add_column("name")
    table.add_column("description")
    table.add_column("steps")
    for m in macros:
        table.add_row(m["name"], m.get("description", ""), str(len(m.get("steps", []))))
    console.print(table)


@macro_app.command("run")
def macro_run(
    macro_file: Path = typer.Argument(..., help="Path to a .yaml macro recipe"),
    base_url: str = typer.Option("", "--base-url", help="Override API base URL"),
    auth_token: str = typer.Option("", "--auth-token", help="Bearer token or API key"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print steps without calling API"),
) -> None:
    """Execute a compound macro recipe against a live API."""
    macro = Macro.from_file(str(macro_file))
    console.print(f"[bold]Running macro[/] [cyan]{macro.name}[/] ({len(macro.steps)} steps)")

    import httpx
    client = httpx.Client(base_url=base_url or "", headers={})
    if auth_token:
        client.headers["Authorization"] = f"Bearer {auth_token}"

    def invoke(op: str, **params) -> Any:
        if dry_run:
            return {"dry_run": True, "operation": op, "params": params}
        # Naive dispatch: assume operation maps to GET <base_url>/...
        # Real implementation would need APISpec to map operation_id -> method/path
        url = params.pop("url", f"/{op.replace('-', '/')}")
        method = params.pop("method", "GET")
        if method.upper() == "GET":
            r = client.get(url, params=params)
        elif method.upper() == "POST":
            r = client.post(url, json=params)
        else:
            r = client.request(method, url, params=params)
        r.raise_for_status()
        return r.json()

    results = run_macro(macro, invoke)
    for i, result in enumerate(results):
        console.print(f"\n[bold]Step {i + 1} result:[/]")
        console.print(json.dumps(result, indent=2, default=str))


@macro_app.command("new")
def macro_new(
    name: str = typer.Argument(..., help="Name for the new macro"),
    out: Path = typer.Option(Path("./macros"), "--out", "-o", help="Output directory"),
) -> None:
    """Scaffold a new macro recipe YAML file."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.yaml"
    scaffold = (
        f"name: {name}\n"
        "description: Describe what this macro does\n"
        "steps:\n"
        "  - operation: list-pets\n"
        "    params: {}\n"
        "    save_as: pets\n"
        "  - operation: get-pet\n"
        "    params:\n"
        "      petId: '{{ steps[0].id }}'\n"
    )
    path.write_text(scaffold, encoding="utf-8")
    console.print(f"[green]Created[/] macro scaffold -> {path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
