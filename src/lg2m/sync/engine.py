"""``run_sync``: reconcile each node/predicate's prose between code and Markdown.

Framework-free even at runtime: it resolves the config, parses the Markdown, and AST-reads
the package's source files for docstrings + spans. It never imports the user module and
never touches the introspector, because prose lives in source text and Markdown, neither
of which needs a compiled graph.

Per entity it runs the pure ``merge.decide``; writes are grouped per file and applied
bottom-to-top (so earlier edits do not invalidate later spans), and the ``.lg2m.lock``
baseline is rewritten only when its content changes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lg2m.annotations import reader
from lg2m.annotations.reader import AnnoRef
from lg2m.config import loader as config_loader
from lg2m.discovery.resolve import ResolvedGraph, resolve
from lg2m.parsing.markdown import Entity, parse_markdown
from lg2m.sync.lockfile import base_hash, dumps_lock, load_lock, set_base
from lg2m.sync.merge import Action, decide
from lg2m.sync.normalize import prose_hash
from lg2m.sync.write_md import write_prose
from lg2m.sync.write_py import write_docstring


@dataclass
class SyncResult:
    code_written: list[tuple[str, str]] = field(default_factory=list)  # (kind, key)
    md_written: list[tuple[str, str]] = field(default_factory=list)
    adopted: list[tuple[str, str]] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    raw_prefix_skips: list[tuple[str, str]] = field(default_factory=list)
    interleaved_skips: list[tuple[str, str]] = field(default_factory=list)
    lock_written: bool = False

    @property
    def unresolved(self) -> list[tuple[str, str]]:
        """Entities that could not be reconciled (drive the non-zero exit)."""
        return [*self.conflicts, *self.raw_prefix_skips, *self.interleaved_skips]

    @property
    def exit_code(self) -> int:
        return 1 if self.unresolved else 0

    @property
    def wrote_files(self) -> bool:
        return bool(self.code_written or self.md_written)


def run_sync(
    config_path: str | Path,
    graph_id: str,
    *,
    prefer: str | None = None,
    dry_run: bool = False,
    lock_path: str | Path | None = None,
) -> SyncResult:
    """Reconcile prose for ``graph_id``. ``prefer`` is ``"code"``, ``"doc"``, or None."""
    config_path = Path(config_path)
    graphs = config_loader.load(config_path)
    resolved = resolve(graphs[graph_id], base_dir=config_path.parent, graph_id=graph_id)
    lock_file = Path(lock_path) if lock_path else config_path.parent / ".lg2m.lock"

    md_text = resolved.markdown_path.read_text(encoding="utf-8")
    doc = parse_markdown(md_text, file=str(resolved.markdown_path))
    md_nodes = {e.id: e for e in doc.entities if e.section == "Nodes"}
    md_predicates = {e.id: e for e in doc.entities if e.section == "Predicates"}

    package_dir = _find_package_dir(resolved)
    code_nodes, code_predicates = _read_code_refs(package_dir)

    lock = load_lock(lock_file)
    before = dumps_lock(lock)
    result = SyncResult()

    code_writes: list[tuple[AnnoRef, str | None, str, str]] = []
    md_writes: list[tuple[Entity, str | None, str, str]] = []

    for kind, code_map, md_map in (
        ("node", code_nodes, md_nodes),
        ("predicate", code_predicates, md_predicates),
    ):
        for key in sorted(code_map.keys() & md_map.keys()):
            ref, entity = code_map[key], md_map[key]
            action = decide(
                base_hash(lock, resolved.graph_id, kind, key), ref.docstring, entity.prose, prefer
            )
            if action is Action.NOOP:
                continue
            if action is Action.CONFLICT:
                result.conflicts.append((kind, key))
            elif action is Action.ADOPT:
                set_base(lock, resolved.graph_id, kind, key, prose_hash(ref.docstring))
                result.adopted.append((kind, key))
            elif action is Action.WRITE_CODE:
                code_writes.append((ref, entity.prose, kind, key))
            elif action is Action.WRITE_MD:
                md_writes.append((entity, ref.docstring, kind, key))

    _apply_code_writes(code_writes, lock, resolved.graph_id, result, dry_run)
    _apply_md_writes(md_writes, resolved.markdown_path, md_text, lock, resolved.graph_id, result,
                     dry_run)

    if dumps_lock(lock) != before:
        result.lock_written = True
        if not dry_run:
            lock_file.write_text(dumps_lock(lock), encoding="utf-8")

    return result


def _apply_code_writes(writes, lock, gid: str, result: SyncResult, dry_run: bool) -> None:
    by_file: dict[str, list] = defaultdict(list)
    for ref, new_prose, kind, key in writes:
        by_file[ref.loc.file].append((ref, new_prose, kind, key))
    for file, items in by_file.items():
        source = Path(file).read_text(encoding="utf-8")
        items.sort(key=lambda t: _anchor(t[0]), reverse=True)  # bottom-to-top keeps spans valid
        changed = False
        for ref, new_prose, kind, key in items:
            written = write_docstring(source, ref, new_prose)
            if written.skipped_raw_prefix:
                result.raw_prefix_skips.append((kind, key))
                continue
            source = written.source
            if written.changed:
                changed = True
                result.code_written.append((kind, key))
            set_base(lock, gid, kind, key, prose_hash(new_prose))
        if changed and not dry_run:
            Path(file).write_text(source, encoding="utf-8")


def _apply_md_writes(writes, md_path: Path, md_text: str, lock, gid: str, result: SyncResult,
                     dry_run: bool) -> None:
    if not writes:
        return
    md_lines = md_text.splitlines()
    writes.sort(key=lambda t: t[0].start, reverse=True)  # bottom-to-top keeps spans valid
    changed = False
    for entity, new_prose, kind, key in writes:
        written = write_prose(md_lines, entity, new_prose)
        if written.refused_interleaved:
            result.interleaved_skips.append((kind, key))
            continue
        md_lines = written.lines
        if written.changed:
            changed = True
            result.md_written.append((kind, key))
        set_base(lock, gid, kind, key, prose_hash(new_prose))
    if changed and not dry_run:
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def _anchor(ref: AnnoRef) -> int:
    return ref.doc_span[0] if ref.doc_span else (ref.body_lineno or 0)


def _read_code_refs(package_dir: Path | None) -> tuple[dict[str, AnnoRef], dict[str, AnnoRef]]:
    nodes: dict[str, AnnoRef] = {}
    predicates: dict[str, AnnoRef] = {}
    if package_dir is None:
        return nodes, predicates
    for path in sorted(package_dir.glob("*.py")):
        for ref in reader.read_file(path).annotations:
            if ref.kind == "node":
                nodes[ref.key] = ref
            elif ref.kind == "predicate":
                predicates[ref.key] = ref
    return nodes, predicates


def _find_package_dir(resolved: ResolvedGraph) -> Path | None:
    """Locate the package source directory from config alone, without importing it."""
    parts = resolved.module.split(".")
    roots = list(resolved.sys_paths) or [resolved.markdown_path.parent]
    for root in roots:
        mod_file = root.joinpath(*parts).with_suffix(".py")
        if mod_file.exists():
            return mod_file.parent
        pkg_init = root.joinpath(*parts, "__init__.py")
        if pkg_init.exists():
            return pkg_init.parent
    return None
