# Architecture assessment

Review architecture when it is requested or a change crosses meaningful module/API boundaries. Do not use an architectural preference as a proxy for a demonstrated defect.

## Method

1. Inventory modules/packages and public interfaces. Set system boundary: application code, tests, generated files, optional dependencies and the SDK. If the inventory is sampled, say so.
2. Extract an actual import/build/runtime dependency graph where possible. Distinguish static source imports from runtime dynamic loading, FFI, reflective edges and generated macro dependencies. Annotate unknown edges.
3. Look for dependency cycles, reversed layering, unnecessary cross-boundary access, broad APIs that leak implementation concerns and multiple sources of truth for one invariant.
4. Determine whether the design makes at least one *real* use case more brittle: trace a concrete feature change or error propagation path to affected modules/tests.
5. For coupling/cohesion, record exact definitions and denominator (e.g. count of outgoing static import edges, number of modules reachable), rather than vague "high coupling" labels. LCOM is only valid when method/field relationships are reliably parsed.
6. Verify any suggestion against local language/runtime requirements, backward compatibility and stability contracts. Sometimes a cycle at the source level is fine due to compile-time modularization; sometimes a dynamic FFI boundary is architectural by design.

## Report

For each actionable observation, provide: affected modules, dependency edges or call path, evidence/commands used, impact on a current workflow, possible lowest-cost change, migration/compatibility cost, and whether any measurement is heuristic.

Do not recommend a large interface hierarchy, service registry or layering rewrite merely to make an abstract diagram cleaner.
