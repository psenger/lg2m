# DRY — Don't Repeat Yourself

> "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."
> — The Pragmatic Programmer, Hunt & Thomas

DRY is about knowledge, not text. Two pieces of code that look similar are not necessarily a DRY violation. Two pieces of code that encode the *same rule or decision* are — because when that rule changes, both must change, and one will be missed.

---

## The Core Principle

### Rules

- Identify the underlying knowledge or decision being expressed, not just the surface-level syntax.
- If the same business rule, algorithm, or constraint exists in two places, one of them will eventually fall out of sync.
- The authoritative representation should be the only place that knows the rule — all other places derive from it.
- Duplication of structure (similar-looking code) is often fine. Duplication of knowledge (the same decision encoded twice) is what causes bugs.

### Example

```
DUPLICATION OF KNOWLEDGE — the VAT rate is encoded in three places:
  calculatePrice(net):     return net * 1.20
  formatReceipt(net):      vat = net * 0.20
  validateInvoice(gross):  if gross != net * 1.20: raise Error

When VAT changes, all three must be updated. One will be missed.

SINGLE AUTHORITATIVE SOURCE:
  VAT_RATE = 0.20

  calculatePrice(net):     return net * (1 + VAT_RATE)
  formatReceipt(net):      vat = net * VAT_RATE
  validateInvoice(gross):  if gross != net * (1 + VAT_RATE): raise Error
```

---

## What DRY Is Not

DRY is frequently misapplied as "never write similar-looking code twice." This produces premature abstractions that are harder to understand and change than the duplication they replaced.

### Rules

- Do not abstract two pieces of code just because they look the same today. Ask: do they represent the same knowledge, or do they merely look similar?
- Accidental similarity is not duplication. Two modules that happen to use the same formula for different business reasons should stay separate — they will diverge.
- The **Rule of Three**: tolerate one instance of duplication. Abstract at the second repetition only if the knowledge is genuinely shared.
- Premature abstraction is more expensive than duplication. A bad abstraction is harder to remove than duplicated code.

### Example

```
ACCIDENTAL SIMILARITY — do not abstract:
  calculateShippingCost(weight):  return weight * 2.5
  calculateTaxAmount(value):      return value * 2.5

These look identical but represent unrelated rules. They will diverge.
Abstracting them creates a meaningless coupling.

GENUINE DUPLICATION — abstract:
  function discountForGold(price):   return price * 0.10
  function discountForSilver(price): return price * 0.10

Same rule, same knowledge. Extract to discountForLoyaltyTier(price, rate).
```

---

## AHA — Avoid Hasty Abstractions

Coined by Kent C. Dodds as a complement to DRY. Prefer duplication over the wrong abstraction.

### Rules

- Write the code inline first. Abstract only when the pattern is clear and the abstraction has a name that carries meaning.
- If you cannot name the abstraction without using "util", "helper", "manager", or "and", it is not ready to be extracted.
- A wrong abstraction forces all future callers to work around it with special cases, flags, and conditional parameters — this is worse than duplication.
- Inline the wrong abstraction and start again when you understand the pattern.

### Example

```
WRONG — abstraction with a flag to handle two different cases:
  function renderButton(label, isPrimary, hasIcon, iconPosition, ...):
    ...  ← grows a new parameter for every caller's special case

RIGHT — two clear, separate components until the real pattern emerges:
  renderPrimaryButton(label)
  renderIconButton(label, icon)

  Abstract later if a genuine shared structure becomes clear.
```

---

## DRY in Tests

Test code has different duplication trade-offs from production code.

### Rules

- Duplication in test *setup* is worth abstracting into fixtures or factories — it reduces the cost of changing the interface under test.
- Duplication in test *assertions* is often intentional — each test should be independently readable without needing to trace through shared helpers.
- Do not abstract test assertions into shared helpers. If a test fails, the failure should be understandable by reading that test alone.
- Test names and descriptions must never be shared or generated — each test must state its own intent.
- Prefer explicit, slightly repetitive test bodies over clever abstractions that obscure what is being tested.

### Example

```
GOOD — extract shared setup, keep assertions explicit:
  user = create_test_user(role='admin')   ← factory, not duplicated construction

  test_admin_can_delete_post:
    result = delete_post(user, post)
    assert result.status == 'deleted'     ← assertion stays local and explicit

  test_admin_can_archive_post:
    result = archive_post(user, post)
    assert result.status == 'archived'    ← assertion stays local and explicit

BAD — shared assertion helper obscures intent:
  def assert_post_action_succeeded(result):
    assert result.status in ('deleted', 'archived')

  test_admin_can_delete_post:
    assert_post_action_succeeded(delete_post(user, post))
    ← failure message is now: "status not in ('deleted', 'archived')"
    ← which post action? what was expected? must read helper to find out
```

---

## DRY and Single Responsibility

These principles reinforce each other. If knowledge is split across multiple modules, it is both a DRY violation and a SRP violation — more than one module now has reason to change when that knowledge changes. The fix is the same: find the single authoritative place where that knowledge should live and make all other places derive from it.

---

## Summary

| Situation | Guidance |
|-----------|----------|
| Same business rule in two places | Extract to a single authoritative source |
| Similar-looking code, different meaning | Leave separate — they will diverge |
| Second occurrence of the same pattern | Consider abstracting |
| Abstraction requires flags or special cases | Inline it and wait for the real pattern |
| Duplicated test setup | Extract to fixtures/factories |
| Duplicated test assertions | Keep explicit — readability matters more |

---

## Related Documents

- `global/solid.md` — SRP and DRY reinforce each other: a single-responsibility module naturally has one authoritative place for each piece of knowledge
- `global/hexagonal-architecture.md` — a single port definition is the authoritative source for a boundary contract; duplicating it across adapters is a DRY violation
- `global/gang-of-four.md` — Factory Method and Builder centralise object-creation knowledge, eliminating construction duplication across callers
