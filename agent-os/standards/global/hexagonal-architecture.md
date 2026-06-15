# Hexagonal Architecture and Orthogonal Design

These two principles are the architectural foundation behind the "mock at system boundaries only" rule. Understanding them explains *why* the testing and mocking standards are written the way they are — not just *what* to do.

---

## Orthogonal Design

**Orthogonality** means that a change to one component does not force a change to another. Two components are orthogonal when they are independent: you can modify, replace, or test either one without touching the other.

### Rules

- Separate concerns so that each module has one reason to change.
- A component should not need to know how another component is implemented — only what it does.
- Dependencies should flow in one direction. Circular dependencies are a sign of non-orthogonal design.
- Design so that swapping an implementation (e.g. switching from one database to another) requires no changes to any component that did not directly depend on it.

### Why It Matters for Testing

When components are orthogonal, you can test each one in isolation. A test for business logic should not break because the database schema changed. A test for an HTTP adapter should not break because domain rules changed. Orthogonal design is what makes this possible.

```
NON-ORTHOGONAL — business logic depends on Stripe directly:
  OrderService → StripeGateway
  Changing payment provider requires rewriting OrderService tests.

ORTHOGONAL — business logic depends on an interface:
  OrderService → PaymentGateway (interface)
                     ↑
               StripeAdapter  BraintreeAdapter
  Changing payment provider does not touch OrderService or its tests.
```

---

## Hexagonal Architecture (Ports and Adapters)

Hexagonal Architecture, defined by Alistair Cockburn, organises an application into three zones:

```
┌─────────────────────────────────────────────┐
│              DRIVING ADAPTERS               │  ← Tests, HTTP controllers, CLI, message consumers
│         (primary — drive the app)           │
├─────────────────────────────────────────────┤
│                                             │
│             APPLICATION CORE               │  ← Domain logic, use cases, business rules
│          (no I/O, no frameworks)            │
│                                             │
├─────────────────────────────────────────────┤
│              DRIVEN ADAPTERS                │  ← Database, email, external APIs, message queues
│       (secondary — driven by the app)       │
└─────────────────────────────────────────────┘
```

### Ports

A **port** is an interface defined by the application core. It describes what the application *needs* — not how it is provided.

- **Driving ports** (primary): interfaces through which external actors interact with the core (e.g. `OrderService`, `UserService`).
- **Driven ports** (secondary): interfaces the core calls outward (e.g. `PaymentGateway`, `UserRepository`, `EmailSender`).

Ports belong to the core. They are defined in terms of the domain, not in terms of any specific technology.

### Adapters

An **adapter** is a concrete implementation of a port. It translates between the application's domain language and an external system.

- A `StripeAdapter` implements `PaymentGateway`.
- A `PostgresUserRepository` implements `UserRepository`.
- An `HttpController` implements the driving port by calling `OrderService`.

Adapters belong outside the core. They depend on the core; the core does not depend on them.

### Rules

- The application core must not import or reference any adapter, framework, or I/O library.
- All I/O crosses the boundary through a port interface.
- Adapters are the only place where third-party libraries (ORMs, HTTP clients, SDKs) appear.
- Driven ports are what you inject into use cases and services — not concrete adapters.
- Wrap any third-party library you do not own in an adapter. Never let a third-party type leak into the core.

### Example

```
WRONG — core depends on a concrete adapter:
  class OrderService:
    def __init__(self):
      self.payment = StripeGateway()   ← adapter imported into core

CORRECT — core depends on a port:
  class OrderService:
    def __init__(self, payment: PaymentGateway):   ← port, not adapter
      self.payment = payment

In production:   OrderService(payment=StripeAdapter())
In tests:        OrderService(payment=FakePaymentGateway())
```

---

## How These Principles Drive the Mocking Rules

The "mock at system boundaries only" rule is a direct consequence of hexagonal architecture:

| Rule | Why |
|------|-----|
| Mock driven ports (external APIs, databases, etc.) | They are the outward boundary. Tests should verify the core behaves correctly given what the port returns. |
| Do not mock your own classes or internal collaborators | Those are inside the core. Mocking them means testing structure, not behaviour. |
| Mock interfaces (ports), not concrete implementations (adapters) | Tests should depend on the contract, not the wiring. |
| Wrap third-party libraries in an adapter; mock the adapter | You do not own the third-party interface — it can change. Your adapter is the stable contract. |
| Prefer dependency injection over internal construction | Ports must be injectable to be replaceable. |

Orthogonality enforces this further: if your tests are hard to write without mocking internal collaborators, it means two concerns are entangled and need to be separated — the design is not orthogonal.

```
SIGNAL: "I need to mock UserService to test OrderService"
CAUSE:  OrderService depends on UserService directly — they are not orthogonal
FIX:    Introduce a port that represents only what OrderService needs from user data,
        and depend on that interface instead
```

---

## Summary

- **Orthogonal design**: components change independently. Enables isolated testing.
- **Hexagonal architecture**: core logic is surrounded by ports (interfaces) and adapters (implementations). The core has no knowledge of external systems.
- **Consequence for mocking**: mock at ports (the boundary between core and adapters). Everything inside the core is tested directly; everything outside is replaced with a fake or stub.
- **Consequence for design**: if mocking feels painful, the boundary is in the wrong place — fix the design, not the test.

---

## Related Documents

- `global/solid.md` — the Dependency Inversion Principle (D) is the SOLID expression of hexagonal architecture; Interface Segregation (I) explains why ports should be narrow
- `global/gang-of-four.md` — the Adapter pattern is how adapters are implemented; Strategy explains why the core can swap adapters at runtime
- `global/dry.md` — keeping a single authoritative port definition prevents knowledge duplication across adapters
