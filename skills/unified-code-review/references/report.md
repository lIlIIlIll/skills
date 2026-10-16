# Output contract

## Header / scope

- Mode; repository/commit/base ref; scanned paths; excludes; generated/vendor handling; whether source was modified (default: no).
- Tools actually run, versions and commands. Missing tools, compiler failures and uninspected code.
- Audit coverage: files/functions counted and files/functions deeply inspected. Never claim "entire repository checked" without an enumeration.

## Executive summary

Report only factual totals:

`confirmed bugs: N (P0/P1/P2/P3) | maintainability: N | metrics hotspots: N | unverified leads: N`

If numbers are unknown because the review was sampled, state `not assessed`, not `0`.

## A. Confirmed defects (risk descending)

```
ID: R-001  |  P1  |  Correctness  |  confidence: high
Location: src/example.cj:31-42
Trigger: exact input/environment preconditions
Evidence: minimal failing test OR control/data-flow proof; source/command/result
Impact: observable wrong output / leak / crash / contract regression
Fix: smallest viable code change, without masking the failure
Verification: reproduced / static-proof / corroborated
```

## B. Style / Maintainability

```
ID: S-001  |  STYLE  |  confidence: high
Location, evidence, established rule or concrete maintenance burden
Smallest simplification; rejected alternatives; compatibility/test implications
```

## C. Metrics (not automatically defects)

| Metric | Source / precision | Current | Baseline | Delta | Scope / coverage |
| --- | --- | ---: | ---: | ---: | --- |
| ... | ... | ... | ... | ... | ... |

For top hotspots include function location and **why the source seems difficult**, not just a numeric threshold. Confirm exact same tool/version/settings for baseline comparisons.

## D. Architecture and testing

Dependency direction/cycle observations; evidence; realistic consequence; tests executed and failures (including unrun tests).

## E. Unverified leads and limitations

Separate plausible issues from confirmed findings. State blockers, unsupported language syntax, inaccessible code and missing toolchains explicitly.

## Suggested remediation order

Order by *impact x likelihood x confidence*, then fix cost and dependency sequencing. Prefer focused minimal fixes and regression tests. Do not merge style cleanups into correctness fixes without reason; do not silently modify any files in review mode.
