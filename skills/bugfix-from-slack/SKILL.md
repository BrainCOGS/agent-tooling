---
name: bugfix-from-slack
description: Use when fixing an error someone reported in Slack (a traceback, a failed cron job or alert, a rig error) in a BrainCOGS repo. Reproduces it with a regression test, files an agent bug report as the braincogs-claude-agent bot, fixes it, commits with the standard Assisted-by trailer and opens a draft PR as the bot.
---

# Fix a Slack-reported error in a BrainCOGS repo

Who does what:

| Action                  | Identity                          | How                                           |
| ----------------------- | --------------------------------- | --------------------------------------------- |
| Commits                 | the user (their git config)       | `git commit`, with one `Assisted-by` trailer  |
| Push                    | the user's own credentials        | `git push -u origin <branch>`                 |
| Issue, PR, PR/issue edits | the `braincogs-claude-agent` bot | `GH_TOKEN=$(mint-agent-token) gh ...`         |

Humans author commits; AI help is disclosed, never credited as an author. The
bot account opens the conversation on GitHub, but it never pushes or commits:
the app has issues and pull-requests permissions only, no contents.

## 0. Read the repo's instructions

Read the repo's `CLAUDE.md` for how to run its tests, its version pins and any
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

## 2. File the issue as the bot

Fill in `.github/ISSUE_TEMPLATE/agent_bug_report.md` from the repo (the
canonical copy is `templates/agent_bug_report.md` in agent-tooling). Keep its
`:robot: _AI text below_ :robot:` line at the top and fill in every section:

- **Report**: the Slack link, and the error text in a code block, verbatim.
- **Regression test**: `path::test_name`, and that it fails on `<base sha>`
  with that error.
- **Root cause**: what is wrong and why, with `file.py:line` references.
- **Linked PR**: leave as `TBD` for now; step 5 fills it in.

```bash
GH_TOKEN=$(mint-agent-token) gh issue create -R BrainCOGS/<repo> \
  --title "[BUG] <one-line summary>" --body-file <issue.md>
```

Skip this step if the repo has issues turned off (element-array-ephys,
element-calcium-imaging, iblapps). Put the same sections in the PR body instead.

## 3. Fix on a branch

- Branch from the default branch: `<user>/fix/<id>`, where `<user>` comes from
  `gh api user --jq .login` (with the user's own token, not the bot's).
- Make the smallest fix that makes the regression test pass. Then run the full
  test suite and `uvx prek run --all-files`.

## 4. Commit as the user, with one trailer

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
  author or committer.
- The `ai-attribution` commit-msg hook enforces this. If it rejects a commit,
  fix the message; never use `--no-verify`. If the hook isn't installed in this
  checkout, run `prek install`.

## 5. Push as the user, open the PR as the bot

```bash
git push -u origin <branch>
GH_TOKEN=$(mint-agent-token) gh pr create -R BrainCOGS/<repo> \
  --base <default-branch> --head <branch> --draft --reviewer tabedzki \
  --title "fix: <summary>" --body-file <pr.md>
GH_TOKEN=$(mint-agent-token) gh issue edit <issue> -R BrainCOGS/<repo> --body-file <issue.md>  # Linked PR: #<pr>
```

The PR body:
- starts with `:robot: _AI text below_ :robot:`
- has `Fixes #<issue>`
- covers the problem, the fix, and the tests, including that the regression
  test failed before the fix
- ends with the same `Assisted-by` trailer

Always pass `-R BrainCOGS/<repo>`. The element repos are forks, so a bare
`gh pr create` targets the DataJoint upstream.

When the work is done, mark the PR ready (`GH_TOKEN=$(mint-agent-token) gh pr ready ...`)
and tell the user it must be merged with **Rebase and merge** (or a merge
commit), not Squash. GitHub attributes a squash commit to the PR's opener, which
is the bot. So keep the branch's commits clean: one or a few Conventional
Commits, each with the trailer, and no "fix typo" or "address review" commits
(amend or fixup them instead).

## The token

- Mint a fresh token for each `gh` command that acts as the bot, inline in that
  command's environment, as above. Tokens last an hour; minting is cheap.
- Never print, echo, log or save the token. Never `export GH_TOKEN`, run
  `gh auth login` with it, or use it for `git push`.
- Use your own credentials (no `GH_TOKEN`) for everything that isn't the bot
  acting: pushes, `gh api user`, and reading CI logs.
- `mint-agent-token` is on PATH, linked from agent-tooling's `bin/`. It reads
  the key from `~/.config/braincogs-agent/agent.pem`. It needs no environment
  variables, since the App ID defaults to braincogs-claude-agent. If it fails,
  stop and tell the user; don't fall back to opening the issue or PR with the
  user's account.

## Agents that commit as themselves

Some cloud agents (Copilot coding agent, other GitHub Apps) commit as a bot.
Before merging such a branch, a human re-authors the commits and adds the
trailer. CI fails until they do:

```bash
git rebase -x 'git commit --amend --no-edit --reset-author --trailer "Assisted-by: Copilot:<model>"' origin/<default-branch>
git push --force-with-lease
```
