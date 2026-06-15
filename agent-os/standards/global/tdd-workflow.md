# TDD Workflow

Test-Driven Development is a design discipline, not a testing strategy. Tests written before implementation drive smaller interfaces, tighter scope, and code that is testable by construction. Tests should verify behaviour through public interfaces — not implementation details. Code can change entirely; tests should not need to.

---

## Planning Before You Start

### Rules

- Before writing any code, confirm what interface changes are needed and which behaviours to test.
- List the behaviours to test — not implementation steps. Get alignment before writing any test.
- You cannot test everything. Prioritise critical paths and complex logic over exhaustive edge-case coverage.
- Identify opportunities for deep modules and design interfaces for testability before committing to a structure.

---

## The Red-Green-Refactor Cycle

Every unit of work follows three steps in order, without skipping.

### Rules

- **Red** — Write one failing test that describes the behaviour you intend to implement. Run it. Confirm it fails for the right reason.
- **Green** — Write the minimum code required to make that one test pass. No more.
- **Refactor** — Improve the code while keeping all tests green. Never refactor while any test is red.
- Do not write implementation code before a failing test exists.
- Do not refactor and add behaviour in the same step.

### Example

```
RED:   write test → run → confirm it fails for the right reason
GREEN: write minimal code → run → confirm it passes
REFACTOR: improve code → run → confirm still green

Repeat for next behaviour.
```

---

## Vertical Slices — Not Horizontal

### Rules

- Do not write all tests first and then all implementation. This is horizontal slicing and produces tests that verify imagined behaviour, not actual behaviour.
- Horizontal slicing causes tests to become insensitive to real changes — they pass when behaviour breaks and fail when behaviour is fine. You commit to test structure before understanding the implementation.
- Work in vertical slices: one test → one implementation → repeat. Each test responds to what you learned from the previous cycle.
- This is called the **tracer bullet** approach — prove one path works end-to-end before widening.

### Example

```
WRONG (horizontal slicing):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical slices):
  RED → GREEN: test1 → impl1
  RED → GREEN: test2 → impl2
  RED → GREEN: test3 → impl3
```

---

## Spec-First Development with Agent-OS

### Rules

- A spec in `agent-os/specs/` is the gate before any implementation begins.
- Run `/shape-spec` and create a spec before writing any code.
- Acceptance criteria in the spec map one-to-one to test cases.
- The AI agent must not write implementation until the spec exists and at least one failing test is committed.
- If a user says "just build it" without a spec, pause and create the spec first.
- Do not open an implementation PR without a corresponding spec.

### Example

```
1. /shape-spec → spec written to agent-os/specs/<feature>.md
2. Write tests → commit: "test: add failing tests for <feature>"  → confirm RED
3. Implement  → commit: "feat: implement <feature>"              → confirm GREEN
4. Refactor   → commit: "refactor: tidy <feature>"              → confirm still GREEN
5. PR         → spec + tests + implementation ship together
```

---

## What to Test

### Rules

- Test behaviour through public interfaces only — never test private methods or internal collaborators.
- A good test reads like a specification: "user can checkout with valid cart" describes a capability.
- A test that breaks when you refactor internal structure (without changing behaviour) is testing implementation, not behaviour — fix or delete it.
- Mock only at system boundaries: external APIs, databases, time/randomness, filesystem. Do not mock your own classes or internal collaborators.
- Test one logical concept per test case.
- Never verify behaviour through external means (e.g. querying a database directly) when the public interface can be used instead.

### Bad test warning signs

- Mocking internal collaborators or your own classes
- Testing private methods
- Asserting on call counts, call order, or internal flag state
- Test name describes *how* the code works, not *what* it does
- Test breaks when refactoring without any behaviour change
- Verification bypasses the public interface (e.g. reads directly from a database instead of calling the retrieval function)

### Example

```
GOOD — tests observable behaviour through public interface:
  it('returns zero LHC loading for members under 31')
  it('makes a created user retrievable by ID')
  it('returns 400 when conversationId is missing')

BAD — tests implementation details:
  it('calls paymentService.process with the correct total')
  it('sets the isLoading flag to true during fetch')
  it('saves to the users table')

BAD — bypasses public interface to verify:
  createUser({ name: 'Alice' })
  // then queries the database directly to check the row

GOOD — verifies through the public interface:
  user = createUser({ name: 'Alice' })
  retrieved = getUser(user.id)
  assert retrieved.name == 'Alice'
```

---

## Test Levels

### Rules

- **Unit** — pure functions, business logic, domain calculations. No I/O, no network. Mock at the port/interface boundary only.
- **Integration** — HTTP routes, adapter implementations, database queries. Test the contract, not internals. Use in-memory fakes or test containers.
- **End-to-end** — critical user journeys only. Mark and skip in fast CI runs; run on demand.
- Many unit → fewer integration → very few E2E.
- Never use integration tests to cover logic that belongs in unit tests.

