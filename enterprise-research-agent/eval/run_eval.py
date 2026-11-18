"""Report-quality evaluation (NFR-01, NFR-02, NFR-03).

    python eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000

`<dataset>/questions.jsonl`, one object per line:
    {"id": "q01", "question": "...", "key_points": ["...", "..."], "source_documents": ["file.pdf"]}

For each question the harness submits a research job, polls until it finishes, then scores:
  - coverage  : share of key_points covered by the report (LLM-as-judge)   → target ≥ 70 %
  - latency   : end-to-end job duration                                    → p95 ≤ 3 min
and samples citations into a CSV for the manual citation-accuracy check (NFR-01, ≥ 50 citations).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_questions(dataset: Path) -> list[dict]:
    lines = (dataset / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--dataset", type=Path, default=Path("eval/datasets/v0"))
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--email", default="eval@example.com")
    parser.add_argument("--out", type=Path, default=Path("eval/reports"))
    args = parser.parse_args()

    questions = load_questions(args.dataset)
    print(f"Loaded {len(questions)} questions from {args.dataset}")
    # TODO(Sprint 3):
    #  1. log in as the eval user, make sure the eval collection is ingested;
    #  2. POST /v1/research for each question, poll GET /v1/research/{id};
    #  3. judge key-point coverage with the LLM (store judge prompt + version in eval/judge/);
    #  4. write eval/reports/eval_<timestamp>.md + citations_sample.csv for manual review.
    raise SystemExit("Evaluation harness not implemented yet (see TODOs).")


if __name__ == "__main__":
    main()
