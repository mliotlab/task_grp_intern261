# ADR-0001: Record architecture decisions

**Status:** Accepted · **Date:** 18/11/2026 · **Deciders:** team, mentor

## Context

The requirement specification asks that every important technical decision (framework, database,
model, deployment) is written down and reviewed by the mentor. Decisions made in chat get lost and
new members cannot see why the system looks the way it does.

## Options considered

1. **No formal record** – fast, but decisions are forgotten and re-debated.
2. **Architecture Decision Records** (Michael Nygard format) in `docs/adr/` – lightweight Markdown,
   reviewed through normal PRs, history kept by Git.

## Decision

Use ADRs in `docs/adr/NNNN-<title>.md` based on [`/docs/templates/ADR.md`](../../../docs/templates/ADR.md).
An ADR is merged only after mentor approval. Accepted ADRs are never edited; they are superseded.

## Consequences

- Every PR that introduces a key technology must link an ADR.
- Slight overhead (~20 minutes per decision) in exchange for a clear decision log for reviews and demos.
