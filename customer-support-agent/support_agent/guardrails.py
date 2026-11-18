"""Input and output guardrails (NFR-05).

Input guardrails run before the LLM (prompt injection, out-of-scope, abusive language).
Output guardrails run before replying (no ungrounded policy claims, no leaked order data).
"""

from __future__ import annotations

from dataclasses import dataclass

from support_agent.schemas import Citation


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str | None = None
    suggest_handoff: bool = False


def check_input(message: str) -> GuardrailResult:
    """TODO(NFR-05): detect prompt injection ("ignore previous instructions", role-play, system
    prompt extraction), out-of-scope requests and strong frustration (→ suggest_handoff=True).
    Start with rules, measure on the attack set in eval/datasets, then decide if an LLM classifier
    is worth the latency and cost (write an ADR)."""
    return GuardrailResult(allowed=True)


def check_output(
    answer: str, citations: list[Citation], used_policy_knowledge: bool
) -> GuardrailResult:
    """TODO(FR-03, NFR-02): reject policy answers without citations; make sure no order data
    appears unless get_order_status succeeded in this turn."""
    return GuardrailResult(allowed=True)
