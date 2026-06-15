# Simplicity

Simplicity is an active discipline, not the absence of effort. The simplest solution that works is almost always the best one. Complexity is the primary cost in software — it makes code harder to read, test, change, and delete.

---

## YAGNI — You Aren't Gonna Need It

Do not add functionality until it is needed. Build what the current requirement demands, not what you imagine future requirements might demand.

### Rules

- Do not add parameters, configuration options, or extension points that no current caller uses.
- Do not abstract prematurely. Two lines of similar code is not a problem. An unnecessary abstraction is.
- Do not write code for hypothetical future requirements. Requirements change; speculative code becomes wrong code that must be maintained or deleted.
- Every line of code is a liability: it must be read, understood, tested, and maintained. Code that does not exist has no cost.
- When you genuinely need the feature, add it then — it will be informed by real requirements and real context.

### Example

```
WRONG — speculative extensibility no caller uses:
  function createUser(data, options = {
    notificationChannel: 'email',
    auditLog: true,
    retryOnFailure: false,
    ... 8 more options nobody asked for
  })

RIGHT — build what is needed now:
  function createUser(data)
  # add options when a real requirement demands them
```

---

## KISS — Keep It Simple

Prefer the simplest solution that correctly solves the problem. Do not introduce accidental complexity.

### Rules

- Choose boring technology when it solves the problem. Reach for a complex solution only when a simpler one is demonstrably insufficient.
- Flat is better than nested. A function with three levels of nesting is a candidate for extraction.
- Direct is better than clever. Code that requires a comment to explain what it does is more complex than code that does not.
- The simplest data structure that works is the right one. A plain list is better than a custom tree if a list solves the problem.
- If you cannot explain the solution to a colleague in two sentences, it may be too complex.

### Example

```
WRONG — clever, fragile, hard to follow:
  result = data.reduce((acc, x) => ({...acc, [x.id]: [...(acc[x.id] || []), x]}), {})

RIGHT — direct, readable:
  grouped = {}
  for item in data:
    if item.id not in grouped:
      grouped[item.id] = []
    grouped[item.id].append(item)
```

---

## Kent Beck's Four Rules of Simple Design

In priority order — higher rules take precedence over lower ones.

1. **Passes the tests** — The code must do what is required. No other rule matters if this one is not met.
2. **Reveals intention** — The code communicates its purpose through names, structure, and flow. A reader should understand what the code does without needing to run it.
3. **No duplication** — Every piece of knowledge has a single authoritative representation. (See `global/dry.md`.)
4. **Fewest elements** — Given the above constraints, remove every class, function, variable, and parameter that is not necessary. Fewer elements means less to understand, test, and maintain.

### Rules

- Apply the Four Rules in order. A cleverly minimal solution that fails tests or obscures intent violates a higher rule.
- "Reveals intention" is the rule most often violated by AI-generated code — ask: does this name, structure, and abstraction communicate what it does and why?
- "Fewest elements" is not about line count. A well-named ten-line function with one clear purpose has fewer elements than a three-line function that requires three comments to understand.
- Run the Four Rules as a checklist after each TDD cycle — they are the refactoring criterion.

### Example

```
After GREEN — evaluate with the Four Rules:

1. Passes tests?          → yes
2. Reveals intention?     → does getUsersByStatus(status) clearly say what it does? yes
3. No duplication?        → is the status-filter logic copied elsewhere? no
4. Fewest elements?       → is there a parameter, variable, or method that can be removed?
                            → the `tempList` variable is unnecessary — filter directly
```

---

## Related Documents

- `global/dry.md` — Rule 3 (No duplication) in depth
- `global/tdd-workflow.md` — the TDD cycle is where the Four Rules are applied
- `global/solid.md` — SOLID principles are specific applications of these broader simplicity rules
- `global/gang-of-four.md` — patterns solve recurring problems; YAGNI says do not apply a pattern until the problem is actually present
