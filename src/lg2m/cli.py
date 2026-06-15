"""The ``lg2m`` command-line interface (docs/design.md Section 11).

A thin Typer shell over the pipeline: each command turns flags into one
``pipeline`` call plus a renderer, and maps failures to the exit-code contract
(``0`` clean / ``1`` drift or structural error / ``2`` usage or config error).

Importing this module pulls in **no** framework: it depends only on the
framework-free ``pipeline`` / ``report`` / ``config`` / ``discovery`` surface, and
``pipeline.check`` already imports the LangGraph adapter lazily.
"""

from __future__ import annotations

import enum
import json
from pathlib import Path
from typing import NoReturn

import typer

from lg2m import pipeline
from lg2m.config import loader as config_loader
from lg2m.diff.assemble import assemble_doc_model
from lg2m.diff.categories import DriftCategory
from lg2m.discovery.resolve import ConfigError, resolve
from lg2m.parsing.markdown import parse_markdown
from lg2m.report import render_json, render_text
from lg2m.report.model import DriftReport
from lg2m.scaffold import ScaffoldError, generate_code, generate_markdown
from lg2m.sync import run_sync

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib  # API-compatible backport

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Check a LangGraph graph against its Mermaid stateDiagram-v2 contract.",
)

_INIT_TEMPLATE = """\
# lg2m configuration. One [tool.lg2m.graphs.<id>] table per graph.
#
# lg2m never builds your graph; it imports the factory below, compiles it, reads
# the real topology with compiled.get_graph(), and diffs it against the Markdown
# contract. Run `lg2m check` to report drift, `lg2m validate` for a lighter check.

[tool.lg2m.graphs.my_graph]
graph = "my_package.graph:build_graph"   # module:callable -> CompiledStateGraph
markdown = "docs/my_graph.md"            # the Mermaid stateDiagram-v2 contract
sys_path = ["src"]                        # roots prepended to sys.path before import
xray = true                               # flatten subgraphs when reading topology
"""


class OutputFormat(str, enum.Enum):
    text = "text"
    json = "json"


class Prefer(str, enum.Enum):
    code = "code"
    doc = "doc"


# --- shared resolution helpers (every usage/config failure exits 2) ----------


def _resolve_config(config: Path | None) -> Path:
    """Return the config path: the explicit ``--config``, else CWD lg2m.toml / pyproject.toml."""
    if config is not None:
        if not config.is_file():
            _fail(f"config not found: {config}")
        return config
    for name in ("lg2m.toml", "pyproject.toml"):
        candidate = Path.cwd() / name
        if candidate.is_file():
            return candidate
    _fail("no lg2m.toml or pyproject.toml in the current directory; pass --config")


