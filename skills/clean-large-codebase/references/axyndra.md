# Axyndra adaptation

Use this reference only when auditing or refactoring Axyndra. Verify every name and command against the current checkout; the repository may have evolved.

## Discover current boundaries first

- Read all applicable `AGENTS.md` files, root and package `cjpm.toml` files, and current architecture documents.
- Map the Cangjie packages and any native C/C++ boundaries before proposing moves.
- Discover supported build and test commands from the repository rather than assuming the SDK or optional tools are installed.

## Preserve runtime invariants

Treat these as high-risk review areas:

- one authoritative `AgentCore` execution loop rather than parallel orchestration paths;
- `ThreadCoordinator` state ownership and thread/run lifecycle transitions;
- tool discovery, validation, authorization, execution, receipt, and observation ordering in `ToolPipeline` or its current equivalent;
- stable attempt, decision, block, and scoped tool-call identities;
- atomic persistence of decisions, blocks, operations, receipts, and checkpoints where the current schema requires it;
- deterministic resume/recovery behavior and no duplicate side effects;
- streaming event order, cancellation propagation, approval boundaries, and shutdown cleanup.

Do not extract code in a way that creates a second state owner, persistence channel, authorization path, or execution loop. Moving types across Cangjie packages also changes visibility and dependency direction; account for that explicitly.

## Verification priorities

Before a structural change, prefer tests around state transitions, persistence/recovery, approval denial, cancellation, tool failure, retry/idempotency, and event ordering. If the relevant Cangjie SDK is unavailable, state exactly which checks could not run and do not mark the refactor verified.

The bundled line-count tools understand `.cj` as source text but do not understand Cangjie syntax. Use compiler/LSP information or complete manual reading for function and type boundaries.
