# Gang of Four Design Patterns

The Gang of Four (GoF) patterns, from *Design Patterns: Elements of Reusable Object-Oriented Software* (Gamma, Helm, Johnson, Vlissides), are 23 solutions to recurring design problems. They are a vocabulary, not a checklist — use them when the problem they solve is actually present, not to demonstrate familiarity with patterns.

This document covers the patterns most relevant to application architecture, testability, and everyday design decisions. For each pattern, the emphasis is on *when to use it* and *what problem it solves*, not just *what it looks like*.

Patterns are grouped into three categories: **Creational** (how objects are made), **Structural** (how objects are composed), and **Behavioral** (how objects communicate).

---

## Creational Patterns

### Factory Method

Define an interface for creating an object, but let subclasses or callers decide which class to instantiate.

**Use when** the exact type of object to create is determined at runtime, or when you want to decouple object creation from the code that uses the object.

**Testability**: Replace the factory in tests to control what gets created without subclassing the class under test.

```
interface Notifier:
  send(message)

EmailNotifier implements Notifier
SmsNotifier   implements Notifier

function createNotifier(type) → Notifier:
  if type == 'email': return EmailNotifier()
  if type == 'sms':   return SmsNotifier()

In tests: inject a FakeNotifier directly — bypass the factory entirely.
```

---

### Abstract Factory

Provide an interface for creating families of related objects without specifying their concrete classes.

**Use when** a system must be independent of how its objects are created, and you need to enforce that a group of related objects are used together (e.g. a UI theme that must use matching Button, Input, and Dialog).

**Testability**: Swap the entire factory for a test factory that returns fakes. All collaborators are consistently replaced in one place.

```
interface UiFactory:
  createButton() → Button
  createDialog() → Dialog

LightThemeFactory implements UiFactory
DarkThemeFactory  implements UiFactory
TestUiFactory     implements UiFactory   ← returns fakes

Application receives UiFactory — never knows which theme it uses.
```

---

### Builder

Separate the construction of a complex object from its representation.

**Use when** an object has many optional parts, requires a specific construction order, or construction logic is complex enough that it should not live in the object itself.

**Testability**: Builders make test data construction readable and maintainable. Test builder factories are a standard pattern for creating rich domain objects in tests without long constructor calls.

```
order = OrderBuilder()
  .withCustomer(customer)
  .withItem(product, quantity=2)
  .withDiscount(10)
  .build()
```

---

### Singleton

Ensure a class has only one instance and provide global access to it.

**Use sparingly.** Singletons introduce global state, make tests order-dependent, and make it impossible to run tests in parallel without interference. In most cases, dependency injection achieves the same goal without the drawbacks.

**Prefer**: inject a shared instance through the dependency graph rather than using a static `getInstance()` method.

```
AVOID:
  config = Config.getInstance()   ← global, hidden dependency, test-hostile

PREFER:
  class AppConfig: ...
  config = AppConfig(env)
  service = MyService(config)     ← injected, replaceable in tests
```

---

### Flyweight

Share fine-grained objects to support large numbers of instances efficiently.

**Use when** a large number of objects consume too much memory because they store repeated, shared data. Factor out the intrinsic (shared, immutable) state into a flyweight object; keep extrinsic (context-specific) state outside.

