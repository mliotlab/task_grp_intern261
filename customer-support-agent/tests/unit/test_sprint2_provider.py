from __future__ import annotations

import json

import httpx
import pytest

from support_agent.llm import Message, ToolCall
from support_agent.llm.base import LLMError
from support_agent.llm.compatible import CompatibleLLM


def test_chat_completions_maps_tool_messages_and_usage() -> None:
    call = ToolCall("abc", "get_order_status", {"order_id": "SX-000001"})

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model"
        assert payload["messages"][0]["tool_calls"][0]["id"] == "abc"
        assert payload["messages"][1]["tool_call_id"] == "abc"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "def",
                                    "function": {
                                        "name": "get_order_status",
                                        "arguments": '{"order_id":"SX-000001"}',
                                    },
                                },
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2},
            },
        )

    llm = CompatibleLLM("test-model", "https://example.invalid/v1/", None, 1.0)
    llm.client.close()
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        llm.client = client
        response = llm.complete(
            [
                Message("assistant", tool_calls=[call]),
                Message("tool", '{"status":"confirmed"}', tool_call_id="abc"),
            ]
        )
    assert response.tool_calls[0] == ToolCall("def", call.name, call.arguments)
    assert response.usage.available and response.usage.prompt_tokens == 11


@pytest.mark.parametrize(
    "status,payload",
    [
        (429, {"error": "private"}),
        (
            200,
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "invalid",
                                    "function": {"name": "lookup", "arguments": "not JSON"},
                                }
                            ]
                        }
                    }
                ]
            },
        ),
    ],
)
def test_provider_errors_hide_raw_body(status: int, payload: dict) -> None:
    llm = CompatibleLLM("test-model", "https://example.invalid/v1", None, 1.0)
    llm.client.close()
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
    with httpx.Client(transport=transport) as client:
        llm.client = client
        with pytest.raises(LLMError, match="Chat provider"):
            llm.complete([Message("user", "Hi")])
