# ADR-0008: Use Redis and RQ for Asynchronous Job Processing

- **Status:** Proposed — selected by the ERA team; pending team and mentor review
- **Date:** 2026-11-28
- **Parent:** ERA-19 — Discovery & Design
- **Task:** S2-08 — Queue & Vector Store ADRs
- **Requirements:** FR-02, FR-05, NFR-04, NFR-08
- **Deciders:** Enterprise Research Agent (ERA) team

## 1. Context

The Enterprise Research Agent (ERA) must perform work that can take longer than a normal HTTP request. Under **FR-02**, uploaded PDF, DOCX, and Markdown files (up to 20 MB each) are processed asynchronously: the system extracts text, splits it into chunks, generates embeddings, and indexes the chunks. The system exposes the document lifecycle states `queued`, `processing`, `ready`, and `failed`.

The Research Pipeline in **FR-05** also performs multiple stages: it decomposes a research question, retrieves relevant chunks for each sub-question, and produces a structured Markdown report with citations. These stages should execute in worker processes rather than keeping an API request open for the duration of the work.

The queue must support the reliability expectations in **NFR-04**:

- Retry a failed task no more than two times.
- Do not lose queued work when a worker is restarted.
- Make ingestion idempotent so uploading the same file again does not create a duplicate document-processing result.

The application must also satisfy **NFR-08**: the frontend, API, worker, PostgreSQL (with pgvector), and Redis services must start through Docker Compose, and CI must build the images for all services.

The current ERA architecture already uses Redis as a service in Docker Compose and runs Python workers for the `ingestion` and `research` queues. An example worker command is:

```bash
rq worker ingestion research --url "$REDIS_URL"
```

PostgreSQL remains the system of record for application entities and business lifecycle states. The queue is responsible for scheduling and execution, not for replacing the application's document or research-job records.

### Decision drivers

- Support asynchronous ingestion and research execution outside the API process.
- Meet the retry and worker-restart requirements in NFR-04, subject to explicit configuration and integration testing.
- Fit the existing Python backend and Docker Compose deployment.
- Keep the number of infrastructure services and operational concepts small.
- Allow ingestion and research workloads to be separated and scaled when needed.

## 2. Options Considered

### Option A — Redis + RQ (selected)

Redis provides the shared queue/job-state backend, while RQ provides the Python API for enqueueing functions and running worker processes.

**Advantages**

- RQ is designed for Python jobs and can enqueue ordinary importable Python functions for execution by separate workers.
- Redis is already present in the ERA Docker Compose architecture, so this option does not introduce another infrastructure service.
- Named queues such as `ingestion` and `research` make it possible to separate the two workloads.
- RQ provides job lifecycle registries, failure information, job timeouts, and configurable retry policies.
- Workers can be started independently. Each standard RQ worker processes one job at a time; additional worker processes can provide more concurrency.
- The implementation and operational model are comparatively small for the current project scope.

**Limitations**

- RQ is intentionally simpler than Celery and does not provide the same breadth of distributed-workflow orchestration features.
- RQ is Python-oriented. Its default serializer uses Python pickle, so Redis must be treated as a trusted internal service and must not be exposed to untrusted clients.
- Redis availability and persistence affect queued work. A worker restart and a Redis data-loss event are different failure cases; Redis persistence and backup settings must be considered separately.
- A task can execute again after a retry or recovery action. Task implementations therefore need to respect the idempotency requirement in NFR-04.

### Option B — Redis + Celery

**Advantages**

- Reuses Redis as the broker, avoiding the need to add another broker service.
- Celery supports a broader distributed-task model, including multiple worker pools, task routing, and workflow primitives such as chains, groups, and chords.
- More appropriate if the system later requires complex task graphs or advanced orchestration.

**Limitations**

- Adds more configuration and operational concepts than the current ERA workflows require.
- Requires adopting Celery's task model and conventions even though the current backend already uses RQ.
- Switching from RQ would create migration and testing work without a demonstrated need for the additional capabilities.

### Option C — RabbitMQ + Celery

**Advantages**

- RabbitMQ is a dedicated message broker with exchanges, routing, acknowledgements, and configurable delivery behavior.
- Combined with Celery, it is suitable for more complex distributed messaging and task-processing architectures.

**Limitations**

- Introduces another infrastructure service alongside PostgreSQL and Redis, increasing deployment, monitoring, backup, and configuration work.
- The richer routing and broker capabilities are not currently justified by the scale and workflow complexity of ERA.
- The team would need to operate and test another service in Docker Compose and CI.

### Option D — FastAPI BackgroundTasks (in-process background work)

**Advantages**

- Minimal setup and direct integration with FastAPI endpoints.
- Suitable for short, best-effort work that does not need an independent worker system.

**Limitations**

- Work is tied to the API process lifecycle and does not provide the independent queue/worker boundary required for long-running ingestion and research tasks.
- It does not provide the same persistent queue and job-management model needed to meet NFR-04.
- It is not suitable as the main execution mechanism for ERA's asynchronous workloads.

