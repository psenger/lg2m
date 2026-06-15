# Object Interaction

These two principles govern how objects should talk to each other. Violations produce code that is tightly coupled to the internal structure of collaborators — fragile, hard to test, and hard to change.

---

## Law of Demeter (Principle of Least Knowledge)

A method should only call methods on: (1) itself, (2) objects passed as parameters, (3) objects it creates, (4) its direct component objects (fields). It should not reach through an object to call methods on a returned object.

### Rules

- A method may call methods on `this`, its parameters, objects it creates locally, and its direct field dependencies.
- A method must not call a method on an object returned by another method call (the "train wreck" smell: `a.getB().getC().doSomething()`).
- Each "dot" after the first in a chain is a potential Demeter violation — the caller now depends on the internal structure of the object it received.
- When you find yourself navigating a chain to do something, ask: should the intermediate object offer a method that does this for me?
- Demeter violations make mocking painful: to test code that calls `order.getCustomer().getAddress().getCity()`, you must mock three layers.

### Example

```
WRONG — violates Demeter, couples to internal structure:
  city = order.getCustomer().getAddress().getCity()
  discount = order.getCart().getPricingEngine().calculateDiscount(order)

RIGHT — ask the object for what you need:
  city = order.getShippingCity()         ← Order knows its shipping city
  discount = order.calculateDiscount()   ← Order delegates to PricingEngine internally
```

### When to Accept a Chain

Fluent interfaces and builder patterns are intentional chains where each method returns the same object type (`query.where().orderBy().limit()`). These are not Demeter violations — the chain does not navigate to a foreign object type.

---

## Tell, Don't Ask

Tell an object what to do rather than asking it for its state and making decisions on its behalf outside the object.

### Rules

- If you find yourself reading an object's state, making a decision, then calling a method on the object based on that decision — move the decision into the object.
- Objects should encapsulate both their state and the behaviour that operates on that state.
- Asking for state to make a decision outside the object creates coupling: the caller now depends on the object's state representation.
- The question "should this object be responsible for this decision?" almost always answers itself: if the decision uses only this object's data, yes.

### Example

```
WRONG — Ask (caller interrogates state and decides):
  if order.getStatus() == 'pending' and order.getPaymentStatus() == 'paid':
    order.setStatus('confirmed')
    order.sendConfirmation()

RIGHT — Tell (caller delegates the decision):
  order.confirm()   ← Order knows its own rules; caller just tells it what to do
```

---

## How These Principles Relate to Testability

Both principles reduce the number of objects a test must understand and mock:

- Demeter: a method that only calls on direct collaborators needs only those collaborators mocked — not their internals.
- Tell Don't Ask: a method that delegates decisions to objects has fewer branches to test — the decision logic is tested where it lives.

```
DEMETER VIOLATION — test must set up three levels of mocks:
  mock_customer = Mock()
  mock_address = Mock()
  mock_order = Mock()
  mock_order.getCustomer.return_value = mock_customer
  mock_customer.getAddress.return_value = mock_address
  mock_address.getCity.return_value = 'London'

DEMETER COMPLIANT — test mocks one level:
  mock_order = Mock()
  mock_order.getShippingCity.return_value = 'London'
```

---

## Related Documents

- `global/solid.md` — SRP (each object is responsible for its own behaviour); DIP (depend on interfaces not structure)
- `global/hexagonal-architecture.md` — ports enforce clean interaction boundaries; Demeter is naturally satisfied when talking to a port
- `global/dry.md` — Ask-style code duplicates decision logic across callers; Tell centralises it
