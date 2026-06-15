# Progressive Enhancement and Graceful Degradation

Progressive Enhancement is a design philosophy: build a core that works under minimal conditions, then layer on enhancements that activate only when the required capabilities are available. Graceful Degradation is the consequence: when a capability is absent or fails, the system continues functioning in a reduced but acceptable form, rather than failing entirely.

These two ideas are two sides of the same coin. Progressive enhancement is how you design a system from the start; graceful degradation is what you observe at runtime when optional dependencies are unavailable.

---

## Core Principle

A system built with progressive enhancement satisfies two constraints at every level:

1. **The core path always works.** The essential behaviour does not depend on any optional capability. Remove any enhancement, and the core still functions correctly.
2. **Enhancements activate conditionally.** Before using an optional capability, the system checks whether it is available. If it is not, the system falls back to the core path.

---

## Rules

- **Core behaviour must not depend on optional capabilities.** Design the core path first. Optional enhancements activate only after a successful availability check. If removing a feature flag or an external service would break the core, the dependency is not truly optional.
- **Design every external dependency as optional where possible.** Before wiring a dependency into the core path, ask: what happens if this is slow? What happens if it is unavailable? What happens if it returns an error? The answer to each question should be a defined fallback, not an uncaught exception.
- **Return partial results with a signal rather than failing entirely when non-critical components fail.** If a response depends on three backends and one times out, return the results from the two that succeeded along with a `warnings` field indicating what is missing. Never silently hide the degradation — callers need to know the response is partial.
- **Use capability detection, not assumption.** Check whether a service or feature is available before using it. Do not assume that because a service was reachable at startup it will be reachable at request time.
- **Circuit breakers and fallbacks are the infrastructure expression of this principle.** A circuit breaker detects that a downstream service is failing and routes traffic to a fallback instead of continuing to call the failing service. This is progressive enhancement applied at the infrastructure level.
- **Never let a non-critical system failure become a critical one.** An analytics service going down must not prevent a checkout from completing. A recommendations engine returning an error must not prevent a product page from loading. Non-critical paths must be isolated from critical paths.

---

## Examples

### Search with Elasticsearch fallback

```
function search(query):
  if elasticsearch.isAvailable():
    try:
      return elasticsearch.search(query)
    except ElasticsearchTimeout:
      log.warning('Elasticsearch unavailable, falling back to database search')

  # Core path — always works
  return database.fullTextSearch(query)
```

The Elasticsearch integration is an enhancement. The core path (database full-text search) always works. The enhancement activates only after a successful availability check and falls back on error.

### Recommendations engine returning a safe default

```
function getRecommendations(userId):
  try:
    return recommendationsService.forUser(userId, timeout=500ms)
  except (ServiceUnavailable, Timeout):
    log.warning('Recommendations service unavailable, returning empty list')
    return []   ← safe default — page still renders

# The calling page never receives an error.
# It receives an empty list, which it handles gracefully.
```

### API response with partial data and warnings

```
function getDashboard(userId):
  results = {}
  warnings = []

  results['profile'] = profileService.get(userId)          ← required, no fallback

  try:
    results['orders'] = orderService.recent(userId)
  except Timeout:
    warnings.append('Recent orders could not be loaded')

  try:
    results['recommendations'] = recommendationsService.get(userId)
  except ServiceUnavailable:
    results['recommendations'] = []
    warnings.append('Recommendations are temporarily unavailable')

  return { data: results, warnings: warnings }
```

The caller receives whatever data is available, plus a transparent account of what is missing.

### Feature flags — progressive activation

```
function processPayment(order):
  if featureFlags.isEnabled('new-payment-flow', order.userId):
    return newPaymentProcessor.charge(order)     ← enhancement: new flow
  return legacyPaymentProcessor.charge(order)    ← core: existing flow always works

# The new payment flow is an enhancement.
# It activates only for users in the feature flag cohort.
# The existing flow is unchanged and always reachable.
```

---

## Relationship to Circuit Breaker

The circuit breaker is the implementation pattern; progressive enhancement is the design philosophy.

A circuit breaker detects repeated failures from a downstream service and opens the circuit — subsequent calls are immediately routed to the fallback without attempting the service call, giving the service time to recover. The fallback is the progressive-enhancement core path.

Without a defined fallback (i.e., without designing the system progressively), a circuit breaker has nowhere to route traffic — it can only fail fast. The circuit breaker is only useful when there is a degraded-but-functional path to fall back to.

---

## Related Documents

- `global/hexagonal-architecture.md` — external dependencies enter through ports; designing a port's fallback behaviour is where progressive enhancement is expressed in hexagonal architecture
- `global/solid.md` — the Open/Closed Principle (OCP) is related: adding a new capability (an enhancement) should not require modifying the core path; the core remains closed to modification while new enhancements are added by extension
- `global/gang-of-four.md` — the Proxy pattern can implement fallback logic: a proxy attempts the real implementation and falls back to a safe alternative when the real implementation fails
