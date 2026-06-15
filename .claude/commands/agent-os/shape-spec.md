# Shape Spec

Gather context and structure planning for significant work. **Run this command while in plan mode.**

## Important Guidelines

- **Always use AskUserQuestion tool** when asking the user anything
- **Offer suggestions** — Present options the user can confirm, adjust, or correct
- **Keep it lightweight** — This is shaping, not exhaustive documentation
- **If AskUserQuestion is unavailable**, present options as a numbered list in plain text and wait for the user to type their selection.

## Prerequisites

This command **must be run in plan mode**.

**Before proceeding, check if you are currently in plan mode.**

If NOT in plan mode, **stop immediately** and tell the user:

```text
Shape-spec must be run in plan mode. Please enter plan mode first, then run /shape-spec again.
```

Do not proceed with any steps below until confirmed to be in plan mode.

## Process

### Step 1: Clarify What We're Building

Use AskUserQuestion to understand the scope:

```text
What are we building? Please describe the feature or change.

(Be as specific as you like — I'll ask follow-up questions if needed)
```

Based on their response, ask 1-2 clarifying questions if the scope is unclear. Examples:
- "Is this a new feature or a change to existing functionality?"
- "What's the expected outcome when this is done?"
- "Are there any constraints or requirements I should know about?"

**Candidate AC capture:** As the user describes the feature, flag any statements that imply observable behaviour as candidate AC items. Record them informally as you go using this format:

```text
[candidate-ac] Given [precondition] / When [action] / Then [outcome]
```

These candidates are not final. They will be presented for confirmation in Step 7 if the user selects the Conversational AC gate style.

### Step 2: Gather Visuals

Use AskUserQuestion:

```markdown
Do you have any visuals to reference?

- Mockups or wireframes
- Screenshots of similar features
- Examples from other apps

(Paste images, share file paths, or say "none")
```

If visuals are provided, note them for inclusion in the spec folder.

**Continue flagging candidate AC items** if the user's description of visuals implies observable behaviour.

### Step 3: Identify Reference Implementations

Use AskUserQuestion:

```markdown
Is there similar code in this codebase I should reference?

Examples:
- "The comments feature is similar to what we're building"
- "Look at how src/features/notifications/ handles real-time updates"
- "No existing references"

(Point me to files, folders, or features to study)
```

If references are provided, read and analyze them to inform the plan.

**Continue flagging candidate AC items** if the reference discussion surfaces expected behaviours not yet captured.

### Step 4: Check Product Context

Check if `agent-os/product/` exists and contains files.

If it exists, read key files (like `mission.md`, `roadmap.md`, `tech-stack.md`) and use AskUserQuestion:

```markdown
I found product context in agent-os/product/. Should this feature align with any specific product goals or constraints?

Key points from your product docs:
- [summarize relevant points]

(Confirm alignment or note any adjustments)
```

If no product folder exists, skip this step.

### Step 5: Surface Relevant Standards

Read `agent-os/standards/index.yml` to identify relevant standards based on the feature being built.

Use AskUserQuestion to confirm:

```markdown
Based on what we're building, these standards may apply:

1. **api/response-format** — API response envelope structure
2. **api/error-handling** — Error codes and exception handling
3. **database/migrations** — Migration patterns

Should I include these in the spec? (yes / adjust: remove 3, add frontend/forms)
```

Read the confirmed standards files to include their content in the plan context.

### Step 6: Generate Spec Folder Name

Create a folder name using this format:

```text
YYYY-MM-DD-HHMM-{feature-slug}/
```

Where:
- Date/time is current timestamp
- Feature slug is derived from the feature description (lowercase, hyphens, max 40 chars)

Example: `2026-01-15-1430-user-comment-system/`

**Note:** If `agent-os/specs/` doesn't exist, create it when saving the spec folder.

### Step 7: Assess Complexity

**This step is mandatory. Do not skip it or merge it with Step 8.**

Apply the rating scale below to the feature described in Step 1.

#### Rating Scale (assess against these criteria)

