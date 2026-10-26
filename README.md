# agent-tooling

Skills and helpers for AI agents working on BrainCOGS repos.

```
agent-tooling/
├── bin/
│   └── vendor                  # copy the shared files into repo checkouts (--check to find drift)
├── skills/
│   └── bugfix-from-slack/
│       └── SKILL.md            # reported error -> regression test -> issue -> fix -> draft PR
├── templates/
│   └── agent_bug_report.md     # canonical copy of each repo's issue template
└── install.sh                  # links skills/ into place
```

## Install

```bash
git clone git@github.com:BrainCOGS/agent-tooling.git ~/code/agent-tooling
~/code/agent-tooling/install.sh
```

Repos also carry their own copy of the skill (see below), so you only need this
for repos that don't, and to edit the canonical copy.

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
| Workflow skills                                   | this repo, linked into `~/.claude/skills/`; vendored into each repo's `.claude/skills/` |
| How to run a repo's tests, its version pins       | that repo's `AGENTS.md` (read by Claude Code and other agents)        |
| Agent bug report template                         | each repo's `.github/ISSUE_TEMPLATE/agent_bug_report.md` (copy of `templates/`) |

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
  `copilot-swe-agent[bot]`, `Co-authored-by: tabedzki`).

Nothing enforces this. The repos vendored a commit-msg hook and CI check
(`check_ai_attribution.py`) until 2026-10-26. It only checked the format of a
disclosure, not whether one was missing: an agent committing as the user looks
the same as the user. On the private repos it couldn't be a required check
either, so it reported after merging. Agents follow the policy from each repo's
`AGENTS.md` and the skill; review the trailers in PRs.

### Bot-authored commits

Copilot coding agent (`copilot-swe-agent[bot]`) authored 44 merged commits
before this policy (Sept 2025 – May 2026): U19-pipeline-python 4 (#49),
tech_calendar_streamlit 30 (8 PRs), WaterPubsGUI 3, U19-pipeline-matlab 7.

- **Past commits stay as they are.** They're merged through merge commits.
  Rewriting them would change every later SHA in four repos, three of them
  public, and break clones, forks and links. They already disclose the agent
  (it's the author), just not in the current form.
- **From 2026-10-15 on, agents don't author commits.** An agent that commits
  as itself (Copilot coding agent, other GitHub Apps) can still draft a branch.
  Before merge, a human re-authors the commits:

  ```bash
  git rebase -x 'git commit --amend --no-edit --reset-author --trailer "Assisted-by: Copilot:<model>"' origin/<default-branch>
  git push --force-with-lease
  ```

## Vendoring

This repo is the one canonical place. Each repo carries byte-identical copies, so
a clone (and a cloud agent) has everything without installing anything:

```bash
bin/vendor ~/code/U19-pipeline-python ~/code/tech_calendar_streamlit   # copy
bin/vendor --check ~/code/U19-pipeline-python                          # drift? exits 1
```

Then open a PR in each repo from your account. Never edit a vendored copy; change
it here and re-run `bin/vendor`. Per-repo details (how to run tests, version
pins) stay in that repo's `AGENTS.md`, which is why the skill itself needs no
per-repo edits.
