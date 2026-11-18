"""Job queue (Redis + RQ — see docs/adr/0002-job-queue.md).

Start a worker:  rq worker ingestion research --url $REDIS_URL
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Any, Literal

from redis import Redis
from rq import Queue, Retry

from app.core.config import get_settings

QueueName = Literal["ingestion", "research"]


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def enqueue(
    queue: QueueName, func: Callable[..., Any], *args: Any, job_id: str | None = None
) -> str:
    """Enqueue with retries (NFR-04).

    Pass the DB id as `job_id` so retries and restarts stay idempotent.
    """
    settings = get_settings()
    q = Queue(queue, connection=get_redis())
    job = q.enqueue(
        func,
        *args,
        job_id=job_id,
        retry=Retry(max=settings.job_max_retries, interval=[10, 30]),
        job_timeout=600,
    )
    return job.id
