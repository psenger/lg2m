# Coupling and Cohesion

Low coupling and high cohesion are the two foundational measures of modular design quality. They were formalised by Larry Constantine in the 1960s and remain the most reliable indicators of whether a codebase will be easy or painful to change.

**Coupling** is the degree to which one module depends on another. Lower is better.
**Cohesion** is the degree to which the elements inside a module belong together. Higher is better.

A well-designed module does one thing well (high cohesion) and needs as little as possible from the outside world to do it (low coupling). These two properties reinforce each other: a module that does one thing tends to need fewer external dependencies; a module with few dependencies tends to have a clear, unified purpose.

---

## The Prime Directive: Minimise Dependencies

### Rules

- Every dependency is a liability. It must be imported, initialised, versioned, tested, and updated. Add a dependency only when the alternative is clearly worse.
- Depend on the narrowest interface that satisfies your need. If you need `send(message)`, depend on a `Sender` interface with one method — not on a full messaging SDK with fifty.
- Depend in the direction of stability. A frequently-changing module must not depend on another frequently-changing module. If both change, they will break each other.
- Prefer receiving dependencies over fetching them. A module that accepts collaborators as parameters can be used in any context. A module that imports them directly is bound to that specific implementation.
- Question every import. Before adding a dependency to a module, ask: can this responsibility be pushed to the caller, or handled at a boundary instead?

### Example

```
WRONG — module fetches its own dependencies, depends on three concrete things:
  import DatabaseClient from 'database-sdk'
  import EmailProvider from 'email-sdk'
  import Logger from 'logging-sdk'

  function registerUser(data):
    db = new DatabaseClient(env.DB_URL)
    email = new EmailProvider(env.EMAIL_KEY)
    log = new Logger()
    ...

RIGHT — module accepts what it needs, depends on narrow interfaces:
  function registerUser(data, repo: UserRepository, notifier: Notifier, log: Logger)
    # three narrow interfaces, each with 1-2 methods
    # caller decides what implementations to provide
```

---

## Coupling Types — Worst to Best

Understanding the type of coupling helps identify how to reduce it. Listed from most harmful to least:

| Level | Name | Description | How to fix |
|-------|------|-------------|------------|
| 1 | **Content coupling** | Module A directly modifies the internal data of module B | Enforce encapsulation; expose behaviour, not data |
| 2 | **Common coupling** | Two modules share mutable global state | Eliminate globals; pass state explicitly |
| 3 | **Control coupling** | A passes a flag to B that controls B's internal logic | Split B into two functions; let A call the right one |
| 4 | **Stamp coupling** | A passes a large data structure to B; B uses only part of it | Pass only what B needs; introduce a narrow type |
| 5 | **Data coupling** | A passes only the data B needs, as simple parameters | Acceptable — keep parameters minimal |
| 6 | **Message coupling** | A and B communicate only through well-defined message/event interfaces | Ideal for independent modules |

### Example — Control Coupling

```
WRONG — flag controls internal branching (control coupling):
  function sendNotification(user, message, isUrgent: boolean):
    if isUrgent:
      sms.send(user.phone, message)
    else:
      email.send(user.email, message)

RIGHT — two functions, caller decides:
  function sendSmsNotification(user, message)
  function sendEmailNotification(user, message)
```

### Example — Stamp Coupling

```
WRONG — entire Order passed to a function that only needs the total (stamp coupling):
  function calculateTax(order: Order):
    return order.total * TAX_RATE

RIGHT — pass only what is needed (data coupling):
  function calculateTax(orderTotal: Money):
    return orderTotal * TAX_RATE
```

---

## Cohesion Types — Best to Worst

High cohesion means the elements in a module genuinely belong together. Listed from most to least cohesive:

| Level | Name | Description |
|-------|------|-------------|
| 1 | **Functional** | Every element contributes to a single, well-defined task |
| 2 | **Sequential** | Output of one element feeds the next (pipeline) |
| 3 | **Communicational** | Elements operate on the same data |
| 4 | **Procedural** | Elements follow a sequence but are otherwise unrelated |
| 5 | **Temporal** | Elements are grouped because they happen at the same time (e.g. startup) |
| 6 | **Logical** | Elements are grouped by category but do unrelated things (e.g. a "utils" module) |
| 7 | **Coincidental** | Elements have no meaningful relationship |

Aim for functional or sequential cohesion. Logical and coincidental cohesion are signals to split the module.

```
LOW COHESION — "utils" module does unrelated things:
  utils.formatDate(date)
  utils.validateEmail(email)
  utils.hashPassword(pwd)
  utils.parseCsv(file)
  utils.sendSlack(msg)

HIGH COHESION — each module does one thing:
  DateFormatter.format(date)
  EmailValidator.validate(email)
  PasswordHasher.hash(pwd)
```

---

## Stable Dependencies Principle

Depend in the direction of stability. A module that changes frequently must not depend on another module that also changes frequently.

### Rules

- Stable modules (interfaces, domain models, utility functions) should be depended on freely — they rarely change.
- Unstable modules (HTTP handlers, UI components, adapters) should not be depended on by stable modules.
- If a stable module must use an unstable one, introduce an interface between them so the stable module depends on the interface (stable), not the implementation (unstable).
- Ports in hexagonal architecture are stable by design — they change only when the domain changes.

### Example

```
WRONG — stable domain logic depends on unstable infrastructure:
  OrderService (stable) → PostgresRepository (unstable — DB schema changes)

RIGHT — stable domain logic depends on a stable interface:
  OrderService (stable) → OrderRepository interface (stable)
                               ↑
                    PostgresRepository (unstable)
```

---

## Acyclic Dependencies Principle

The dependency graph must contain no cycles.

### Rules

- A cycle means two modules are so entangled that neither can be changed, tested, or released independently of the other.
- If module A depends on B and B depends on A, extract the shared concern into a third module C that both depend on.
- Run a dependency cycle check in CI for large codebases.
- Cycles in package/module imports are always a design problem — resolve the design rather than using workarounds like deferred imports.

### Example

```
CYCLE — neither can change without breaking the other:
  UserService → OrderService → UserService

FIX — extract the shared concept both need:
  UserService   →  AccountSummary (interface/type)
  OrderService  →  AccountSummary (interface/type)

  Neither UserService nor OrderService knows about the other.
```

---

## Dependency Budget

Treat dependencies as a budget, not a free resource.

### Rules

- For any module, count its direct imports/dependencies. If the count exceeds five to seven, the module likely has more than one responsibility.
- Each new package-level dependency (an npm package, a pip package, an imported library) adds a supply-chain risk, a versioning constraint, and a build-time cost. Justify it explicitly.
- Prefer using language built-ins and standard library before reaching for a third-party package.
- When evaluating a new package dependency, ask: is the value this provides worth the maintenance cost over the next two years?

---

## Related Documents

- `global/solid.md` — Interface Segregation Principle (I) enforces narrow interfaces; Dependency Inversion Principle (D) enforces depending on abstractions
- `global/hexagonal-architecture.md` — ports and adapters enforce the Stable Dependencies Principle structurally; orthogonal design is low coupling applied to component boundaries
- `global/dry.md` — knowledge duplication creates implicit coupling; the single authoritative representation reduces it
- `global/simplicity.md` — YAGNI prevents unnecessary dependencies from being added in the first place
- `global/object-interaction.md` — Law of Demeter is the method-level expression of low coupling
