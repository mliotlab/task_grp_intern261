# Prompts

Prompts are code: they are **versioned**, **reviewed in PRs** and **evaluated** before being promoted.

```text
prompts/
├── system/v1.md      # system prompt; {context} is replaced by retrieved chunks
└── tools/v1.json     # tool descriptions shown to the LLM
```

Workflow for a prompt change:

1. Copy `v1.md` → `v2.md` (never edit a version that has an eval report).
2. Run `PROMPT_VERSION=v2 make eval` and compare with the previous report.
3. Open a PR with both eval reports; record the change in `docs/PROMPT_CARD.md`.
4. Promote by changing `PROMPT_VERSION` in `.env.example`.
