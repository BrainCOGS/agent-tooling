---
name: bugfix-from-slack
description: Use when fixing an error someone reported in Slack (a traceback, a failed cron job or alert, a rig error) in a BrainCOGS repo. Reproduces it with a regression test, fixes it, commits with the standard Assisted-by trailer and opens a draft PR from the user's account.
---

# Fix a Slack-reported error in a BrainCOGS repo

Everything goes through the user's own account: commits (their git config),
the push (their credentials) and the PR (their `gh` login). The agent files
nothing on its own and has no GitHub identity of its own. Humans author commits;
AI help is disclosed with an `Assisted-by` trailer, never credited as an author.

## 0. Read the repo's instructions

Read the repo's `AGENTS.md` for how to run its tests, its version pins and any
other quirks. Find the default branch with
`gh repo view BrainCOGS/<repo> --json defaultBranchRef -q .defaultBranchRef.name`.

## 1. Reproduce with a regression test first

- Copy the Slack link and the error text exactly as posted (traceback, log
  lines). Don't paraphrase.
- Write a test that fails the same way the report does, before you change any
  code. Run it and confirm it fails with that error on the base commit. Note the
  base commit's short SHA.
- Cover the corner cases around the bug too: empty, zero, `None`, one versus many,
  numpy arrays versus lists, missing keys.

## 2. Fix on a branch

- Branch from the default branch: `<user>/fix/<id>`, where `<user>` comes from
  `gh api user --jq .login`.
- Make the smallest fix that makes the regression test pass. Then run the full
  test suite and `uvx prek run --all-files`.

## 3. Commit as the user, with one trailer

Use Conventional Commits, and end the message with one trailer per agent:

```
fix: <summary>

<what was wrong, why, and how it's fixed>

Assisted-by: ClaudeCode:claude-opus-5-5
```

- `Assisted-by: <Harness>:<model>`. `<Harness>` is one word (`ClaudeCode` for
  Claude Code). `<model>` is the exact model ID the harness reports
  (`claude-opus-5-5`, never `claude-opus-5.5` or `Opus 5`), with no provider
  prefix.
- Never add `Co-authored-by` or `Signed-off-by` for an AI, or a
  `Generated with ...` line. Never commit with an AI's name or email as
  author or committer. If the harness adds its own commit or PR attribution
  text, turn it off (Claude Code: `"attribution": {"commit": "", "pr": ""}` in
  `~/.claude/settings.json`).
- The `ai-attribution` commit-msg hook enforces this. If it rejects a commit,
  fix the message; never use `--no-verify`. If the hook isn't installed in this
  checkout, run `prek install`.

## 4. Push and open the PR

```bash
git push -u origin <branch>
gh pr create -R BrainCOGS/<repo> --base <default-branch> --head <branch> \
  --draft --title "fix: <summary>" --body-file <pr.md>
```

Always pass `-R BrainCOGS/<repo>`. The element repos are forks, so a bare
`gh pr create` targets the DataJoint upstream.

The PR body:
- starts with `:robot: _AI text below_ :robot:`
- **Report**: the Slack link, and the error text in a code block, verbatim
- **Regression test**: `path::test_name`, and that it fails on `<base sha>`
  with that error
- **Root cause**: what is wrong and why, with `file.py:line` references
- covers the fix and the tests
- ends with the same `Assisted-by` trailer

When the work is done, mark the PR ready (`gh pr ready ...`). Keep the
branch's commits clean: one or a few Conventional Commits, each with the
trailer, and no "fix typo" or "address review" commits (amend or fixup them
instead).

## Agents that commit as themselves

Some cloud agents (Copilot coding agent, other GitHub Apps) commit as a bot.
Before merging such a branch, a human re-authors the commits and adds the
trailer. CI fails until they do:

```bash
git rebase -x 'git commit --amend --no-edit --reset-author --trailer "Assisted-by: Copilot:<model>"' origin/<default-branch>
git push --force-with-lease
```