**Intrinsic state**: shared, immutable data stored in the flyweight (e.g. a font's character shape data).
**Extrinsic state**: context-specific data passed to the flyweight at use time (e.g. a character's position on screen).

**Common uses**: compiled regex patterns (shared across calls), parsed configuration objects, database connection metadata, template objects.

**Testability**: flyweights are small, immutable, and stateless — trivially testable. Pass extrinsic state as parameters.

```
WITHOUT flyweight:
  10,000 Character objects, each storing: shape_data(50kb) + position + colour
  = 500MB

WITH flyweight:
  26 CharacterType flyweights, each storing: shape_data(50kb)
  10,000 CharacterInstance objects, each storing: flyweight_ref + position + colour
  = 1.3MB + trivial instance data
```

---

## Structural Patterns

### Adapter

Convert the interface of a class into another interface that clients expect.

**Use when** you need to integrate a third-party or legacy component whose interface does not match what your application expects.

**This is the pattern behind hexagonal architecture**. Adapters implement port interfaces, translating between the application's domain language and an external system's API. See `global/hexagonal-architecture.md`.

```
interface EmailSender:         ← port defined by the application core
  send(to, subject, body)

SendGridAdapter implements EmailSender:
  send(to, subject, body):
    self.sendgrid_client.send_message(    ← translates to SendGrid's API
      to=to,
      subject=subject,
      html_content=body,
    )

In tests: FakeEmailSender implements EmailSender — no HTTP calls.
```

---

### Decorator

Attach additional responsibilities to an object dynamically, without subclassing.

**Use when** you want to add behaviour (logging, caching, validation, retries) to an object without modifying its class, and without creating a subclass for every combination of behaviours.

**Testability**: Each decorator wraps a port interface and can be tested independently by passing in a mock of the wrapped interface.

```
interface Repository:
  find(id)
  save(entity)

CachingRepository(Repository) implements Repository:
  find(id):
    if cache.has(id): return cache.get(id)
    result = self.inner.find(id)
    cache.set(id, result)
    return result

LoggingRepository(Repository) implements Repository:
  save(entity):
    logger.info('saving', entity.id)
    self.inner.save(entity)

In production: LoggingRepository(CachingRepository(PostgresRepository()))
In tests:      test the domain with FakeRepository(); test CachingRepository separately.
```

---

### Facade

Provide a simplified interface to a complex subsystem.

**Use when** a subsystem is complex or has many moving parts, and callers only need a narrow slice of its capabilities. The facade does not add behaviour — it simplifies access.

**Testability**: The facade is itself a port-style interface from the caller's perspective. Mock the facade in tests for code that uses it; test the facade separately with integration tests.

```
COMPLEX subsystem: OrderValidator, InventoryChecker, PricingEngine, FraudDetector

FACADE:
  class CheckoutFacade:
    def checkout(cart, payment):
      self.validator.validate(cart)
      self.inventory.reserve(cart.items)
      price = self.pricing.calculate(cart)
      self.fraud.screen(payment, price)
      return self.payments.charge(payment, price)

Callers depend on CheckoutFacade — not on the five subsystems.
```

---

### Proxy

Provide a surrogate or placeholder for another object to control access to it.

**Use when** you need to add access control, lazy initialisation, remote communication, or logging around an object without the client knowing.

**Common forms**: virtual proxy (defer expensive creation), protection proxy (access control), remote proxy (network call behind a local interface).

**Testability**: Like Decorator, a proxy wraps an interface and can be tested by injecting a mock for the wrapped interface.

```
interface ImageLoader:
  load(url) → Image

LazyImageProxy implements ImageLoader:
  load(url):
    if not self._image:
      self._image = RealImageLoader().load(url)   ← deferred until needed
    return self._image
```

---

### Bridge

Separate an abstraction from its implementation so that the two can vary independently.

**Use when** the abstraction and implementation should be extensible via subclassing, and a permanent binding between them would be inflexible. Also useful when implementation details should be hidden from the client entirely.

**Key distinction from Adapter**: Adapter makes two incompatible existing interfaces work together (it fixes a mismatch after the fact). Bridge is designed upfront to allow both the abstraction and implementation to vary independently.

**Testability**: The abstraction depends on an implementation interface — swap implementations in tests without changing the abstraction.

```
Abstraction: Report (defines what a report contains)
Implementation interface: Renderer (defines how to render)

Report → Renderer (interface)
             ↑
    HtmlRenderer   PdfRenderer   CsvRenderer

SalesReport extends Report
SummaryReport extends Report

Both reports work with any renderer — add new report types or renderers independently.
```

---

## Behavioral Patterns

### Strategy

Define a family of algorithms, encapsulate each one, and make them interchangeable.

**Use when** you have multiple variants of a behaviour and want to select among them at runtime, or when you want to isolate the variation from the code that uses it.

**This is the pattern behind the Open/Closed Principle**. Add new strategies without modifying existing code.

**Testability**: Each strategy is a small, independently testable unit. The context class can be tested with a fake strategy.

```
interface SortStrategy:
  sort(data) → data

QuickSort  implements SortStrategy
MergeSort  implements SortStrategy
TimSort    implements SortStrategy

class DataPipeline:
  def __init__(self, sort_strategy: SortStrategy):
    self.sort = sort_strategy

  def process(data):
    return self.sort.sort(data)
```

---

### Observer

Define a one-to-many dependency so that when one object changes state, all its dependents are notified automatically.

**Use when** a change in one object requires updating others, and you do not want those objects tightly coupled.

**Common names**: event system, pub/sub, signals, hooks, listeners.

**Testability**: Inject a fake observer or collect emitted events in a list during tests. Never assert on internal state — assert on the events emitted through the observable interface.

```
interface OrderEventListener:
  on_order_placed(order)

class OrderService:
  def __init__(self, listeners: list[OrderEventListener]):
    self.listeners = listeners

  def place_order(order):
    ...
    for listener in self.listeners:
      listener.on_order_placed(order)

In tests:
  events = []
  service = OrderService(listeners=[lambda o: events.append(o)])
  service.place_order(order)
  assert events[0].id == order.id
```

---

### Command

Encapsulate a request as an object, allowing parameterisation, queuing, logging, and undoable operations.

**Use when** you need to: parameterise objects with operations, queue or log requests, support undo/redo, or decouple the sender of a request from its receiver.

**Testability**: Commands are plain objects — they are trivially testable. Handlers that execute commands can be tested independently by constructing the command directly.

```
class TransferFundsCommand:
  from_account: str
  to_account:   str
  amount:       Decimal

class TransferFundsHandler:
  def execute(cmd: TransferFundsCommand):
    ...

In tests:
  handler = TransferFundsHandler(fake_repo)
  handler.execute(TransferFundsCommand('A', 'B', 100))
  assert fake_repo.balance('A') == original - 100
```

---

### Template Method

Define the skeleton of an algorithm in a base class, deferring some steps to subclasses.

**Use when** you have an invariant algorithm structure but need to vary individual steps. The base class controls the sequence; subclasses fill in the details.

**Prefer composition (Strategy) over inheritance (Template Method)** when the variation point can be isolated as a dependency. Template Method is appropriate when the steps are tightly bound to the algorithm's structure and separation via injection would be forced.

```
abstract class ReportGenerator:
  generate(data):              ← template method — sequence is fixed
    raw     = self.fetch(data)
    cleaned = self.clean(raw)
    return self.format(cleaned)

  abstract fetch(data)         ← subclass provides these
  abstract clean(data)
  abstract format(data)

CsvReportGenerator  extends ReportGenerator
JsonReportGenerator extends ReportGenerator
```

---

### Chain of Responsibility

Pass a request along a chain of handlers, where each handler decides to process it or pass it on.

**Use when** more than one object may handle a request, and the handler is not known at design time — or when you want to issue a request to one of several handlers without specifying the receiver explicitly.

**Common uses**: middleware pipelines, validation chains, event bubbling.

```
interface RequestHandler:
  handle(request) → response

AuthMiddleware   implements RequestHandler
LoggingMiddleware implements RequestHandler
RateLimiter       implements RequestHandler
ApplicationHandler implements RequestHandler

pipeline = AuthMiddleware(LoggingMiddleware(RateLimiter(ApplicationHandler())))
response = pipeline.handle(request)
```

---

## Patterns to Approach with Caution

| Pattern | Risk |
|---------|------|
| **Singleton** | Global state; test-hostile; use DI instead |
| **Template Method** | Tight inheritance coupling; prefer Strategy |
| **Visitor** | Hard to extend with new types; use polymorphism first |
| **Mediator** | Can become a god object; keep it narrow |

---

## Choosing a Pattern

Patterns are not solutions to invent problems for. Identify the design problem first, then check if a known pattern addresses it:

| Problem | Pattern |
|---------|---------|
| Need to swap an algorithm at runtime | Strategy |
| Need to add behaviour without subclassing | Decorator |
| Need to integrate a foreign interface | Adapter |
| Need to simplify a complex subsystem | Facade |
| Need to notify dependents of a change | Observer |
| Need to encapsulate a request as data | Command |
| Need to create a family of related objects | Abstract Factory |
| Need to build a complex object step by step | Builder |
| Need to control access to an object | Proxy |
| Need to create objects without specifying the exact type | Factory Method |
| Need abstraction and implementation to vary independently | Bridge |
| Need to share state across many fine-grained instances | Flyweight |

---

## Related Documents

- `global/hexagonal-architecture.md` — Adapter is the structural pattern used to implement adapters in hexagonal architecture; ports are the Strategy-style interfaces the core depends on
- `global/solid.md` — OCP is implemented via Strategy and Decorator; DIP is implemented via Adapter and Factory Method
- `global/dry.md` — Builder and Factory Method centralise object-creation knowledge; Abstract Factory ensures families of objects are created consistently from one place
