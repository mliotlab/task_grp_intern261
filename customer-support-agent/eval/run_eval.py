"""Run eval v0 via POST /v1/chat and export Sprint 2 reports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from support_agent.config import get_settings
from support_agent.orchestrator import EMAIL, ORDER_TOOL, VIETNAMESE_STATUS
from support_agent.schemas import ChatResponse

DENIED_LOOKUPS = {"ord-104", "ord-105"}
MISSING_DETAILS = {"ord-002", "ord-103"}
ORDER_STATUS = re.compile(
    r"\b(?:" + "|".join([*VIETNAMESE_STATUS, *VIETNAMESE_STATUS.values()]) + r")\b",
    re.IGNORECASE,
)
DATE_VALUE = re.compile(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b")


class EvalCase(BaseModel):
    id: str = Field(min_length=1)
    category: str
    turns: list[str] = Field(min_length=1)
    expected_answer: str
    expected_doc_ids: list[str]
    expected_tool: str | None
    expected_tool_args: dict[str, Any] | None
    must_handoff: bool

    @property
    def in_scope(self) -> bool:
        return (
            len(self.turns) == 1
            and self.category in {"policy", "order"}
            and not self.must_handoff
            and self.expected_tool in {None, ORDER_TOOL}
        )


@dataclass
class CaseResult:
    id: str
    category: str
    status: str
    turns_checked: int = 0
    turn_latency_ms: str = ""
    answer: str = ""
    expected_doc_ids: str = ""
    cited_doc_ids: str = ""
    tools: str = ""
    citation_hit: bool | None = None
    tool_match: bool | None = None
    verified_order_fields: bool | None = None
    order_privacy: bool | None = None
    fallback_hit: bool | None = None
    trace_id: str = ""
    reason: str = ""


def load_cases(dataset: Path, limit: int | None = None) -> list[EvalCase]:
    cases = []
    seen = set()
    with (dataset / "cases.jsonl").open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                case = EvalCase.model_validate_json(line)
            except ValidationError:
                raise ValueError(f"Invalid eval case on line {number}.") from None
            if case.id in seen or any(not turn.strip() for turn in case.turns):
                raise ValueError(f"Duplicate case ID or empty turn on line {number}.")
            seen.add(case.id)
            cases.append(case)
    if not cases:
        raise ValueError("The eval dataset has no cases.")
    return cases[:limit] if limit else cases


def _private_order_reply(response: ChatResponse) -> bool:
    return (
        not EMAIL.search(response.answer)
        and not any(EMAIL.search(action.model_dump_json()) for action in response.actions)
        and not response.citations
        and not response.ticket_id
        and not any(action.ok for action in response.actions)
        and not ORDER_STATUS.search(response.answer)
        and not DATE_VALUE.search(response.answer)
    )


def _check_order(
    case: EvalCase,
    transcript: list[ChatResponse],
    result: CaseResult,
    requirements: dict[str, bool | None],
) -> None:
    needs_privacy = case.id in DENIED_LOOKUPS | MISSING_DETAILS
    if needs_privacy:
        result.order_privacy = all(_private_order_reply(reply) for reply in transcript)
        requirements["order privacy"] = result.order_privacy
    if case.id in DENIED_LOOKUPS:
        actions = transcript[-1].actions
        requirements["denied lookup"] = (
            len(actions) == 1 and not actions[0].ok and actions[0].summary == "not_found"
        )
    elif case.id in MISSING_DETAILS:
        requirements["clarification"] = "email" in transcript[-1].answer.lower()
    elif case.expected_tool == ORDER_TOOL:
        actions = transcript[-1].actions
        expected_order_id = (case.expected_tool_args or {}).get("order_id")
        result.verified_order_fields = (
            len(actions) == 1
            and actions[0].ok
            and actions[0].arguments.get("order_id") == expected_order_id
            and expected_order_id is not None
            and expected_order_id in transcript[-1].answer
            and bool(ORDER_STATUS.search(transcript[-1].answer))
            and not EMAIL.search(transcript[-1].answer + actions[0].model_dump_json())
        )
        requirements["verified order response"] = result.verified_order_fields


def run_case(client: Any, case: EvalCase) -> tuple[CaseResult, list[float]]:
    result = CaseResult(case.id, case.category, "failed")
    session_id = f"eval-{uuid.uuid4().hex}"
    latencies = []
    transcript = []
    for turn in case.turns:
        start = time.perf_counter()
        try:
            response = client.post("/v1/chat", json={"session_id": session_id, "message": turn})
            response.raise_for_status()
            body = ChatResponse.model_validate_json(response.content)
        except httpx.HTTPStatusError as error:
            result.reason = f"HTTP {error.response.status_code}"
            return result, latencies
        except (httpx.RequestError, ValidationError):
            result.reason = "API transport or invalid response schema"
            return result, latencies
        latencies.append((time.perf_counter() - start) * 1000)
        result.turn_latency_ms = json.dumps([round(value, 2) for value in latencies])
        if (
            not ChatResponse.model_fields.keys() <= body.model_fields_set
            or body.session_id != session_id
            or not body.trace_id.strip()
            or not body.answer.strip()
        ):
            result.reason = "Missing response field, answer/trace, or incorrect session"
            return result, latencies
        transcript.append(body)
        result.turns_checked += 1

    last = transcript[-1]
    result.answer = EMAIL.sub("[email]", last.answer)
    result.trace_id = last.trace_id
    result.expected_doc_ids = ", ".join(case.expected_doc_ids)
    result.cited_doc_ids = ", ".join(dict.fromkeys(c.doc_id for c in last.citations))
    result.tools = ", ".join(action.tool for action in last.actions)
    if not case.in_scope:
        result.status, result.reason = "outside_s2", "Behavior scheduled for Sprint 3"
        return result, latencies

    expected = set(case.expected_doc_ids)
    if expected:
        cited = {c.doc_id for c in last.citations if c.snippet.strip()}
        result.citation_hit = bool(expected & cited)
    elif case.category == "policy":
        answer = last.answer.lower()
        result.fallback_hit = (
            not last.citations
            and not last.actions
            and ("chưa tìm thấy" in answer or "not find" in answer)
            and ("nhân viên" in answer or "support agent" in answer)
        )
    tool_names = [a.tool for a in last.actions]
    result.tool_match = tool_names == ([case.expected_tool] if case.expected_tool else [])
    requirements = {
        "citation": result.citation_hit,
        "tool name/count": result.tool_match,
        "fallback": result.fallback_hit,
        "handoff state": last.handoff == case.must_handoff,
    }
    if case.category == "order":
        _check_order(case, transcript, result, requirements)
    failures = [name for name, passed in requirements.items() if passed is False]
    result.status = "failed" if failures else "passed_checks"
    result.reason = ", ".join(failures)
    return result, latencies


def _rate(values: list[bool | None]) -> str:
    measured = [value for value in values if value is not None]
    return f"{sum(measured)}/{len(measured)}" if measured else "not measured"


def _kb_digest(kb_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(kb_dir.rglob("*")):
        if (
            path.is_file()
            and path.suffix.lower() in {".md", ".pdf"}
            and path.name.lower() != "readme.md"
        ):
            digest.update(path.relative_to(kb_dir).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def write_reports(
    results: list[CaseResult], latencies: list[float], out_dir: Path, metadata: dict[str, str]
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    with (out_dir / f"eval_{stamp}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)
    counts = Counter(result.status for result in results)
    md = [f"# ShopX Sprint 2 eval — {stamp}", ""]
    md.extend(f"- {key}: {value}" for key, value in metadata.items())
    md += [
        "",
        f"Cases: **{len(results)}** · Passed checks: **{counts['passed_checks']}** · "
        f"Failed: **{counts['failed']}** · Outside S2: **{counts['outside_s2']}**",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for label, key in (
        ("Expected citation ID and nonempty snippet", "citation_hit"),
        ("Tool name and call count", "tool_match"),
        ("Verified-order response", "verified_order_fields"),
        ("Denied/incomplete lookup privacy checks", "order_privacy"),
        ("No-source response", "fallback_hit"),
    ):
        md.append(f"| {label} | {_rate([getattr(r, key) for r in results])} |")
    if latencies:
        p95 = sorted(latencies)[math.ceil(0.95 * len(latencies)) - 1]
        md.append(
            f"| Observed p95 ({len(latencies)} returned turns; includes warm-up) | {p95:.1f} ms |"
        )
    md += [
        "",
        "Answer correctness by judge and formal NFR-06 latency: not measured.",
        "",
        "## Cases requiring follow-up",
        "",
    ]
    md.extend(f"- {r.id} · {r.status} · {r.reason}" for r in results if r.status != "passed_checks")
    report = out_dir / f"eval_{stamp}.md"
    report.write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("eval/datasets/v0"))
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--in-process", action="store_true", help="Run the current app in-process")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path, default=Path("eval/reports"))
    parser.add_argument("--kb-dir", type=Path)
    parser.add_argument("--commit", default="not supplied")
    parser.add_argument("--model-label", help="Provider/model deployed at --api-url")
    parser.add_argument("--prompt-version", help="Prompt version deployed at --api-url")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")

    settings = get_settings()
    kb_dir = args.kb_dir or settings.kb_dir
    cases = load_cases(args.dataset, args.limit)
    if args.in_process:
        from fastapi.testclient import TestClient

        from services.chat_api.main import create_app

        if settings.llm_provider != "mock":
            parser.error("Set LLM_PROVIDER=mock for --in-process, or use --api-url.")
        client = TestClient(create_app(), raise_server_exceptions=False)
        mode, model, prompt = "in-process app", "mock", settings.prompt_version
    else:
        client = httpx.Client(base_url=args.api_url, timeout=60)
        mode = "HTTP API"
        model, prompt = (
            args.model_label or "not supplied",
            args.prompt_version or "not supplied",
        )
    results, latencies = [], []
    with client:
        for case in cases:
            result, measured = run_case(client, case)
            results.append(result)
            latencies.extend(measured)

    metadata = {
        "Mode": mode,
        "Model": model,
        "Prompt": prompt,
        "Commit": args.commit,
        "Dataset": str(args.dataset),
        "Dataset SHA-256": hashlib.sha256((args.dataset / "cases.jsonl").read_bytes()).hexdigest(),
        "Local KB SHA-256": _kb_digest(kb_dir),
        "Local embedding": settings.embedding_model,
        "Local embedding revision": settings.embedding_revision or "not supplied",
        "Local retrieval config": json.dumps(settings.agent_params()["retrieval"], sort_keys=True),
    }
    report = write_reports(results, latencies, args.out, metadata)
    print(report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
