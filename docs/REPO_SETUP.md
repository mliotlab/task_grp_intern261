# Repository setup (for the repo owner, one time)

## 1. Push the first version

```bash
cd task_grp_intern261
git init -b main
git add -A
git commit -m "chore(repo): initial scaffold for intern cohort 26.1"
git remote add origin https://github.com/<org>/task_grp_intern261.git
git push -u origin main
```

Then replace `<org>` in the root `README.md` badges.

## 2. Protect `main` (Settings → Branches → Add rule, or Rulesets)

- ✅ Require a pull request before merging · 1 approval · dismiss stale approvals
- ✅ Require status checks to pass — select the jobs that exist after the first CI run:
  `Lint & unit tests`, `Lint, tests & OpenAPI contract`, `lint-typecheck-build`, `lint-test`, `conventional-title`
- ✅ Require conversation resolution · ✅ Block force pushes
- Settings → General → Pull Requests: allow **Squash merging** only; default message = "Pull request title"

> Path-filtered workflows do not run for PRs that don't touch their folder. If you mark them as
> *required*, use GitHub **Rulesets** (which skip required checks that were not triggered) or keep
> only `conventional-title` as required and rely on reviewers for the rest.

## 3. Collaborators and owners

- Invite members (Settings → Collaborators / Teams), ideally one GitHub team per project.
- Replace the placeholder handles in `.github/CODEOWNERS`, then enable "Require review from Code Owners".

## 4. Labels and project board

```bash
for p in csa era rsm s2r; do gh label create "project:$p" --color 1f6feb; done
for t in feature bug docs chore; do gh label create "type:$t" --color 8250df; done
for p in P0 P1 P2; do gh label create "$p" --color d1242f; done
```

Create one GitHub Project (board view) per team, columns: Backlog → Todo → In Progress → In Review → Done.

## 5. Secrets (only when needed)

Settings → Secrets and variables → Actions. Never put API keys in code or workflow files.
CI runs with the mock LLM, so no secret is required for the scaffold to be green.
