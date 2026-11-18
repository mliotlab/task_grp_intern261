# Contributing Guide

This guide is the single engineering standard for every project in `task_grp_intern261`.
It implements Section 6 ("Engineering process") of each requirement specification.

## 1. Sprint rhythm

| When | Ceremony | Output |
|---|---|---|
| Monday | Sprint planning (≤ 30 min) | Sprint goal + committed issues on the project board |
| Daily (async) | Stand-up in the team channel: *done / doing / blocked* | — |
| Thursday | Internal code freeze for the sprint | PRs open for review |
| Friday | Sprint review / demo with mentor + retrospective | `docs/reports/WSR-S<n>.md` merged |

Blocked for more than 1 hour? Ask your mentor — do not wait for the next check-in.

## 2. Work tracking

- Every piece of work is a **GitHub issue** on the **GitHub Project** board (`Backlog → Todo → In Progress → In Review → Done`).
- Label every issue with the project: `project:csa`, `project:era`, `project:rsm`, `project:s2r`,
  plus a type (`type:feature`, `type:bug`, `type:docs`, `type:chore`) and a priority (`P0`–`P2`).
- Every functional requirement (`FR-xx`) and non-functional requirement (`NFR-xx`) is traceable to ≥ 1 issue
  and ≥ 1 test case. Put the requirement ID in the issue title, e.g. `[FR-04] get_order_status tool`.

## 3. Git workflow

```text
main  ──●────────●────────●──────── (protected, always green, squash-merge only)
         \      /  \      /
          feat/12-csa-chat-endpoint
```

- **Never push to `main`.** Branch from the latest `main`, open a PR, merge with **Squash and merge**.
- **Branch name:** `<type>/<issue>-<project>-<short-desc>`
  - `feat/12-csa-chat-endpoint`
  - `fix/31-rsm-null-bbox`
  - `docs/40-era-design-doc-v1`
- **Project scopes:** `csa` · `era` · `rsm` · `s2r` · `repo` (root files).

### Commit messages — Conventional Commits

```text
<type>(<scope>): <imperative summary, ≤ 72 chars>

[optional body: why, not what]

[optional footer: Closes #12]
```

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`, `build`.

```text
feat(csa): add get_order_status tool with email verification
fix(rsm): handle images with zero detections in fill-rate computation
docs(era): add ADR-0003 choose arq as job queue
```

The **PR title** must also follow this format — it becomes the squashed commit on `main` (checked by CI).

## 4. Pull Requests

- Small PRs: **< 400 changed lines** (excluding generated files and data).
- Use the PR template; link the issue with `Closes #<n>`.
- At least **1 approval** and **green CI** before merge. Reviewers respond within **24 hours**.
- Reviewers distinguish **must-fix** (`[blocking]`) from **suggestions** (`[nit]`).

### Reviewer checklist

- [ ] Code does what the issue asks; acceptance criteria verified
- [ ] Readable, well-named, no dead code
- [ ] Errors and edge cases handled
- [ ] Tests cover the new logic; coverage did not drop
- [ ] No negative impact on performance or security
- [ ] Docs updated (README / API / Design Doc / ADR)

## 5. Code quality

- **Python 3.11**, formatted and linted with **ruff** (config: root `ruff.toml`, extended per project).
- Type hints on all public functions; Pydantic models at API boundaries.
- No secrets in Git. Use `.env` (ignored) and keep `.env.example` (committed) up to date.
- Configuration comes from environment variables or files in `configs/`, never hard-coded paths.
- Structured **JSON logs** with a `request_id` (and `job_id` where relevant).

Run locally before pushing:

```bash
make lint     # ruff check + ruff format --check
make test     # pytest with coverage
```

## 6. Definition of Done

An issue moves to **Done** only when:

- [ ] Code is merged into `main` via an approved PR with green CI.
- [ ] Tests exist for the new logic (unit or integration); coverage did not decrease.
- [ ] Acceptance criteria are verified, and *how* they were verified is written in the PR.
- [ ] Related docs are updated (README, API docs, Design Doc, ADR).
- [ ] The feature has been demoed or can be run by following the README.

## 7. Releases

- Tag format per project: `<project>-v<MAJOR>.<MINOR>.<PATCH>`, e.g. `csa-v1.0.0`, `rsm-v1.0.0`.
- Every release has Release Notes (`docs/RELEASE_NOTES.md`, template in `docs/templates/`) published on
  **GitHub Releases**, including measured NFR values and third-party licenses.

## 8. Data, models and licenses

- Never commit real customer / personal data. Use public or synthetic data only.
- Never commit large binaries (model weights, datasets). Commit a **checksum + download link** instead.
- Record the license of every dataset, model and library you use in the project README.
