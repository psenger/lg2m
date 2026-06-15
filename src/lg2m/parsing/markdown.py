"""Markdown contract structure for lg2m.

A forward line scanner that pulls out only the lg2m contract shape (PLAN
Section 7): YAML-ish frontmatter (``lg2m_graph``), the canonical ``##`` sections
(``Index``, ``Graph``, ``Data Models``, ``Predicates``, ``Nodes``, ``Edges``),
the ``###`` per-entity sub-sections with their prose, and the ``stateDiagram-v2``
block inside ``## Graph``. It does not build a full Markdown AST.

Prose is the free text under a ``###`` heading; table rows (``|``), blockquote /
``> Note:`` lines (``>``), and hidden ``<!-- lg2m: ... -->`` fences are excluded
(they are parsed by ``tables.py`` / ``meta.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

CANONICAL_SECTIONS = ("Index", "Graph", "Data Models", "Predicates", "Nodes", "Edges")


@dataclass
class Section:
    name: str
    start: int  # 0-based line index of the `## ` heading
    end: int  # exclusive
    lines: list[str]  # body lines (heading excluded)


@dataclass
class Entity:
    id: str  # `### ` heading text, backticks stripped
    section: str  # parent `## ` section name
    start: int
    end: int
    lines: list[str]  # body lines under the `### ` heading
    prose: str  # free prose only (tables/fences/notes excluded)


@dataclass
class MarkdownDoc:
    file: str
    graph_id: str | None
    frontmatter: dict[str, str] = field(default_factory=dict)
    sections: dict[str, Section] = field(default_factory=dict)
    entities: list[Entity] = field(default_factory=list)
    mermaid_lines: list[str] = field(default_factory=list)
    mermaid_start: int | None = None  # 0-based line index of first block-body line

    def entity(self, entity_id: str) -> Entity | None:
        return next((e for e in self.entities if e.id == entity_id), None)


def parse_markdown(text: str, *, file: str = "<md>") -> MarkdownDoc:
    raw = text.splitlines()
    frontmatter, body_start = _parse_frontmatter(raw)
    sections = _split_sections(raw, body_start)
    entities = _split_entities(raw, sections)
    mermaid_lines, mermaid_start = _find_mermaid(raw, sections.get("Graph"))
    return MarkdownDoc(
        file=file,
        graph_id=frontmatter.get("lg2m_graph"),
        frontmatter=frontmatter,
        sections=sections,
        entities=entities,
        mermaid_lines=mermaid_lines,
        mermaid_start=mermaid_start,
    )


def _parse_frontmatter(raw: list[str]) -> tuple[dict[str, str], int]:
    if not raw or raw[0].strip() != "---":
        return {}, 0
    fm: dict[str, str] = {}
    j = 1
    while j < len(raw) and raw[j].strip() != "---":
        if ":" in raw[j]:
            key, _, value = raw[j].partition(":")
            fm[key.strip()] = value.strip()
        j += 1
    return fm, j + 1  # skip the closing ---


def _split_sections(raw: list[str], body_start: int) -> dict[str, Section]:
    headings = [i for i in range(body_start, len(raw)) if raw[i].startswith("## ")]
    sections: dict[str, Section] = {}
    for n, hidx in enumerate(headings):
        end = headings[n + 1] if n + 1 < len(headings) else len(raw)
        name = raw[hidx][3:].strip()
        sections[name] = Section(name=name, start=hidx, end=end, lines=raw[hidx + 1 : end])
    return sections


def _split_entities(raw: list[str], sections: dict[str, Section]) -> list[Entity]:
    entities: list[Entity] = []
    for sec in sections.values():
        heads = [k for k in range(sec.start + 1, sec.end) if raw[k].startswith("### ")]
        for m, k in enumerate(heads):
            e_end = heads[m + 1] if m + 1 < len(heads) else sec.end
            body = raw[k + 1 : e_end]
            entities.append(
                Entity(
                    id=_strip_backticks(raw[k][4:].strip()),
                    section=sec.name,
                    start=k,
                    end=e_end,
                    lines=body,
                    prose=_extract_prose(body),
                )
            )
    return entities


def _find_mermaid(raw: list[str], graph: Section | None) -> tuple[list[str], int | None]:
    if graph is None:
        return [], None
    in_block = False
    start: int | None = None
    collected: list[str] = []
    for idx in range(graph.start + 1, graph.end):
        stripped = raw[idx].strip()
        if not in_block and stripped.startswith("```") and "mermaid" in stripped:
            in_block = True
            start = idx + 1
            continue
        if in_block and stripped.startswith("```"):
            break
        if in_block:
            collected.append(raw[idx])
    return collected, start


def _strip_backticks(text: str) -> str:
    return text.strip().strip("`").strip()


def is_prose_line(line: str) -> bool:
    """True for a free-prose line: not a table row, ``> Note:``, or hidden ``<!-- -->`` fence.

    The single authority on the prose/meta boundary, shared by the parser and ``sync``'s
    Markdown write-back so the two cannot disagree about what counts as prose.
    """
    return not line.strip().startswith(("|", ">", "<!--"))


def _extract_prose(lines: list[str]) -> str:
    kept: list[str] = []
    for ln in lines:
        if not is_prose_line(ln):
            continue
        kept.append(ln.rstrip())

    out: list[str] = []
    prev_blank = False
    for ln in "\n".join(kept).split("\n"):
        blank = ln.strip() == ""
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    return "\n".join(out).strip()
