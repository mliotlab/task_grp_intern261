"""Evaluation harness (NFR-01..NFR-06, NFR-08). One command → Markdown + CSV report.

    # against a running API
    python eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000
    # in-process with the mock LLM (CI)
    python eval/run_eval.py --dataset eval/datasets/v0 --in-process --limit 20

Each line of `<dataset>/cases.jsonl` is one test case:
    {"id": "...", "category": "policy|order|ticket|handoff|attack|out_of_scope",
     "turns": ["user message", ...], "expected_answer": "...", "expected_doc_ids": ["..."],
     "expected_tool": "get_order_status" | null, "expected_tool_args": {...} | null,
     "must_handoff": false}
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class CaseResult:
    id: str
    category: str
    answer: str
    latency_ms: float
    citation_hit: bool | None
    tool_match: bool | None
    handoff_match: bool
    judge_correct: bool | None = None  # TODO(NFR-01): LLM-as-judge


def load_cases(dataset: Path, limit: int | None) -> list[dict[str, Any]]:
    lines = (dataset / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    return cases[:limit] if limit else cases


def make_client(api_url: str | None, in_process: bool):
    import httpx

    if in_process:
        from fastapi.testclient import TestClient

        from services.chat_api.main import app

        return TestClient(app)
    return httpx.Client(base_url=api_url, timeout=60)


def run_case(client, case: dict[str, Any]) -> CaseResult:
    session_id = f"eval-{uuid.uuid4().hex[:8]}"
    body: dict[str, Any] = {}
    start = time.perf_counter()
    for turn in case["turns"]:
        body = client.post("/v1/chat", json={"session_id": session_id, "message": turn}).json()
    latency = (time.perf_counter() - start) * 1000 / max(len(case["turns"]), 1)

    cited = {c["doc_id"] for c in body.get("citations", [])}
    expected_docs = set(case.get("expected_doc_ids") or [])
    tools = [a["tool"] for a in body.get("actions", [])]
    expected_tool = case.get("expected_tool")
    return CaseResult(
        id=case["id"],
        category=case.get("category", "policy"),
        answer=body.get("answer", ""),
        latency_ms=round(latency, 1),
        citation_hit=bool(cited & expected_docs) if expected_docs else None,
        # TODO(NFR-03): also compare tool arguments with expected_tool_args.
        tool_match=(expected_tool in tools) if expected_tool else None,
        handoff_match=bool(body.get("handoff")) == bool(case.get("must_handoff")),
    )


def rate(values: list[bool | None]) -> str:
    vals = [v for v in values if v is not None]
    return f"{100 * sum(vals) / len(vals):.1f}% ({sum(vals)}/{len(vals)})" if vals else "n/a"


def write_reports(results: list[CaseResult], out_dir: Path, dataset: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with (out_dir / f"eval_{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)

    latencies = sorted(r.latency_ms for r in results)
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    md = [
        f"# Eval report – {stamp}",
        "",
        f"Dataset: `{dataset}` · Cases: {len(results)}",
        "",
        "| Metric | Value | Target |",
        "|---|---|---|",
        f"| Answer correct (LLM judge) | {rate([r.judge_correct for r in results])} | ≥ 80% |",
        f"| Citation hit | {rate([r.citation_hit for r in results])} | ≥ 90% |",
        f"| Tool match | {rate([r.tool_match for r in results])} | ≥ 90% |",
        f"| Handoff match | {rate([r.handoff_match for r in results])} | recall ≥ 90% |",
        f"| Latency p50 / p95 (ms) | {statistics.median(latencies):.0f} / {p95:.0f} | p95 ≤ 6000 |",
    ]
    report = out_dir / f"eval_{stamp}.md"
    report.write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--dataset", type=Path, default=Path("eval/datasets/v0"))
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument(
        "--in-process", action="store_true", help="Use FastAPI TestClient + mock LLM"
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("eval/reports"))
    args = parser.parse_args()

    cases = load_cases(args.dataset, args.limit)
    client = make_client(args.api_url, args.in_process)
    results = [run_case(client, c) for c in cases]
    report = write_reports(results, args.out, args.dataset)
    print(report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