| Rating | Label | Criteria |
|--------|-------|----------|
| 1 | Trivial | Single file or function change. Pattern already exists. No cross-system impact. < 30 min. |
| 2 | Simple | A few files. Requirements are unambiguous. No new patterns. < 2 hours. |
| 3 | Moderate | Multiple files or systems. At least one design decision. Minor unknowns. < 1 day. |
| 4 | Complex | Cross-cutting concerns, new patterns, or significant unknowns. Touches 3+ systems. 1–3 days. |
| 5 | Very Complex | Architectural change, high uncertainty, large surface area, or context exhaustion risk. > 3 days. |

#### Conservative Assessment Rule

When two ratings are plausible, choose the higher one. Uncertainty about scope, unknown dependencies, or anything that requires investigation before implementation begins are all reasons to rate up, not down. It is safer to over-plan than to discover mid-execution that the work is larger than the spec assumed.

#### What to produce

Assess the feature and determine:

1. **Rating** (1–5) with specific named evidence: file names, systems, or unknowns. Vague justifications are not valid.
2. **Plan structure** based on rating (three tiers — exactly one applies):
   - **Rating 1–2 → Flat:** a single `## Tasks` section with `- [ ] action` items. No `## Task N:` headings. No subtasks. No phases.
   - **Rating 3 → Tasks + subtasks (no phases):** `## Task N: Name` headings, each containing `- [ ] subtask` items. No `**Phase X:**` wrapper. This is the default for Rating 3.
   - **Rating 4–5 → Phases + tasks + subtasks:** `**Phase X: Name**` wrappers containing `**Task X.Y: Name**` blocks, each containing `- [ ] atomic action` items. Group phases by logical boundary (data layer, API, UI, tests).
3. **Model recommendation:**
   - Rating 1–2: Sonnet
   - Rating 3: Sonnet (note if a specific sub-task may need Opus)
   - Rating 4–5: Opus
4. **Context Warning** (Rating 5 only): flag that a single session may exhaust context, and recommend phase split points.

Present the complexity assessment to the user before building the plan:

```markdown
Complexity Assessment

Rating: [N] — [Label]

Evidence:
- [Specific file, system, or unknown]
- [Specific file, system, or unknown]

Plan structure: [flat checklist / phased]
Model recommendation: [Sonnet / Opus]
Reason: [one sentence]

[Context Warning if Rating 5]

Does this assessment look right? (yes / adjust)
```

Wait for confirmation before proceeding.

#### Quality gate selection

After the complexity assessment is confirmed, **use the AskUserQuestion tool** to let the user pick a quality-gate style for this spec. The choice shapes the Step 8 templates and the contents of `shape.md`.

Ask exactly this question:

- **header:** `Quality gates`
- **question:** `Which quality-gate style should this spec use?`
- **multiSelect:** `false`
- **options:**
  1. **Per-task Definition of Done (recommended)** — Each task ends with a `### Done when` checklist (tests pass, lint clean, etc.). Tasks cannot be marked complete until every Done-when item is checked.
  2. **Acceptance criteria up front** — Each task gets explicit acceptance criteria in `shape.md` before implementation. The executing agent verifies against them.
  3. **DoD + Acceptance criteria** — Both gates active. Most rigorous, highest ceremony.
  4. **None (lightweight)** — No gate templates emitted. Use only for Rating 1–2 specs where ceremony exceeds value.
5. **Conversational AC captures** – AC items were flagged during Steps 1–3 as the user described expected behaviour. Present captured candidates now for confirmation, then formalise into Given/When/Then before building the plan. Option 5 implies DoD: `### Done when` blocks are emitted in `plan.md` and reference the confirmed AC IDs.

Record the user's choice as `selected_gates` and apply it consistently in Step 8.

#### If selected_gates is "Conversational AC capture"

Present the candidate AC items collected during Steps 1–3 to the user for review:

```markdown
During our conversation I captured these candidate acceptance criteria. Please confirm, adjust, or remove any items:

1. Given [precondition] / When [action] / Then [outcome]
2. Given [precondition] / When [action] / Then [outcome]
...

(Confirm all / adjust: remove 2, reword 1 / add more)
```

Once confirmed, assign stable IDs (`AC-1`, `AC-2`, …) and write them into `shape.md` under `## Acceptance Criteria`. Task `### Done when` blocks in `plan.md` will reference these IDs (e.g., "AC-1 satisfied").

