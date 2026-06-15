# Scaffold + `gen` — Shaping Notes

## Scope

Layer 5 of `lg2m`: a framework-free `scaffold/` package plus a `gen` CLI command that
generates in both directions between the Markdown contract and annotated LangGraph code.

- **In:** `scaffold/` (framework-free code + markdown emitters); a `gen` CLI command with
  `--from-doc` and `--from-code`; LangGraph emission; `--out`/refuse-overwrite/stdout dry-run;
  two `@langgraph` golden round-trips; per-task DoD gates.
- **Out:** LangChain `RunnableBranch` emission (rejected with exit 2 in v1); prose write-back /
  `lg2m sync` / `.lg2m.lock` 3-way merge (docs/design.md Section 12); reconstructing mermaid sugar
  (`<<fork>>`/`<<join>>`/composite) in `--from-code` (canonical flat mermaid only).

## Decisions

1. **Both directions, one layer** — completes `gen` per docs/design.md Section 13 item 5.
2. **LangGraph-only emission for v1** — the introspector and both goldens are LangGraph-only;
   a LangChain emitter would ship untested. `--framework langchain` → exit-2 "not yet supported";
   the flag stays for forward compatibility.
3. **Canonical (flat) mermaid for `--from-code`** — re-parses to the same IR, so the round-trip
   is structural (identity fields), not byte-exact. The introspected `GraphModel` is in topology
   vocabulary (flattened `parent:child` subgraph nodes, `__start__`/`__end__` sentinels, plain
   conditional edges), and the introspector cannot reconstruct the diagram's pseudostates /
   composites. Documented limitation.
4. **String templates, framework-free `scaffold/`** — per-file emitters; no AST lib; no framework
   import. Generated code *does* import the framework (that is the user's code), but the emitter
   does not.
5. **`--model-style` default `typeddict`** — the doc cannot know TypedDict vs pydantic, so
   `--from-doc` must choose; `typeddict` is the default, `pydantic` is opt-in.
6. **`--out` + refuse-overwrite (mirror `init`), stdout dry-run default** — safe and explicit;
   `gen` writes only where asked. `--from-doc --out <dir>` writes the package files;
   `--from-code --out <file>` writes the markdown; no `--out` prints to stdout.
7. **Prose as `TODO`** — no merge in v1; the design note for prose sync lives at
   `docs/prose-sync.md` and is out of scope here.
8. **Thin CLI over `scaffold/`** — mirrors `check`'s thin shell over `pipeline`; the goldens
   exercise the `scaffold` API directly, and CLI tests cover exit codes via `CliRunner`.

## Round-trip semantics (the acceptance bar)

Both goldens assert **structural equality on IR identity fields** (per `ir/identity.md`):
`Node.id`, `Edge(src_id, dst_id, predicate)`, `Route.branches`/`else_target`,
`Predicate.name`, `DataModel.name`. Non-identity fields (prose, docstrings, locations, meta)
are carried but ignored for equality.

- **(a) code → markdown → IR:** introspect the example → `generate_markdown` →
  `parse_markdown` + `assemble_doc_model` → equals the introspected code IR.
- **(b) markdown → code → introspect → IR:** `generate_code` on the example contract → write a
  temp package → compile + introspect → equals `assemble_doc_model` of the same contract.

The example graph cannot *run* (its composition root never imports `predicates.py`, so the
lazy router would `LookupError`), but it can be *introspected* (introspection never invokes the
router), so the goldens that only introspect are safe.

## Context

- **Visuals:** None.
- **References:** prior spec `agent-os/specs/2026-06-14-2225-cli-typer/`; the working example
  `examples/support_pipeline/` and its contract `docs/support_pipeline.md`. See `references.md`.
- **Product alignment:** docs/design.md Sections 10 (scaffolding), 11 (CLI), 12 (limitations), 13 (build
  order item 5), 14 (test strategy: golden round-trips).
- **Complexity:** Rating 4 (Complex); model recommendation Opus.
- **Quality gates:** per-task Definition of Done (`### Done when` blocks in `plan.md`).
