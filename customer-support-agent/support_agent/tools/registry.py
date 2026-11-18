"""Tool registry: one place that declares tool schemas and validates arguments before execution.

The LLM proposes a tool call; the registry validates the arguments with a Pydantic model and only
then runs the Python function. Invalid arguments never reach business services (NFR-03).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Raised when a tool is unknown, its arguments are invalid, or it fails."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    func: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        """OpenAI-style function schema, generated from the Pydantic model."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"Unknown tool '{name}'")
        try:
            args = tool.args_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolError(f"Invalid arguments for '{name}': {exc.errors()}") from exc
        return tool.func(**args.model_dump())
