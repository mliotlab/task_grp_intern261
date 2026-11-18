"""Research worker entry point (FR-03, FR-04)."""

from __future__ import annotations

from app.core.logging import job_id_var


def run_research(job_id: str) -> None:
    """Executed by `rq worker research`.

    TODO(FR-03..05, NFR-04):
      - load ResearchJob; skip if already succeeded/cancelled (idempotent);
      - status = running, attempts += 1;
      - run_pipeline(state, on_progress=<persist step into job.steps + commit>);
      - save report + citations, status = succeeded; on error status = failed and re-raise.
    """
    job_id_var.set(job_id)
    raise NotImplementedError("Research worker is not implemented yet (FR-03)")