def _load_graphs(path: Path) -> dict[str, dict]:
    try:
        return config_loader.load(path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _fail(f"could not read config {path}: {exc}")


def _resolve_graph_id(graphs: dict[str, dict], graph_id: str | None) -> str:
    if graph_id is not None:
        if graph_id not in graphs:
            _fail(f"unknown graph {graph_id!r}; configured: {_join(graphs)}")
        return graph_id
    if len(graphs) == 1:
        return next(iter(graphs))
    if not graphs:
        _fail("no graphs configured in the config file")
    _fail(f"multiple graphs configured; specify one of: {_join(graphs)}")


def _emit(report: DriftReport, fmt: OutputFormat, *, no_prose: bool = False) -> None:
    if no_prose:
        report.items = [i for i in report.items if i.category is not DriftCategory.PROSE_DRIFT]
    typer.echo(render_json(report) if fmt is OutputFormat.json else render_text(report))


def _join(graphs: dict[str, dict]) -> str:
    return ", ".join(sorted(graphs)) or "(none)"


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(2)


# --- commands ----------------------------------------------------------------

_GRAPH_ID_ARG = typer.Argument(None, help="graph id (optional if exactly one is configured)")
_CONFIG_OPT = typer.Option(None, "-c", "--config", help="path to lg2m.toml or pyproject.toml")
_FORMAT_OPT = typer.Option(OutputFormat.text, "--format", help="output format")
_STRICT_OPT = typer.Option(False, "--strict", help="escalate warning diagnostics to errors")
_NO_PROSE_OPT = typer.Option(False, "--no-prose", help="hide report-only PROSE_DRIFT items")
_INIT_CONFIG_OPT = typer.Option(
    None, "-c", "--config", help="where to write lg2m.toml (default: ./lg2m.toml)"
)
_FROM_DOC_OPT = typer.Option(False, "--from-doc", help="generate annotated code from the contract")
_FROM_CODE_OPT = typer.Option(
    False, "--from-code", help="generate a Markdown skeleton from the compiled graph"
)
_FRAMEWORK_OPT = typer.Option(
    "langgraph", "--framework", help="--from-doc target framework (langgraph only in v1)"
)
_MODEL_STYLE_OPT = typer.Option(
    "typeddict", "--model-style", help="--from-doc model style: typeddict | pydantic"
)
_OUT_OPT = typer.Option(
    None, "--out", help="write here (dir for --from-doc, file for --from-code); default: stdout"
)
_PREFER_OPT = typer.Option(None, "--prefer", help="conflict resolution: code or doc")
_DRY_RUN_OPT = typer.Option(False, "--dry-run", help="report without writing files")
_LOCK_OPT = typer.Option(None, "--lock", help="override default .lg2m.lock path")


@app.command()
def check(
    graph_id: str | None = _GRAPH_ID_ARG,
    config: Path | None = _CONFIG_OPT,
    fmt: OutputFormat = _FORMAT_OPT,
    strict: bool = _STRICT_OPT,
    no_prose: bool = _NO_PROSE_OPT,
) -> None:
    """Reconcile a graph against its Markdown contract and report drift."""
    path = _resolve_config(config)
    gid = _resolve_graph_id(_load_graphs(path), graph_id)
    try:
        report = pipeline.check(path, gid, strict=strict)
    except ConfigError as exc:
        _fail(f"config error: {exc}")
    _emit(report, fmt, no_prose=no_prose)
    raise typer.Exit(report.exit_code)


@app.command()
def validate(
    graph_id: str | None = _GRAPH_ID_ARG,
    config: Path | None = _CONFIG_OPT,
    fmt: OutputFormat = _FORMAT_OPT,
    strict: bool = _STRICT_OPT,
) -> None:
    """Light pre-flight: parse each side, import the entry point, check the state model and else."""
    path = _resolve_config(config)
    gid = _resolve_graph_id(_load_graphs(path), graph_id)
    try:
        report = pipeline.validate(path, gid, strict=strict)
    except ConfigError as exc:
        _fail(f"config error: {exc}")
    _emit(report, fmt)
    raise typer.Exit(report.exit_code)


@app.command("list")
def list_graphs(
    config: Path | None = _CONFIG_OPT,
    fmt: OutputFormat = _FORMAT_OPT,
) -> None:
    """List the graphs configured in the config file."""
    path = _resolve_config(config)
    graphs = _load_graphs(path)
    if fmt is OutputFormat.json:
        payload = {
            gid: {"graph": cfg.get("graph"), "markdown": cfg.get("markdown")}
            for gid, cfg in graphs.items()
        }
        typer.echo(json.dumps(payload, indent=2))
    elif not graphs:
        typer.echo("(no graphs configured)")
    else:
        for gid, cfg in sorted(graphs.items()):
            typer.echo(f"{gid}\tgraph={cfg.get('graph')}\tmarkdown={cfg.get('markdown')}")
    raise typer.Exit(0)


@app.command()
def init(
    config: Path | None = _INIT_CONFIG_OPT,
) -> None:
    """Write a starter lg2m.toml (refuses to overwrite an existing file)."""
    target = config if config is not None else Path.cwd() / "lg2m.toml"
    if target.exists():
        _fail(f"refusing to overwrite existing file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_INIT_TEMPLATE, encoding="utf-8")
    typer.echo(f"wrote {target}")
    raise typer.Exit(0)


@app.command()
def gen(
    graph_id: str | None = _GRAPH_ID_ARG,
    config: Path | None = _CONFIG_OPT,
    from_doc: bool = _FROM_DOC_OPT,
    from_code: bool = _FROM_CODE_OPT,
    framework: str = _FRAMEWORK_OPT,
    model_style: str = _MODEL_STYLE_OPT,
    out: Path | None = _OUT_OPT,
) -> None:
    """Generate a package from the contract, or a contract skeleton from the graph."""
    if from_doc == from_code:
        _fail("pass exactly one of --from-doc / --from-code")
    path = _resolve_config(config)
    graphs = _load_graphs(path)
    gid = _resolve_graph_id(graphs, graph_id)
    if from_doc:
        _gen_from_doc(path, graphs, gid, framework=framework, model_style=model_style, out=out)
    else:
        _gen_from_code(path, gid, out=out)


def _gen_from_doc(
    config_path: Path,
    graphs: dict[str, dict],
    gid: str,
    *,
    framework: str,
    model_style: str,
    out: Path | None,
) -> None:
    """``--from-doc``: read the contract, emit an annotated package (no framework needed)."""
    try:
        resolved = resolve(graphs[gid], base_dir=config_path.parent, graph_id=gid)
    except ConfigError as exc:
        _fail(f"config error: {exc}")
    try:
        text = resolved.markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        _fail(f"cannot read markdown {resolved.markdown_path}: {exc}")
    doc = assemble_doc_model(
        parse_markdown(text, file=str(resolved.markdown_path)),
        file=str(resolved.markdown_path),
    )
    try:
        files = generate_code(doc, framework=framework, model_style=model_style)
    except ScaffoldError as exc:
        _fail(str(exc))
    if out is None:
        for name, src in files.items():
            typer.echo(f"# ===== {name} =====")
            typer.echo(src)
    else:
        _write_files(files, out)
    raise typer.Exit(0)


def _gen_from_code(config_path: Path, gid: str, *, out: Path | None) -> None:
    """``--from-code``: introspect the real graph (lazily) and emit a Markdown skeleton."""
    try:
        result = pipeline.build_code_model(config_path, gid)
    except ConfigError as exc:
        _fail(f"config error: {exc}")
    if result.model is None:
        for diag in result.diagnostics:
            typer.echo(f"{diag.kind.value}: {diag.message}", err=True)
        raise typer.Exit(1)
    text = generate_markdown(result.model)
    if out is None:
        typer.echo(text)
    else:
        _write_text(text, out)
    raise typer.Exit(0)


def _write_files(files: dict[str, str], out_dir: Path) -> None:
    targets = {name: out_dir / name for name in files}
    existing = sorted(str(p) for p in targets.values() if p.exists())
    if existing:
        _fail(f"refusing to overwrite existing file(s): {', '.join(existing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, src in files.items():
        targets[name].write_text(src, encoding="utf-8")
    typer.echo(f"wrote {len(files)} files to {out_dir}")


def _write_text(text: str, out: Path) -> None:
    if out.exists():
        _fail(f"refusing to overwrite existing file: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    typer.echo(f"wrote {out}")


@app.command()
def sync(
    graph_id: str | None = _GRAPH_ID_ARG,
    config: Path | None = _CONFIG_OPT,
    prefer: Prefer | None = _PREFER_OPT,
    dry_run: bool = _DRY_RUN_OPT,
    lock: Path | None = _LOCK_OPT,
) -> None:
    """Reconcile prose between docstrings and the Mermaid contract."""
    path = _resolve_config(config)
    gid = _resolve_graph_id(_load_graphs(path), graph_id)
    try:
        result = run_sync(
            path, gid,
            prefer=prefer.value if prefer else None,
            dry_run=dry_run,
            lock_path=lock,
        )
    except ConfigError as exc:
        _fail(f"config error: {exc}")
    prefix = "(dry run) " if dry_run else ""
    n_written = len(result.code_written) + len(result.md_written)
    typer.echo(
        f"{prefix}{gid}: {n_written} written, "
        f"{len(result.adopted)} adopted, {len(result.unresolved)} unresolved"
    )
    for kind, key in result.code_written:
        typer.echo(f"  code:     {kind}:{key}")
    for kind, key in result.md_written:
        typer.echo(f"  doc:      {kind}:{key}")
    for kind, key in result.adopted:
        typer.echo(f"  adopted:  {kind}:{key}")
    for kind, key in result.conflicts:
        typer.echo(f"  conflict: {kind}:{key}", err=True)
    for kind, key in result.raw_prefix_skips:
        typer.echo(f"  skipped:  {kind}:{key}  (raw prefix)", err=True)
    for kind, key in result.interleaved_skips:
        typer.echo(f"  skipped:  {kind}:{key}  (interleaved)", err=True)
    if result.lock_written:
        typer.echo("  lock:     updated")
    raise typer.Exit(result.exit_code)


if __name__ == "__main__":  # pragma: no cover
    app()
