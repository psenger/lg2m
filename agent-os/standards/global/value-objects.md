# Value Objects

A Value Object is an object whose identity is defined entirely by its value, not by a reference or database ID. Two value objects with the same data are interchangeable. They are always immutable. They eliminate Primitive Obsession — the code smell of using raw strings, integers, and floats to represent domain concepts.

---

## What Is a Value Object

### Rules

- A Value Object has no identity beyond its value. Two Money objects of £10.00 GBP are equal; it does not matter which one you use.
- Value Objects are always immutable. Operations that would "change" a Value Object return a new instance.
- Value Objects encapsulate validation. An Email object cannot represent an invalid email — the constructor enforces the invariant.
- Value Objects carry domain semantics. `Money(10.00, 'GBP')` communicates more than `float 10.0`.
- Value Objects should define equality based on their contents, not their reference.

### Example

```
WITHOUT value objects — Primitive Obsession:
  function transfer(fromAccount, toAccount, amount: float, currency: string)

  transfer(account1, account2, 100.0, 'GBP')   ← nothing prevents:
  transfer(account1, account2, 'GBP', 100.0)   ← swapped params, compiles, wrong
  transfer(account1, account2, -50.0, 'GBP')   ← negative amount, no validation

WITH value objects:
  function transfer(fromAccount, toAccount, amount: Money)

  money = Money(100.0, Currency.GBP)            ← validated at construction
  transfer(account1, account2, money)           ← param order enforced by type
```

---

## When to Introduce a Value Object

### Rules

- When a primitive has validation rules (email format, positive amounts, non-empty names).
- When a primitive carries units or constraints that must be enforced everywhere it is used.
- When the same primitive appears together with another in multiple places (street + city + postcode → Address).
- When code is littered with validation of the same raw primitive in multiple locations.
- When a function takes two or more primitives of the same type that could be accidentally swapped.

### Primitive Obsession Signals

```
SIGNALS — consider a Value Object:
  function setAge(age: int)                             ← can pass negative or 200
  function createUser(email: string)                    ← can pass any string
  function charge(amount: float, currency: string)      ← units and currency coupled
  if len(name) > 0 and '@' in email and ...            ← validation duplicated across codebase
```

---

## Value Object vs Entity

- **Entity**: has an identity independent of its values. Two Users with the same name are not the same User — they have different IDs. Entities are mutable over time.
- **Value Object**: has no identity beyond its value. Two Money(10, GBP) instances are interchangeable. Value Objects are immutable.

```
Entity:   User(id=1, name='Alice')  ≠  User(id=2, name='Alice')   ← different identity
Value:    Money(10, GBP)            =  Money(10, GBP)              ← same value, interchangeable
```

---

## Immutability and Operations

### Rules

- Operations on a Value Object return a new instance — never mutate the original.
- This makes Value Objects safe to share, cache, and use as dictionary keys.

### Example

```
money = Money(100, 'GBP')
discounted = money.subtract(Money(10, 'GBP'))   ← returns new Money(90, 'GBP')
# money is still Money(100, 'GBP')
```

---

## Related Documents

- `global/dry.md` — Value Objects eliminate duplicated validation logic (single authoritative representation of the constraint)
- `global/solid.md` — SRP: each Value Object is responsible for the validity and behaviour of one domain concept
- `global/gang-of-four.md` — Flyweight: immutable Value Objects are natural candidates for flyweight sharing
