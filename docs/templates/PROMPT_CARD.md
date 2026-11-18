# Prompt Card – <agent name>

## Active prompt versions

| Prompt | File | Version | Changed in PR |
|---|---|---|---|
| System prompt | `prompts/system/vN.md` | vN | # |
| Tool schemas | `prompts/tools/vN.json` | vN | # |

## Model and parameters

| Parameter | Value |
|---|---|
| Provider / model | |
| Temperature | |
| Max output tokens | |
| Context window used (history turns) | |

## Behaviour contract

- Answers policy questions only from retrieved documents and always cites them.
- Never reveals order data before the order ID and email are verified.
- Hands off to a human when <rules>.

## Evaluation results for this version

| Metric | Value | Eval run |
|---|---|---|

## Known failure modes

## Change log

| Version | Date | Change | Eval delta |
|---|---|---|---|