---

## Deep Modules and Testable Interfaces

Design for deep modules: small interface, lots of hidden implementation. The smaller the interface, the fewer tests needed. The simpler the parameters, the simpler the test setup.

### Rules

- Accept dependencies as parameters rather than creating them internally — this makes every function trivially testable and mockable.
- Return results rather than producing side effects — pure functions are always easier to test.
- Prefer specific interfaces over generic ones — one function per external operation is easier to mock than one generic dispatcher.
- Ask before implementing: can I reduce the number of methods? Can I simplify the parameters? Can I hide more complexity inside?

### Example

```
Deep module (testable):
┌─────────────────────┐
│  Small Interface    │  ← few methods, simple params
├─────────────────────┤
│                     │
│  Deep Implementation│  ← complex logic hidden inside
│                     │
└─────────────────────┘

Shallow module (hard to test):
┌─────────────────────────────────┐
│       Large Interface           │  ← many methods, complex params
├─────────────────────────────────┤
│  Thin Implementation            │  ← just passes through
└─────────────────────────────────┘

TESTABLE — accepts dependency, returns result:
  processOrder(order, paymentGateway) → result

HARD TO TEST — creates dependency internally, produces side effect:
  processOrder(order) {
    gateway = new StripeGateway()   // hidden dep, cannot mock
    cart.total -= discount          // side effect, cannot assert cleanly
  }
```

---

## Mocking

Mock at system boundaries only. Do not mock what you own. This rule is a direct consequence of hexagonal architecture and orthogonal design — see `global/hexagonal-architecture.md` for the underlying principles.

### Rules

- Mock driven ports (external APIs, databases, message queues, time, randomness, the filesystem) — these are the boundary between your application core and the outside world.
- Do not mock your own classes, internal collaborators, or anything you control. If a test is painful without mocking internals, the components are not orthogonal — fix the design, not the test.
- Mock interfaces (ports), not concrete adapter implementations. Tests should depend on the contract, not the wiring.
- Wrap any third-party library you do not own in an adapter and mock the adapter — never let a third-party type leak into the core.
- Design for mockability: prefer dependency injection and SDK-style interfaces over generic fetchers.
- Prefer specific functions per external operation over one generic dispatcher — each specific function is independently mockable with no conditional logic in the mock.
- Reset mocks between tests to prevent pollution.
- For language and framework-specific mocking examples, see your profile's `testing/mocking.md`.

### Example

```
GOOD — specific SDK-style interface, each operation independently mockable:
  api.getUser(id)
  api.getOrders(userId)
  api.createOrder(data)

BAD — generic fetcher, mock requires conditional logic to handle different endpoints:
  api.fetch(endpoint, options)

GOOD — dependency injected, easy to substitute a mock:
  processPayment(order, paymentClient)

BAD — dependency created internally, cannot be substituted:
  processPayment(order) { client = new StripeClient() }
```

---

## Refactoring After Green

### Rules

- Only refactor when all tests are green.
- After each TDD cycle, look for: duplication, long methods, shallow modules, feature envy, primitive obsession.
- **Duplication** — extract into a shared function or class.
- **Long methods** — break into private helpers; keep tests on the public interface, not the helpers.
- **Shallow modules** — combine or deepen; push complexity behind the interface.
- **Feature envy** — move logic to the module where the data lives.
- **Primitive obsession** — introduce value objects or domain types.
- Consider what the new code reveals about existing code — refactor that too if it is now obviously wrong.
- Run tests after each refactor step before continuing.

---

## Per-Cycle Checklist

After each red-green step, verify:

```
[ ] Test describes behaviour, not implementation
[ ] Test uses public interface only
[ ] Test would survive an internal refactor
[ ] Implementation code is minimal for this test
[ ] No speculative features were added
```

---

## Commit Discipline

### Rules

- Commit failing tests before implementation — this creates an auditable red-green history.
- Use Conventional Commits: `test:` for test-only commits, `feat:` for implementation, `refactor:` for cleanup.
- Never mix test additions, implementation, and refactoring in a single commit.

### Example

```
git log --oneline

a1b2c3d refactor: extract premium calculation into pure function
9e8f7g6 feat: implement get_recommended_products
5d4c3b2 test: add failing tests for premium calculation
```

---

## AI Agent Rules

### Rules

- Before writing any implementation, check: does a spec exist in `agent-os/specs/`? If not, create one first.
- Write failing tests and confirm they are red before writing any implementation code.
- Do not mark a task complete until all tests are green and committed.
- Do not generate placeholder tests that always pass — tests must assert real behaviour.
- Commit failing tests and passing implementation as separate commits.
- If the user says "skip the tests", explain the risk and add tests immediately after — never skip silently.
- Do not call real external APIs (LLMs, payment gateways, etc.) in unit tests — mock at the boundary.
