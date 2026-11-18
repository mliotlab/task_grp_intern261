# task_grp_intern261

> Monorepo for the **HCMUT EE Machine Learning & IoT Lab — Engineering Internship Program (Cohort 26.1)**.
> Four intern teams, four projects, one shared engineering standard.

[![CSA CI](https://github.com/<org>/task_grp_intern261/actions/workflows/csa-ci.yml/badge.svg)](../../actions/workflows/csa-ci.yml)
[![ERA Backend CI](https://github.com/<org>/task_grp_intern261/actions/workflows/era-backend-ci.yml/badge.svg)](../../actions/workflows/era-backend-ci.yml)
[![ERA Frontend CI](https://github.com/<org>/task_grp_intern261/actions/workflows/era-frontend-ci.yml/badge.svg)](../../actions/workflows/era-frontend-ci.yml)
[![RSM CI](https://github.com/<org>/task_grp_intern261/actions/workflows/rsm-ci.yml/badge.svg)](../../actions/workflows/rsm-ci.yml)
[![S2R CI](https://github.com/<org>/task_grp_intern261/actions/workflows/s2r-ci.yml/badge.svg)](../../actions/workflows/s2r-ci.yml)

> Replace `<org>` in the badge URLs above with the GitHub organization/user that hosts this repository.

---

## Projects

| Folder | Project | Track | Team code | Scope | Duration |
|---|---|---|---|---|---|
| [`customer-support-agent/`](customer-support-agent/) | **Customer Support Agent** — LLM agent that answers from policy docs (RAG), looks up orders, creates tickets and hands off to humans | AI Engineering | AIE-01 (CSA) | Product build, 4 sprints | 4 weeks · 8–10 h/person/week |
| [`enterprise-research-agent/`](enterprise-research-agent/) | **Enterprise Research Agent** — multi-service web platform: async ingestion, research agent that plans, retrieves and writes cited reports | Software Eng. · AI Eng. | SE-AI-02 (ERA) | Product build, 4 sprints | 4 weeks · 8–10 h/person/week |
| [`retail-shelf-monitoring/`](retail-shelf-monitoring/) | **Retail Shelf Monitoring** — CV service that detects products, finds empty shelf gaps, computes fill rate and raises alerts | AI Engineering | AIE-01 (RSM) | Product build, 4 sprints | 4 weeks · 8–10 h/person/week |
| [`sim2real-segmentation/`](sim2real-segmentation/) | **Sim2Real Domain Adaptation in Semantic Segmentation** (GTA5 → Cityscapes) | Research Familiarization | S2R | Mini research, 4 weekly deliverables | 4 weeks · 5–7 h/person/week |

Each project folder is **self-contained**: its own dependencies, `Makefile`, `docker-compose.yml`, docs and tests.
Shared conventions (Git workflow, CI, PR rules, document templates) live at the repository root.

## Repository layout

```text
task_grp_intern261/
├── .github/
│   ├── workflows/              # one CI workflow per project (path-filtered) + PR title lint
│   ├── ISSUE_TEMPLATE/         # bug / feature / task forms
│   ├── pull_request_template.md
│   ├── CODEOWNERS
│   └── dependabot.yml
├── docs/
│   └── templates/              # WSR, PRD, Design Doc, ADR, Test Plan, Eval Report, ...
├── customer-support-agent/
├── enterprise-research-agent/
├── retail-shelf-monitoring/
├── sim2real-segmentation/
├── CONTRIBUTING.md             # Git workflow, commit convention, Definition of Done
├── ruff.toml                   # shared Python lint/format rules (projects extend it)
├── .pre-commit-config.yaml
├── .editorconfig
├── .gitignore
└── LICENSE
```

> **Why a monorepo?** The requirement specs describe one repository per project. Here the four projects share one
> repository so mentors can review all teams in one place and the engineering standard stays identical. GitHub only
> reads workflows from the root `.github/workflows/`, so each project's `ci.yml` from the spec lives there as
> `<project>-ci.yml` and is filtered by path — a PR touching only `retail-shelf-monitoring/` runs only RSM CI.
> If a team later wants its own repository, `git subtree split --prefix=<project-folder>` extracts it with history.

## Quick start

```bash
git clone https://github.com/<org>/task_grp_intern261.git
cd task_grp_intern261

# one-time: install git hooks (ruff, trailing whitespace, secret guard, ...)
pip install pre-commit && pre-commit install

# then work inside your project folder
cd customer-support-agent        # or enterprise-research-agent / retail-shelf-monitoring / sim2real-segmentation
cat README.md                    # project-specific setup
```

Requirements: **Python 3.11**, **Docker + Docker Compose v2**, **Git**; Node.js 20+ for `enterprise-research-agent/frontend` and `e2e`.

Repository owner: see [`docs/REPO_SETUP.md`](docs/REPO_SETUP.md) for the first push, branch protection, labels and boards.

## How we work

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before your first PR. In short:

- `main` is protected — changes land only through Pull Requests with green CI and ≥ 1 approval, merged with **squash**.
- Branch name: `<type>/<issue>-<project>-<short-desc>`, e.g. `feat/12-csa-chat-endpoint`.
- Commits & PR titles follow **Conventional Commits** with the project as scope: `feat(rsm): add gap detection`.
- One sprint = one week. Every sprint ends with a **Weekly Status Report** in `<project>/docs/reports/WSR-S<n>.md`.
- Every important technical decision is an **ADR** in `<project>/docs/adr/`.

## Document templates

All teams use the same templates in [`docs/templates/`](docs/templates/):

| Template | File in project | When |
|---|---|---|
| [Weekly Status Report](docs/templates/WSR.md) | `docs/reports/WSR-S<n>.md` | Every sprint |
| [PRD](docs/templates/PRD.md) | `docs/PRD.md` | Sprint 1 |
| [Design Doc](docs/templates/DESIGN.md) | `docs/DESIGN.md` | v0 Sprint 1, v1 Sprint 2 |
| [ADR](docs/templates/ADR.md) | `docs/adr/NNNN-<title>.md` | Any time a key decision is made |
| [Test Plan](docs/templates/TEST_PLAN.md) | `docs/TEST_PLAN.md` | Sprint 3 |
| [Evaluation Report](docs/templates/EVAL_REPORT.md) | `docs/EVAL_REPORT.md` | Sprint 3 |
| [Release Notes](docs/templates/RELEASE_NOTES.md) | `docs/RELEASE_NOTES.md` | Sprint 4 |
| [Runbook](docs/templates/RUNBOOK.md) | `docs/RUNBOOK.md` | Sprint 4 |
| [Postmortem](docs/templates/POSTMORTEM.md) | `docs/POSTMORTEM.md` | Sprint 4 |
| [Model Card](docs/templates/MODEL_CARD.md) | `models/MODEL_CARD.md` | RSM, Sprint 3–4 |
| [Prompt Card](docs/templates/PROMPT_CARD.md) | `docs/PROMPT_CARD.md` | CSA, Sprint 4 |

## Using this work in your résumé

Each project README has a **"Highlights"** section listing the engineering practices the project demonstrates
(CI/CD, evaluation harness, async workers, model registry, ...). After v1.0.0 is tagged, link directly to your
project folder and your merged PRs — e.g. `github.com/<org>/task_grp_intern261/pulls?q=author:<you>+is:merged`.

## License

Code is released under the [MIT License](LICENSE) unless a project folder states otherwise. Third-party datasets,
models and libraries keep their own licenses — see the **Licenses** section of each project README
(e.g. Ultralytics YOLO is AGPL-3.0, SKU-110K, GTA5 and Cityscapes have their own terms).
