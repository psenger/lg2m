# lg2m: keeping documentation (prose) in sync

> Design note for the `lg2m sync` verb, shipped in v0.1.0. The `sync` verb is an
> optional, write-only command that is **not** part of the drift-checked contract;
> `check` still only *reports* `PROSE_DRIFT` and never writes. This document
> captures the design decisions that shaped the implementation and lives at
> `docs/` rather than under `examples/` because it is design context, not a
> runnable artifact. The worked example it draws on is `examples/support_pipeline/`,
> whose drift-checked contract is
> `examples/support_pipeline/docs/support_pipeline.md`.

## The thing that makes prose different from everything else

Every other reconciliation in the plan has a source of truth: introspection owns
shape, and the diagram + router mapping are generated from one source so they
can't drift. Reconciliation there is one-directional: when they disagree, code
wins and the doc is wrong.

Prose has no truth. The paragraph under `### classify_intent` isn't derived from
anything introspectable. So the moment you let it live in both the docstring and
the Markdown, you have two writable copies of the same fact and no arbiter.
That's not a "check," it's a sync, and a two-way sync between two human-writable
stores is a git merge without a base. You can detect THAT they differ, but not
WHO moved, which means you can't auto-resolve safely.

Verb boundary: `check` stays read-only and just reports `PROSE_DRIFT` (already in
Section 8, optionally). A new `lg2m sync` is the only thing allowed to write prose
across the boundary. Don't fold prose-writing into `check` (Section 14 promises
`check` writes nothing).

## Where prose lives in code, and the edge problem

Nodes and predicates have an obvious home: the docstring. The IR already
anticipates it (`Node(prose?, docstring?)`, same on `Predicate`). prose = from
Markdown, docstring = from code; sync reconciles the two.

Edges have no home. They're tuples in a router mapping or `add_edge` calls in
`graph.py`, no function to carry a docstring. Three options:

1. Edge prose stays Markdown-only. Asymmetric but honest: nothing in code claims
   what an edge does, so there's nothing to sync. (recommended)
2. Carry edge prose in a third tuple slot on the router mapping. Pollutes the
   routing model with documentation.
3. A side annotation keyed by `(src,dst)`. New surface for little gain.

## A `### node` section is three different things, only one of which syncs

- free prose (the paragraph): no truth, two-way, this is what syncs with the docstring
- metadata table / hidden fence (`| fan-out | parallel |`, `<!-- lg2m: ... -->`):
  derived from introspection, already drift-checked one-directionally. Must NOT
  go into the docstring, or you've turned checked structured data back into
  freehand text that can lie.
- a `> Note:`: explicitly human-only, never checked, Markdown-only by design.

Framing: segment each entity section into (prose | structured-meta | note); only
prose crosses into code.

## Markdown-in-a-docstring is fine if you normalize, lossy if you don't

A docstring can hold GFM, but round-tripping bytes won't work:
- indented to the function body; dedent on read, re-indent on write. A fenced
  code block inside the prose makes indentation ambiguous.
- triple-quote style, trailing blank lines, line endings vary.
- other tools (help(), Sphinx, IDE hovers) render GFM as RST/plain.

Fix: define a normalization (strip common leading indentation, normalize
newlines, trim trailing blanks) and compare/merge on the normalized form.
Round-trip equality is on normalized prose. Keep tables/fences out of the
docstring (their indentation-in-a-docstring is the fragile case).

## What makes the two-way sync actually safe: a baseline

Store a per-entity baseline hash of the last synced prose (a `.lg2m.lock`, or a
hidden fence; lockfile keeps the doc clean). On `sync`, per entity, compare
`hash(code_now)` and `hash(md_now)` against `base_hash`:

- only Markdown changed -> write it into the docstring
- only code changed -> write it into the Markdown
- both changed -> real conflict, refuse and show diff (or honor `--prefer code|doc`)
- neither -> nothing

Hash-only at entity granularity gives those four cases without intra-paragraph
merging. "Both touched the same node's prose -> ask a human" is acceptable and far
simpler than line-level 3-way merge. To auto-merge different sentences of the
same entity later, store the base TEXT (not just hash) and do a 3-way per entity.
Defer that.

Natural extension of Section 10: `gen --from-doc` ("existing prose preserved")
and `gen --from-code` ("prose as TODO") are the one-shot versions; `sync` is the
same operation made incremental and bidirectional with a baseline.

## The decisions to settle

1. Edges: Markdown-only (rec), or pay for an edge-prose home in the routing model?
2. Baseline storage: `.lg2m.lock` (committed, conflicts also surface in git) vs a
   hidden fence in the doc. Lean lockfile.
3. Conflict policy: refuse + diff by default, with `--prefer code|doc` escape
   hatch, or always require an explicit preference?
4. Scope of "prose": confirm we only sync the free-prose slice and leave
   structured-meta (introspection-owned) and `> Note:` (human-only) out of code.

Overall rec: docstrings for nodes/predicates only, edges stay Markdown-only, a
`.lg2m.lock` of per-entity hashes drives a new write-only `lg2m sync` verb,
`check` keeps reporting `PROSE_DRIFT` read-only, only the free-prose slice
crosses the boundary.
