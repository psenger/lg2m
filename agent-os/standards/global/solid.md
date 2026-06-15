# SOLID Principles

SOLID is five design principles that, applied together, produce code that is easy to test, extend, and maintain. They are not rules to apply mechanically — they are heuristics for managing the cost of change. Each principle describes a different way that a design can resist or invite unnecessary coupling.

---

## S — Single Responsibility Principle

A module should have one reason to change.

A "reason to change" means a stakeholder or concern whose requirements could cause the module to be modified. If two different stakeholders could independently ask for changes to the same module, that module has more than one responsibility and should be split.

### Rules

- A class or function that does two conceptually separate things should become two.
- I/O, transformation, and validation are almost always separate responsibilities — do not mix them in a single function.
- If you struggle to name a module without using "and" or "or", it probably has more than one responsibility.
- Symptoms of violation: long files, functions that need extensive mocking to test, and frequent merge conflicts in the same file from unrelated features.

### Example

```
WRONG — three responsibilities in one class:
  OrderProcessor
    validate(order)       ← validation concern
    save(order)           ← persistence concern
    sendConfirmation()    ← notification concern

RIGHT — one responsibility each:
  OrderValidator.validate(order)
  OrderRepository.save(order)
  OrderNotifier.sendConfirmation(order)
```

---

## O — Open/Closed Principle

A module should be open for extension but closed for modification.

Once a module is working and tested, new behaviour should be added by extending it — not by editing it. Editing existing code risks breaking existing tests and existing callers.

### Rules

- Favour extension points (interfaces, abstract classes, callbacks, composition) over if/switch chains that grow with every new case.
- When adding a new variant of behaviour, ask: can I add a new class/function rather than modify an existing one?
- A long if/switch that must be edited every time a new type is added is a violation — introduce a polymorphic interface instead.
- This principle is most valuable at stable, high-use boundaries. Do not apply it prematurely to code that is still being discovered.

### Example

```
WRONG — must modify existing code to add a new discount type:
  function applyDiscount(order, type):
    if type == 'percent': ...
    if type == 'fixed':   ...
    if type == 'loyalty': ...   ← edit required for each new type

RIGHT — extend by adding a new implementation:
  interface DiscountStrategy:
    apply(order) → amount

  PercentDiscount implements DiscountStrategy
  FixedDiscount   implements DiscountStrategy
  LoyaltyDiscount implements DiscountStrategy   ← no existing code modified
```

---

## L — Liskov Substitution Principle

A subtype must be substitutable for its base type without altering the correctness of the program.

If code works with a `Shape`, it must continue to work correctly when passed a `Circle` or `Rectangle` without knowing which it received. Violations mean the abstraction is wrong — the types are not truly interchangeable.

### Rules

- A subtype must honour the contract of its base type: preconditions cannot be strengthened, postconditions cannot be weakened, invariants must be preserved.
- If a subclass overrides a method in a way that changes its observable behaviour (not just implementation), that is a Liskov violation.
- If calling code needs to inspect the concrete type before using it (`if isinstance(x, SubclassA)`), the abstraction is broken.
- Prefer composition over inheritance when the "is-a" relationship is forced or partial.

### Example

```
WRONG — Square violates Rectangle's contract:
  Rectangle.setWidth(w)  sets width, height unchanged
  Square.setWidth(w)     sets both width AND height  ← violates expectation

  Code that relies on Rectangle's contract breaks when given a Square.

RIGHT — do not inherit where the contract cannot be honoured:
  Use a common Shape interface with an area() method only.
  Rectangle and Square implement Shape independently.
```

---

## I — Interface Segregation Principle

Clients should not be forced to depend on methods they do not use.

A large interface forces every implementor to provide all methods and every caller to import the whole contract, even when only a fraction is needed. Split interfaces along the lines of what each caller actually needs.

### Rules

- Define narrow, role-specific interfaces rather than wide, catch-all ones.
- If a class implements an interface and leaves some methods as `raise NotImplementedError` or empty stubs, the interface is too wide — split it.
- Each caller should depend on the smallest interface that satisfies its needs.
- Narrow interfaces are easier to mock: a mock only needs to implement the methods the code under test actually calls.

### Example

```
WRONG — one wide interface forces unneeded dependencies:
  interface Worker:
    work()
    eat()
    sleep()

  RobotWorker must implement eat() and sleep() despite not needing them.

RIGHT — split by role:
  interface Workable:  work()
  interface Feedable:  eat()
  interface Restable:  sleep()

  HumanWorker  implements Workable, Feedable, Restable
  RobotWorker  implements Workable
```

---

## D — Dependency Inversion Principle

High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details.

This is the principle that makes hexagonal architecture work. The application core (high-level) defines port interfaces. Adapters (low-level) implement those interfaces. The core never imports the adapter — the dependency arrow points inward, toward the core.

### Rules

- High-level policy (business logic) must not import low-level mechanism (database, HTTP client, file system).
- Define the interface in terms of the domain, in the same layer as the code that uses it.
- Inject dependencies through constructors or function parameters — never instantiate them internally.
- This principle is the primary enabler of testability: when high-level code depends on an interface, tests pass a fake; production code passes the real adapter.

### Example

```
WRONG — high-level module depends on low-level detail:
  class OrderService:
    def __init__(self):
      self.db = PostgresDatabase()   ← imports low-level adapter directly

  OrderService is now untestable without a real Postgres instance.

RIGHT — both depend on an abstraction:
  interface OrderRepository:           ← defined in the domain layer
    save(order)
    find_by_id(id)

  class OrderService:
    def __init__(self, repo: OrderRepository):   ← depends on interface
      self.repo = repo

  class PostgresOrderRepository(OrderRepository): ...   ← adapter depends on interface

  In tests:   OrderService(repo=FakeOrderRepository())
  In prod:    OrderService(repo=PostgresOrderRepository(db))
```

---

## How SOLID Relates to Hexagonal Architecture and Orthogonal Design

These principles are not independent ideas — they reinforce each other:

| Principle | Connection |
|-----------|------------|
| **SRP** | Each port and each adapter has one responsibility. |
| **OCP** | New adapters extend the system without modifying the core. |
| **LSP** | All adapters for a port are substitutable — tests can use fakes. |
| **ISP** | Ports are narrow; each caller depends only on what it needs. |
| **DIP** | The core defines ports; adapters implement them. Dependency arrows point inward. |

Violating any of these principles typically makes testing harder. If a test requires excessive setup, broad mocking, or knowledge of internal structure, trace the pain back to a SOLID violation — then fix the design.

---

## Related Documents

- `global/hexagonal-architecture.md` — the structural application of DIP and ISP; ports are the narrow interfaces the core defines
- `global/gang-of-four.md` — Strategy implements OCP; Adapter implements DIP; Decorator implements OCP without subclassing
- `global/dry.md` — SRP and DRY reinforce each other: a module with one responsibility has one place where each piece of knowledge lives
