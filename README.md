# agent-tooling

Skills and helpers for AI agents working on BrainCOGS repos.

```
agent-tooling/
├── hooks/
│   └── check_ai_attribution.py # commit-msg hook + CI check, vendored into each repo
├── skills/
│   └── bugfix-from-slack/
│       └── SKILL.md            # Slack error -> regression test -> fix -> draft PR
├── tests/                      # tests for hooks/
└── install.sh                  # links skills/ into place
```

## Install

```bash
git clone <this repo> ~/code/agent-tooling
~/code/agent-tooling/install.sh
```

`install.sh` symlinks each `skills/<name>/` into `~/.claude/skills/<name>`, so a
`git pull` here updates them. Re-run it after adding a skill.

Agents have no GitHub identity of their own here. Commits, pushes, issues and
PRs all go through the user's account, and the commits disclose the agent with
an `Assisted-by` trailer. If your harness adds its own attribution (Claude Code
adds a `Co-Authored-By` trailer and a "Generated with" line by default), turn it
off. For Claude Code, in `~/.claude/settings.json`:

```json
"attribution": { "commit": "", "pr": "" }
```

## Where things live

| What                                              | Where                                                                 |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| Workflow skills                                   | this repo, linked into `~/.claude/skills/`                            |
| How to run a repo's tests, its version pins       | that repo's `AGENTS.md` (read by Claude Code and other agents)        |
| AI attribution check                              | each repo's `.github/scripts/check_ai_attribution.py` (copy of `hooks/`) |

## Attribution policy

**Humans author commits; AI help is disclosed.**

- Each commit an agent helped with ends with one trailer per agent:
  `Assisted-by: <Harness>:<model>`, e.g. `Assisted-by: ClaudeCode:claude-opus-5-5`
  or `Assisted-by: OpenCode:kimi-k2.6`. `git log --grep='^Assisted-by: '` finds
  them all.
- No AI or bot identity as a commit's author, committer, `Co-authored-by` or
  `Signed-off-by`. The exceptions are non-AI automation: Dependabot, GitHub
  Actions, Renovate, pre-commit.ci, and the GitHub web UI as committer.
- No `Generated with <agent>` lines in commit messages.
- Issues, PRs, commits and pushes all stay with the human who ran the agent.
  A PR opened by an agent account (Copilot coding agent, other GitHub Apps) is
  the exception: GitHub attributes its squash commit to that account, so merge
  it with "Rebase and merge" (see tech_calendar_streamlit `78c6983`: author
  `copilot-swe-agent[bot]`, `Co-authored-by: tabedzki`). The CI check on pushes
  to the default branch flags it if this happens.

`hooks/check_ai_attribution.py` enforces this in two places:

- **Local commit-msg hook**: checks the message, plus the author and committer
  git is about to use.
- **CI**: checks every commit in a PR or push (`--since <base>`). This catches
  commits made on GitHub that no local hook sees, like cloud agents' commits.

The checker is robust to new harnesses and models:
- Any one-word harness is accepted. The ones in `KNOWN_HARNESSES` must use their
  canonical spelling.
- Any one-token model ID is accepted. Models from the vendors in `MODEL_RULES`
  must match that vendor's API ID format.
- Agent identities are recognized four ways: GitHub App bot accounts (`[bot]`),
  AI vendor email domains, agent names and GitHub logins, and aider-style
  `(aider)` suffixes.

To support a new agent, add it to the matching table and add a test.

### Bot-authored commits

Copilot coding agent (`copilot-swe-agent[bot]`) authored 44 merged commits
before this policy (Sept 2025 – May 2026): U19-pipeline-python 4 (#49),
tech_calendar_streamlit 30 (8 PRs), WaterPubsGUI 3, U19-pipeline-matlab 7.

- **Past commits stay as they are.** They're merged through merge commits.
  Rewriting them would change every later SHA in four repos, three of them
  public, and break clones, forks and links. They already disclose the agent
  (it's the author), just not in the current form. The CI check only looks at
  new commits, so they never trip it.
- **From 2026-10-15 on, agents don't author commits.** An agent that commits
  as itself (Copilot coding agent, other GitHub Apps) can still draft a branch.
  Before merge, a human re-authors the commits, and CI fails until they do:

  ```bash
  git rebase -x 'git commit --amend --no-edit --reset-author --trailer "Assisted-by: Copilot:<model>"' origin/<default-branch>
  git push --force-with-lease
  ```

## Changing the attribution check

1. Edit `hooks/check_ai_attribution.py` and `tests/`, then run
   `uv run --no-project --with pytest pytest`.
2. Copy the file to each repo's `.github/scripts/check_ai_attribution.py` in a PR.
   Don't edit a vendored copy.

The file opts out of each repo's ruff (`# ruff: noqa`, `# fmt: off`), so the
repos' different rules and line lengths leave it byte-identical. This repo still
lints it with `--ignore-noqa`. A repo that enables ruff's `PGH` rules also needs
`".github/scripts/check_ai_attribution.py" = ["PGH004"]` under
`[lint.per-file-ignores]`, as in WaterPubsGUI.

Each repo wires it up in `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: ai-attribution
      name: AI attribution (Assisted-by trailer, no AI authors)
      language: python
      entry: python .github/scripts/check_ai_attribution.py
      stages: [commit-msg]
```

and in `.github/workflows/lint.yml`, with `fetch-depth: 0` on the checkout:

```yaml
- name: Check AI attribution in the commits of the PR (or push)
  env:
    BASE: ${{ github.event.pull_request.base.sha || github.event.before }}
    # On PRs, HEAD is GitHub's synthetic merge commit; check up to the PR's tip.
    HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}
  run: python3 .github/scripts/check_ai_attribution.py --since "$BASE" --head "$HEAD_SHA"
```
