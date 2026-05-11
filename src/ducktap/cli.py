"""Top-level `ducktap` command line."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ducktap import __version__
from ducktap.catalog import get_entry, list_entries
from ducktap.core import plugins
from ducktap.core.pipeline import discover, press
from ducktap.verify.scorecard import score
from ducktap.verify.shipcheck import shipcheck

app = typer.Typer(
    name="ducktap",
    help=(
        "DuckTap — print agent-native CLIs, MCP servers, and skills from any "
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


@app.command()
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
) -> None:
    """One-shot: discover and generate (the default `printing-press` flow)."""
    tgts = [t.strip() for t in targets.split(",") if t.strip()]
    result = press(source, str(out), hint=hint, targets=tgts, name=name)
    sc = score(result.spec, str(out))
    console.print(f"[bold green]Pressed[/] [bold]{result.spec.name}[/] "
                  f"({len(result.spec.operations)} operations) -> [cyan]{out}[/]")
    for tgt, files in result.artifacts.items():
        console.print(f"  [yellow]{tgt}[/]: {len(files)} files")
    console.print(f"\n[bold]Scorecard[/]: {sc.overall}/100 ({sc.grade})")
    for s in sc.scores:
        console.print(f"  - {s.dimension}: {s.score} — {s.notes}")


# Convenience alias matching PP's `printing-press` verbs
app.command(name="press")(press_cmd)


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
def scorecard(
    source: str = typer.Argument(..., help="APISpec JSON file or original source"),
    out_dir: Path = typer.Option(Path("./out"), "--out-dir"),
) -> None:
    """Score a spec / generated CLI."""
    if source.endswith(".json") and Path(source).exists():
        from ducktap.core.spec import APISpec
        spec = APISpec.model_validate_json(Path(source).read_text(encoding="utf-8"))
    else:
        spec = discover(source)
    sc = score(spec, str(out_dir))
    typer.echo(json.dumps(sc.to_dict(), indent=2))


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


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main() or 0)