If no candidate AC items were captured during Steps 1–3, tell the user:

```text
No candidate AC items were captured during shaping. Would you like to write them now, or switch to a different gate style?
```

### Step 8: Structure the Plan

Now build the plan using the structure determined in Step 7. **Task 1 is always "Save spec documentation".**

#### Mandatory: Execution Protocol header

**Every generated `plan.md` MUST begin with the following block, copied verbatim. This is non-negotiable. Do not paraphrase. Do not omit. Do not move it below the Complexity block.**

```markdown
## Execution Protocol (MANDATORY)

These rules govern any agent executing this plan. They are not optional.

1. **The checkbox is the source of truth.** A task is not complete until its checkbox in this file has been changed from `- [ ]` to `- [x]` using the Edit tool. Verbal claims of completion in chat are not completion.
2. **Flip immediately.** After finishing any action, edit this file to update the checkbox **before** beginning the next action. Do not batch checkbox updates across multiple tasks.
3. **Done-when gates are blocking.** If a task has a `### Done when` block, every item in it must be verifiably true before that task's checkbox may be flipped to `[x]`. No exceptions.
4. **Failure stops the run.** If any Done-when item cannot be satisfied, stop. Do not proceed to later tasks. Report the failure and wait for direction.
5. **No silent skips.** If a task is intentionally skipped, change `- [ ]` to `- [~]` and append a one-line note explaining why. Never delete a task.
6. **Self-audit before reporting completion.** Before telling the user the plan is done, re-read this file and confirm every checkbox is `[x]` or `[~]`. If any `[ ]` remains, the plan is not complete.

Violating these rules is a defect. Treat them as you would treat a failing test.
```

This block applies regardless of complexity rating and regardless of gate selection.

#### Flat structure (Rating 1–2)

```markdown
[Execution Protocol block — see above]

## Task 1: Save Spec Documentation

- [ ] Create `agent-os/specs/{folder-name}/` with plan.md, shape.md, standards.md, references.md, visuals/.

## Tasks

- [ ] [Action]
- [ ] [Action]
- [ ] [Action]
```

If `selected_gates` includes DoD, append a `### Done when` block after the `## Tasks` list (single block covering the flat list, since there are no per-task headings).

#### Tasks + subtasks structure (Rating 3)

```markdown
## Execution Protocol

- [ ] Read relevant files before making changes
- [ ] Review applicable standards/related specs before planning
- [ ] Confirm the approach matches the selected complexity

---

## Complexity

**Rating:** 3 — Moderate

**Evidence:**
- [Specific evidence]

**Model Recommendation:** Sonnet
**Reason:** [one sentence]

---

## Task 1: Save Spec Documentation

- [ ] Create `agent-os/specs/{folder-name}/` with plan.md, shape.md, standards.md, references.md, visuals/.

## Task 2: [Name]

- [ ] Subtask
- [ ] Subtask
- [ ] Subtask

### Done when
- [ ] [verifiable condition — e.g., "tests in tests/foo_test.py pass"]
- [ ] [verifiable condition]

## Task 3: [Name]

- [ ] Subtask
- [ ] Subtask

### Done when
- [ ] [verifiable condition]
```

No `**Phase X:**` wrappers. Each subtask must be completable independently in under 2 hours.

If `selected_gates` is option 2 (Acceptance criteria up front) or option 4 (None), omit every `### Done when` block. Options 1, 3, and 5 all emit `### Done when` blocks. When `selected_gates` is option 3 (DoD + AC) or option 5 (Conversational AC capture), each `### Done when` item references an AC ID from `shape.md` (e.g., "AC-2.1 satisfied"). When `selected_gates` is option 1 (DoD only), Done-when items list concrete commands or checks instead.

#### Phased structure (Rating 4–5)

