# Delegation

Delegation is the practice of an object handling a request by passing it to a second "delegate" object rather than doing the work itself. The delegating object remains responsible for the outcome — it coordinates and composes; the delegate executes.

---

## Delegation vs Inheritance

Inheritance and delegation are two different answers to the same question: how does an object gain a capability?

- **Inheritance** says "I *am* a X" — the subclass acquires the capability by being a specialisation of the base class.
- **Delegation** says "I *have* a X that does this for me" — the object acquires the capability by holding a reference to a collaborator and forwarding the relevant calls.

Prefer delegation when the relationship is not a genuine "is-a" relationship, when you want to swap the capability at runtime, or when combining multiple capabilities would require an impractical inheritance hierarchy.

```
INHERITANCE — capability comes from being a subtype:
  class LoggingRepository extends PostgresRepository
    ← now tightly coupled to the parent implementation

DELEGATION — capability comes from forwarding to a collaborator:
  class LoggingRepository
    constructor(inner: Repository)
    save(entity) → inner.save(entity)   ← forwards, adds logging around it
    ← works with any Repository, not just Postgres
```

---

## Rules

- **Delegate to injected collaborators, never to internally constructed ones.** If the delegate is `new`-ed inside the delegating object, it cannot be replaced — this breaks testability and couples the two classes. Pass the delegate in via the constructor. This rule pairs directly with the Dependency Inversion Principle and the dependency injection pattern.
- **The delegating object remains responsible for the outcome.** Delegation is not abandonment. The delegator coordinates the interaction: it decides when to call the delegate, what to pass, and how to handle the result. The delegate executes one specific part of the work.
- **Delegate along port interfaces, not to concrete classes.** The delegating object should depend on an abstraction (an interface or protocol) rather than the concrete class of the delegate. This preserves substitutability and testability.
- **Use delegation to add capabilities without subclassing.** Logging, caching, retrying, auditing, and rate-limiting are all cross-cutting concerns that can be added by wrapping a delegate, not by extending a class. This keeps the base implementation clean and the added behaviour composable.
- **Explicit delegation (forwarding calls) is clearer than implicit delegation (inheritance).** When you forward a call explicitly, the intent is visible in the code. When you rely on inherited methods to do the work, the path of execution is hidden in the class hierarchy.

---

## Delegation vs Composition

These terms are related but distinct:

- **Composition** is the structural relationship: an object *has* a collaborator as a field.
- **Delegation** is the behavioural act: an object *forwards* a call to that collaborator.

Composition is necessary for delegation, but not sufficient. An object may hold a reference to a collaborator and never delegate to it (using it only as a data store, for example). Delegation is the active, runtime use of the composed relationship.

They are complementary: compose your objects structurally, then implement behaviour via delegation to those composed parts.

---

## Examples

### Logger delegating to a Transport

```
interface Transport:
  write(level, message, metadata)

class Logger:
  constructor(transport: Transport)

  info(message, metadata):
    self.transport.write('info', message, metadata)

  error(message, metadata):
    self.transport.write('error', message, metadata)

ConsoleTransport  implements Transport
FileTransport     implements Transport
RemoteTransport   implements Transport

Logger delegates the act of writing to whichever Transport was injected.
Swapping the transport (e.g. in tests) does not require changing Logger.
```

### Repository delegating reads to a cache, writes to a database

```
interface ProductRepository:
  findById(id) → Product | null
  save(product) → Product

class CachingProductRepository implements ProductRepository:
  constructor(
    cache:    CachePort,
    database: ProductRepository,
  )

  findById(id):
    cached = cache.get('product:' + id)
    if cached: return cached
    product = database.findById(id)     ← delegate reads to database
    if product: cache.set('product:' + id, product)
    return product

  save(product):
    result = database.save(product)     ← delegate writes to database
    cache.delete('product:' + result.id)
    return result

Neither the cache nor the database knows about each other.
CachingProductRepository orchestrates; both delegates execute their part.
```

---

## Delegation Enables Decorator, Proxy, and Facade

All three GoF structural patterns are specialised forms of delegation:

| Pattern | How it uses delegation |
|---------|----------------------|
| **Decorator** | Wraps a delegate implementing the same interface; adds behaviour before or after forwarding the call |
| **Proxy** | Wraps a delegate implementing the same interface; controls access, defers initialisation, or intercepts the call |
| **Facade** | Holds references to multiple delegates (subsystem components); composes them into a simpler interface for callers |

The difference is in intent: Decorator adds behaviour, Proxy controls access or defers work, and Facade simplifies a complex subsystem. The mechanical form — hold a reference to a collaborator and forward calls — is the same in all three cases.

---

## Related Documents

- `global/hexagonal-architecture.md` — ports are the interfaces along which delegation flows; adapters are delegates injected at the boundary
- `global/gang-of-four.md` — Decorator, Proxy, and Facade sections show delegation in three different structural forms
- `global/solid.md` — the Dependency Inversion Principle (DIP) explains why delegates must be injected via interfaces; the Single Responsibility Principle (SRP) explains why the delegating object keeps coordination responsibility while the delegate keeps execution responsibility
