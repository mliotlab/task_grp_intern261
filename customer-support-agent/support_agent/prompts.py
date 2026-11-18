"""Load versioned prompts from `prompts/` (NFR-08)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from support_agent.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"


def load_system_prompt(version: str, prompts_dir: Path = PROMPTS_DIR) -> str:
    return (prompts_dir / "system" / f"{version}.md").read_text(encoding="utf-8")


def load_tool_descriptions(version: str, prompts_dir: Path = PROMPTS_DIR) -> dict[str, Any]:
    return json.loads((prompts_dir / "tools" / f"{version}.json").read_text(encoding="utf-8"))
