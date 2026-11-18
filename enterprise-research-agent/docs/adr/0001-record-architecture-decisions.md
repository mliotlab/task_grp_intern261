# ADR-0001: Record architecture decisions

**Status:** Accepted · **Date:** 18/11/2026 · **Deciders:** team, mentor

## Context

The specification requires every important technical decision (framework, database, model,
deployment) to be documented and reviewed by the mentor.

## Options considered

1. **No formal record** – fast, but decisions get lost and are re-debated.
2. **Architecture Decision Records** in `docs/adr/` – short Markdown files reviewed through PRs.

## Decision

Use ADRs based on [`/docs/templates/ADR.md`](../../../docs/templates/ADR.md). An ADR is merged only
after mentor approval; accepted ADRs are superseded, never edited.

## Consequences

Every PR that introduces a key technology links an ADR. Small overhead, clear decision history.
