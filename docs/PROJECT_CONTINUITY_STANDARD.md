# Project Continuity Standard

> Reusable continuity protocol for long-running ChatGPT engineering/projects that may outlive any single chat.

## Goal

A chat must be replaceable without forcing the operator to re-explain the project or re-export old transcripts.

The continuity system preserves two different things:

1. **Slow memory** — why the project exists, product rationale, locked working method, important decisions and retired routes.
2. **Fast memory** — exact current refs, last durable result, in-flight task and next atomic action.

Do not mix these roles into one giant log.

## Required files

Use equivalent names if a project already has established conventions.

### `CONTINUITY_LOG.md` — slow memory

Keep:
- project intent and product goal;
- operator/assistant working contract;
- architectural and methodological decisions;
- important causal history;
- rejected/retired routes and why;
- evidence standards and invariants.

Do **not** append every commit, tool call or transient status.

### `CHAT_HANDOFF.md` — fast memory

Keep:
- checkpoint state;
- active branches/PRs and exact refs/SHAs;
- last verified durable result;
- work currently in flight;
- exact next atomic action/discriminant;
- expected workflow/artifact/evidence;
- whether operator evidence is required;
- recovery instructions if interrupted.

## Two-phase durability protocol

### A. PREPARED — write ahead before substantial work

Before a substantial engineering/analysis block, the first durable project action is to update `CHAT_HANDOFF.md`.

Use PREPARED when losing the current reasoning/work would cause meaningful reconstruction, especially when:
- several repository/tool/workflow actions are likely;
- commits, runs or artifacts may be created;
- analysis may materially change the next discriminant;
- a semantic/product decision may result.

Record only what a replacement chat would need to continue.

Do not checkpoint trivial reads, tiny edits or normal conversation.

### B. STABLE — commit result after a meaningful milestone

After the real result is durably persisted:
1. record actual refs/runs/artifacts;
2. record what the evidence changed;
3. record the new exact next atomic action;
4. set the handoff to STABLE when nothing remains in flight;
5. update the slow continuity log only if causal history/methodology/product direction changed.

## Recovery algorithm

When a chat ends unexpectedly:

1. read the project's canonical resume order;
2. read slow memory before fast memory;
3. compare the refs recorded in the handoff with the actual repository/project state;
4. inspect only the delta created after the checkpoint;
5. if refs did not move, execute the recorded next atomic action;
6. if refs moved, reconstruct completed work from commits/runs/artifacts and continue from there;
7. do not restart completed analysis merely because the prior conversational explanation disappeared;
8. consult old chat transcripts only if canonical project evidence contains an unresolved contradiction.

## Default resume order

For repository-backed engineering projects:

```text
README / project identity
-> CANONICAL_STATE
-> CONTINUITY_LOG
-> CHAT_HANDOFF
-> active PR/branch/issues
-> only the detailed worklogs needed by the current gate
```

For projects without GitHub, use the same pattern with the project's most durable available store.

## Interaction rule

Continuity exists to preserve the working rhythm, not to replace it with ceremony.

The assistant should:
- act autonomously within the granted scope;
- advance when the operator says “continue” instead of asking unnecessary micro-confirmations;
- do repeatable engineering/analysis without turning the chat into a running tool log;
- ask the operator mainly for evidence or decisions that only the operator can provide;
- keep product usefulness ahead of process overhead.

## Bootstrap TODO for new projects

When a new project becomes substantial/long-running:

- [ ] establish a canonical durable store;
- [ ] create slow continuity memory;
- [ ] create fast handoff/checkpoint;
- [ ] define authority/resume order;
- [ ] write the project-specific interaction contract;
- [ ] use PREPARED before the first substantial block;
- [ ] use STABLE after the first meaningful durable result.

This is the default continuity pattern unless a project's needs clearly justify a different mechanism.