```markdown
## Complexity

**Rating:** [N] — [Label]

**Evidence:**
- [Specific evidence]

**Model Recommendation:** [Sonnet / Opus]
**Reason:** [one sentence]

---

## Task 1: Save Spec Documentation

- [ ] Create `agent-os/specs/{folder-name}/` with plan.md, shape.md, standards.md, references.md, visuals/.

- [ ] **Phase 1: [Name]**

  - [ ] **Task 1.1: [Name]**
    - [ ] Atomic action
    - [ ] Atomic action

    ### Done when
    - [ ] [verifiable condition]
    - [ ] [verifiable condition]

  - [ ] **Task 1.2: [Name]**
    - [ ] Atomic action

    ### Done when
    - [ ] [verifiable condition]
```

Each checkbox item must be completable independently in under 2 hours. If it is not, break it down further.

If `selected_gates` is option 2 (Acceptance criteria up front) or option 4 (None), omit every `### Done when` block. Options 1, 3, and 5 all emit `### Done when` blocks. When `selected_gates` is option 3 (DoD + AC) or option 5 (Conversational AC capture), each `### Done when` item references an AC ID from `shape.md`. When `selected_gates` is option 1 (DoD only), Done-when items list concrete commands or checks instead. Phases themselves do not get a Done-when block – only tasks do. A phase is complete when every task inside it is `[x]`.

Present the full plan structure to the user:

```text
Here's the plan. Task 1 saves all shaping work before implementation begins.

[plan structure]

Does this look right? I'll fill in the implementation tasks next.
```

### Step 9: Complete the Plan

After the structure is confirmed, build out the remaining implementation tasks based on:
- The feature scope from Step 1
- Patterns from reference implementations (Step 3)
- Constraints from standards (Step 5)
- The complexity rating and structure from Step 7

Each task should be specific and actionable. Checkbox items must be atomic.

### Step 10: Ready for Execution

When the full plan is ready:

```text
Plan complete. When you approve and execute:

1. Task 1 will save all spec documentation first
2. Then implementation tasks will proceed

Ready to start? (approve / adjust)
```

## Output Structure

The spec folder will contain:

```text
agent-os/specs/{YYYY-MM-DD-HHMM-feature-slug}/
├── plan.md           # The full plan with complexity block
├── shape.md          # Shaping decisions and context
├── standards.md      # Which standards apply and key points
├── references.md     # Pointers to similar code
└── visuals/          # Mockups, screenshots (if any)
```

## shape.md Content

The shape.md file should capture:

```markdown
# {Feature Name} — Shaping Notes

## Scope

[What we're building, from Step 1]

## Decisions

- [Key decisions made during shaping]
- [Constraints or requirements noted]

## Context

- **Visuals:** [List of visuals provided, or "None"]
- **References:** [Code references studied]
- **Product alignment:** [Notes from product context, or "N/A"]

## Standards Applied

- api/response-format — [why it applies]
- api/error-handling — [why it applies]

## Acceptance Criteria

[Included only when `selected_gates` includes Acceptance criteria. Otherwise omit this section.]

### AC-1: [Short name]
**Given** [precondition]
**When** [action]
**Then** [observable outcome]

### AC-2: [Short name]
**Given** [precondition]
**When** [action]
**Then** [observable outcome]
```

Acceptance criteria use stable IDs (`AC-1`, `AC-2`, …) so `### Done when` blocks in `plan.md` can reference them.

## standards.md Content

Include the full content of each relevant standard:

```markdown
# Standards for {Feature Name}

The following standards apply to this work.

---

## api/response-format

[Full content of the standard file]

---

## api/error-handling

[Full content of the standard file]
```

## references.md Content

```markdown
# References for {Feature Name}

## Similar Implementations

### {Reference 1 name}

- **Location:** `src/features/comments/`
- **Relevance:** [Why this is relevant]
- **Key patterns:** [What to borrow from this]

### {Reference 2 name}

...
```

## Tips

- **Keep shaping fast** — Don't over-document. Capture enough to start, refine as you build.
- **Visuals are optional** — Not every feature needs mockups.
- **Standards guide, not dictate** — They inform the plan but aren't always mandatory.
- **Specs are discoverable** — Months later, someone can find this spec and understand what was built and why.
- **Complexity theater is waste** — Adding phases and sub-tasks beyond what the rating requires makes specs harder to execute, not easier.
- **Conversational AC is lowest ceremony** – If the user is naturally describing behaviour during Steps 1–3, capture it then rather than reconstructing it cold at Step 7.
