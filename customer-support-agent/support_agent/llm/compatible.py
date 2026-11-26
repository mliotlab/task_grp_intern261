"""OpenAI-compatible Chat Completions adapter for the configured endpoint."""

from __future__ import annotations

import json
from typing import Any

import httpx

from support_agent.llm.base import LLMError, LLMResponse, Message, ToolCall, Usage


def _provider_message(message: Message) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    return payload


def _provider_response(payload: dict[str, Any]) -> LLMResponse:
    message = payload["choices"][0]["message"]
    content = message.get("content") or ""
    if not isinstance(content, str):
        raise ValueError("Provider returned non-text content.")
    calls = []
    for tool in message.get("tool_calls") or []:
        function = tool["function"]
        arguments = json.loads(function["arguments"])
        if not isinstance(arguments, dict) or not tool["id"] or not function["name"]:
            raise ValueError("Provider returned an invalid tool call.")
        calls.append(ToolCall(tool["id"], function["name"], arguments))
    usage = payload.get("usage") or {}
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")
    if type(tokens_in) is int and type(tokens_out) is int and min(tokens_in, tokens_out) >= 0:
        return LLMResponse(content, calls, Usage(tokens_in, tokens_out, available=True))
    return LLMResponse(content, calls)


class CompatibleLLM:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None,
        timeout: float,
    ) -> None:
        url = httpx.URL(base_url)
        if (
            url.scheme not in {"https", "http"}
            or not url.host
            or url.query
            or url.fragment
            or url.userinfo
        ):
            raise ValueError("LLM_BASE_URL must be an absolute HTTP(S) API root.")
        if not model.strip() or timeout <= 0:
            raise ValueError("A model name and positive LLM timeout are required.")
        self.model = model
        self.endpoint = url.copy_with(path=url.path.rstrip("/") + "/chat/completions")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": [_provider_message(message) for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
        try:
            response = self.client.post(self.endpoint, json=body)
            response.raise_for_status()
            return _provider_response(response.json())
        except httpx.HTTPError:
            raise LLMError("Chat provider request failed.") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise LLMError("Chat provider returned an invalid response.") from None