## 3. Decision

The ERA system will use **Redis as the queue backend and RQ as the Python job-queue library** for asynchronous ingestion and research processing.

1. The API enqueues jobs into named Redis-backed RQ queues:
   - `ingestion` — document parsing, chunking, embedding generation, and indexing.
   - `research` — execution of the research pipeline described in FR-05.
2. RQ workers run as processes/services separate from the API. The current deployment may run a worker listening to both queues. Separate workers can be deployed later to scale ingestion and research independently.
3. Queue arguments should contain stable identifiers and small control parameters, such as `document_id` or `research_job_id`. Large file contents, uploaded binaries, and embedding batches remain in their designated storage/database locations and must not be copied into Redis job arguments.
4. **PostgreSQL remains the source of truth for application state.** Document and research-job status exposed by the API must be read from PostgreSQL. RQ status and registries are operational information about queue execution.
5. Configure bounded RQ retries for transient failures, with **at most two retries after the initial attempt**, in accordance with NFR-04. Permanent input or validation failures should not be retried. Exhausted jobs must be reflected in the corresponding PostgreSQL business state as failed.
6. NFR-04's worker-restart requirement must be verified with integration tests that restart workers while jobs are queued and while jobs are executing. RQ tracks queued and started jobs in Redis registries; this tracking is useful for recovery, but the application must not assume that every abrupt process termination is automatically retried without the required RQ configuration and recovery handling.
7. Redis persistence is a separate operational concern from worker restart handling. For deployments that must also preserve queued work across a Redis process/container restart, configure and test an appropriate Redis persistence and backup policy. AOF with `appendfsync everysec`, together with periodic RDB snapshots, is a reasonable starting profile; the final policy must be validated against the deployment's recovery-point and latency requirements.
8. The worker implementation must satisfy the idempotent-ingestion part of NFR-04. The exact deduplication keys, database constraints, and recovery workflow belong to the ingestion/job-lifecycle design and are not selected by this ADR.
9. Configure Redis through environment-based connection settings such as `REDIS_URL`, keep it on the private application network, and include the Redis and worker services in Docker Compose and CI image builds as required by NFR-08.

## 4. Consequences

### Positive

- Long-running document ingestion and research work no longer needs to execute inside API request handling.
- The team reuses the existing Redis service and Python worker architecture.
- Separate queue names provide a clear boundary between ingestion and research workloads.
- Worker processes can be increased or separated without changing the API architecture.
- PostgreSQL remains authoritative for business state, while RQ manages execution state.

### Negative / risks

- Redis becomes an operational dependency for dispatching new work. Enqueue failures must be surfaced and handled rather than silently ignored.
- Worker restarts, abrupt worker termination, and Redis data loss are distinct failure modes and require separate verification.
- Redis persistence introduces disk usage, backup, and recovery responsibilities. A named Docker volume alone is not an independent backup.
- RQ has fewer built-in orchestration capabilities than Celery; more complex workflows may eventually justify reassessment.
- Retries can repeat side effects. Ingestion and research task implementations must be safe against repeated execution to satisfy NFR-04.
- RQ's default pickle serializer requires Redis to be trusted and isolated from untrusted network access. A JSON serializer may be considered where job arguments are JSON-compatible.

### Operational responsibilities

- Set explicit job timeouts and a maximum of two retries for transient failures.
- Monitor queue depth, started/failed job registries, worker heartbeats, and task duration.
- Use graceful worker shutdown during routine deployments and test forced worker termination separately.
- Configure Redis authentication/network isolation and persistence appropriate to the deployment.
- Include worker-restart and retry scenarios in integration tests; verify that the PostgreSQL document/research state matches the final job outcome.

## 5. Revisit This Decision When

Reconsider RQ if ERA requires complex task graphs, cross-service workflows, advanced broker-level routing, non-Python consumers, substantially higher throughput, or stronger broker-level delivery guarantees. At that point, compare Celery with Redis or RabbitMQ and managed queue services using measured workload requirements.

## 6. References

1. [RQ documentation — Overview](https://python-rq.org/docs/) — enqueueing jobs, job IDs, queue behavior, and serializer considerations.
2. [RQ documentation — Workers](https://python-rq.org/docs/workers/) — worker lifecycle, worker execution, and graceful shutdown.
3. [RQ documentation — Jobs](https://python-rq.org/docs/jobs/) — job lifecycle and job states.
4. [RQ documentation — Exceptions & Retries](https://python-rq.org/docs/exceptions/) — retry configuration and failed-job handling.
5. [Redis documentation — Persistence](https://redis.io/docs/latest/management/persistence/) — RDB snapshots, AOF, and persistence trade-offs.
6. [Celery documentation — Introduction](https://docs.celeryq.dev/en/stable/getting-started/introduction.html) — task queues, workers, brokers, and workflow capabilities.
