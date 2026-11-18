# ADR-0002: Job queue for ingestion and research

**Status:** Proposed — team to confirm in Sprint 1 · **Date:** 18/11/2026 · **Deciders:** team, mentor

## Context

Document ingestion and research jobs take seconds to minutes (NFR-03) and must not block the API.
Failed jobs are retried up to 2 times and a worker restart must not lose jobs (NFR-04).
The team has 4 weeks and mixed experience with async Python.

## Options considered

### Option A – Redis + RQ

- ✅ Very small API, synchronous functions, easy to debug; built-in `Retry`; `rq-dashboard` available.
- ❌ No native async; fewer features than Celery (no canvas/chords).

### Option B – Redis + Celery

- ✅ Industry standard, rich features (routing, rate limits, chords), Flower monitoring.
- ❌ Heavier configuration and more concepts to learn in a 4-week project.

### Option C – Redis + arq

- ✅ Native asyncio, lightweight, retries.
- ❌ Smaller community; async everywhere raises the bar for the team.

## Decision

**Option A (RQ)** as the scaffold default. Job state of record is kept in PostgreSQL
(`documents.status`, `research_jobs.status/steps`), Redis runs with AOF persistence, and jobs are
enqueued with the DB id as the RQ job id so retries and re-enqueues are idempotent.

## Consequences

- Workers run `rq worker ingestion research`; job functions take only ids, never large payloads.
- A startup "reaper" should re-enqueue jobs stuck in `running` after a crash (Sprint 3).
- Revisit (supersede this ADR) if we need streaming progress from async LLM calls.
