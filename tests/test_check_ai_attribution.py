"""Tests for hooks/check_ai_attribution.py.

Run with: uv run --with pytest pytest
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "check_ai_attribution.py"
spec = importlib.util.spec_from_file_location("check_ai_attribution", HOOK)
caa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caa)


# --- Assisted-by ---------------------------------------------------------------
@pytest.mark.parametrize(
    "line",
    [
        "Assisted-by: ClaudeCode:claude-opus-5-5",
        "Assisted-by: ClaudeCode:claude-opus-5",
        "Assisted-by: ClaudeCode:claude-sonnet-5-5",
        "Assisted-by: ClaudeCode:claude-fable-5-1",
        "Assisted-by: ClaudeCode:claude-haiku-4-5-20251001",
        "Assisted-by: ClaudeCode:claude-3-5-sonnet-20241022",  # older id order
        "Assisted-by: OpenCode:claude-opus-5-5",  # Claude model, other harness
        "Assisted-by: OpenCode:kimi-k2.6",
        "Assisted-by: Pi:glm-5.1",
        "Assisted-by: Codex:gpt-5.1-codex",
        "Assisted-by: Codex:o3",
        "Assisted-by: Cursor:composer-2",  # vendor without a rule: free-form
        "Assisted-by: GeminiCLI:gemini-3-pro",
        "Assisted-by: Aider:deepseek-v3.2",
        "Assisted-by: Copilot:gpt-5",
        "Assisted-by: SomeNewAgent:new-model-7",  # unknown harness and model
        "Assisted-by: SomeNewAgent:NewModel-7B",  # unknown vendors keep their case
        "Assisted-by: Zed:qwen3-coder-plus",
    ],
)
def test_assisted_by_accepted(line):
    assert caa.check_message(f"fix: x\n\n{line}\n") == []


@pytest.mark.parametrize(
    ("line", "hint"),
    [
        ("Assisted-by: ClaudeCode:claude-opus-5.5", "exact model id"),
        ("Assisted-by: ClaudeCode:claude-opus-4.8", "exact model id"),
        ("Assisted-by: ClaudeCode:Claude-Opus-5-5", "exact model id"),
        ("Assisted-by: ClaudeCode:claude-opus", "exact model id"),  # no version
        ("Assisted-by: ClaudeCode:Opus-5", "exact model id"),
        ("Assisted-by: OpenCode:claude-opus-5.5", "exact model id"),
        ("Assisted-by: OpenCode:Kimi-K2.6", "exact model id"),
        ("Assisted-by: Codex:GPT-5", "exact model id"),
        ("Assisted-by: GeminiCLI:Gemini-3-Pro", "exact model id"),
        ("Assisted-by: OpenCode:anthropic/claude-opus-5-5", "provider prefix"),
        ("Assisted-by: OpenCode:moonshotai/kimi-k2.6", "provider prefix"),
        ("Assisted-by: Claude-Code:claude-opus-5-5", "ClaudeCode"),
        ("Assisted-by: claudecode:claude-opus-5-5", "ClaudeCode"),
        ("Assisted-by: Opencode:kimi-k2.6", "OpenCode"),
        ("Assisted-by: Gemini-CLI:gemini-3-pro", "GeminiCLI"),
        ("Assisted-by: GitHubCopilot:gpt-5", "Copilot"),
        ("Assisted-by: Claude Code:Opus 5", "malformed"),
        ("Assisted-by: GitHub Copilot:gpt-5", "malformed"),
        ("Assisted-by: OpenCode:Kimi K2.6", "malformed"),
        ("assisted-by: ClaudeCode:claude-opus-5-5", "malformed"),
        ("Assisted-By: ClaudeCode:claude-opus-5-5", "malformed"),
        ("Assisted by: ClaudeCode:claude-opus-5-5", "malformed"),
        ("Assisted_by: ClaudeCode:claude-opus-5-5", "malformed"),
        ("Assisted-by:ClaudeCode:claude-opus-5-5", "malformed"),
        ("Assisted-by: ClaudeCode: claude-opus-5-5", "malformed"),
        ("Assisted-by: claude-opus-5-5", "malformed"),
        ("Assisted-by: ClaudeCode:claude-opus-5-5 ", "malformed"),
        ("Assisted-by: ClaudeCode:claude-opus-5-5 (reviewed)", "malformed"),
        ("Assisted-by: OpenCode", "malformed"),
        ("Assisted-by: ", "malformed"),
        ("Assisted-by: 1Harness:model-1", "one word"),
    ],
)
def test_assisted_by_rejected(line, hint):
    errors = caa.check_message(f"fix: x\n\n{line}\n")
    assert len(errors) == 1, errors
    assert hint in errors[0]


# --- Co-authors and sign-offs -----------------------------------------------------
@pytest.mark.parametrize(
    "line",
    [
        "Co-authored-by: Kabilar Gunalan <kabilar@datajoint.com>",
        "Co-authored-by: tabedzki <35670232+tabedzki@users.noreply.github.com>",
        "Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
        "Co-authored-by: Claudia Smith <claudia@princeton.edu>",  # starts with "Claud"
        "Co-authored-by: Ann McClaude <ann@princeton.edu>",  # agent word, not first
        "Co-authored-by: Kimi Laine <kimi@princeton.edu>",  # first name = agent name
        "Co-authored-by: Devin Lee <devin@princeton.edu>",
        "Co-authored-by: Jules Verne <jules@princeton.edu>",
        "Signed-off-by: Christian Tabedzki <35670232+tabedzki@users.noreply.github.com>",
        "co-authored-by: Jane Doe <jane@princeton.edu>",  # key case doesn't matter
    ],
)
def test_human_identities_accepted(line):
    assert caa.check_message(f"fix: x\n\n{line}\n") == []


@pytest.mark.parametrize(
    "line",
    [
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
        "Co-authored-by: Claude <noreply@anthropic.com>",
        "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>",
        "Co-authored-by: Claude Sonnet 4.6 <claude@users.noreply.github.com>",
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
        "Co-authored-by: copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>",
        "Co-authored-by: Cursor Agent <cursoragent@cursor.com>",
        "Co-authored-by: aider (gpt-4o) <noreply@aider.chat>",
        "Co-authored-by: Codex <codex@openai.com>",
        "Co-authored-by: devin-ai-integration[bot] <158243242+devin-ai-integration[bot]@users.noreply.github.com>",
        "Co-authored-by: google-labs-jules[bot] <161369871+google-labs-jules[bot]@users.noreply.github.com>",
        "Co-authored-by: Gemini <gemini@example.com>",
        "Co-authored-by: Jane Doe (aider) <jane@princeton.edu>",
        "Co-authored-by: Kimi <kimi@moonshot.ai>",  # agent name caught by its domain
        "Co-authored-by: some-new-agent[bot] <1+some-new-agent[bot]@users.noreply.github.com>",
        "Co-authored-by: Claude",  # no email at all
        "Co-authored by: Claude <noreply@anthropic.com>",  # misspelled key
        "Signed-off-by: Claude <noreply@anthropic.com>",
    ],
)
def test_agent_identities_rejected(line):
    errors = caa.check_message(f"fix: x\n\n{line}\n")
    assert len(errors) == 1, errors
    assert "not authors" in errors[0]


# --- Generated-with lines -----------------------------------------------------------
@pytest.mark.parametrize(
    "line",
    [
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
        "Generated with Claude Code",
        "Generated by GitHub Copilot",
        "Generated with AI",
    ],
)
def test_generated_lines_rejected(line):
    errors = caa.check_message(f"fix: x\n\n{line}\n")
    assert len(errors) == 1, errors
    assert "Generated with" in errors[0]


@pytest.mark.parametrize(
    "msg",
    [
        "fix: x\n\nGenerated by scripts/make_tables.py from the schema.\n",
        "fix: x\n\nThe docs are generated with sphinx.\n",
        "fix: x\n\nThis was assisted by Claude.\n",  # prose, not a trailer
        "fix: x\n\n  Assisted-by: an indented line in prose\n",
        "fix: x\n\nNote: something\n",
        "",
        "\n\n",
    ],
)
def test_ordinary_messages_accepted(msg):
    assert caa.check_message(msg) == []


def test_comments_and_scissors_ignored():
    msg = (
        "fix: x\n\nAssisted-by: ClaudeCode:claude-opus-5-5\n"
        "# Assisted-by: Claude Code:Opus 5\n"
        "# ------------------------ >8 ------------------------\n"
        "Co-Authored-By: Claude <noreply@anthropic.com>\n"  # in the diff of `commit -v`
    )
    assert caa.check_message(msg) == []


def test_custom_comment_char():
    # core.commentChar=";": only a ";" scissors line ends the message.
    msg = "fix: x\n; ------------------------ >8 ------------------------\nAssisted-by: bad one\n"
    assert caa.check_message(msg, comment_char=";") == []
    assert caa.check_message(msg, comment_char="#") != []


def test_every_problem_reported():
    msg = (
        "fix: x\n\nAssisted-by: ClaudeCode:claude-opus-5.5\n"
        "Assisted-by: OpenCode:kimi-k2.6\n"
        "Co-Authored-By: Claude <noreply@anthropic.com>\n"
    )
    errors = caa.check_message(msg)
    assert len(errors) == 2
    assert errors[0].startswith("line 3:") and errors[1].startswith("line 5:")


# --- Identities -------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("Christian Tabedzki", "35670232+tabedzki@users.noreply.github.com"),
        ("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"),
        ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com"),
        ("GitHub", "noreply@github.com"),
        ("Kimi Laine", "kimi@princeton.edu"),
        ("", ""),
    ],
)
def test_is_agent_people_and_automation(name, email):
    assert caa.is_agent(name, email) is None


@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com"),
        ("Claude", "noreply@anthropic.com"),
        ("claude[bot]", "209825114+claude[bot]@users.noreply.github.com"),
        ("braincogs-claude-agent[bot]", "1+braincogs-claude-agent[bot]@users.noreply.github.com"),
        ("Jane Doe", "123+Copilot@users.noreply.github.com"),
        ("Jane Doe (aider)", "jane@princeton.edu"),
        ("Someone", "bot@sub.openai.com"),
    ],
)
def test_is_agent_agents(name, email):
    assert caa.is_agent(name, email)


# --- Against real git -------------------------------------------------------------------
def git(repo, *args, env=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    ).stdout.strip()


ME = {
    "GIT_AUTHOR_NAME": "Jane Doe",
    "GIT_AUTHOR_EMAIL": "jane@princeton.edu",
    "GIT_COMMITTER_NAME": "Jane Doe",
    "GIT_COMMITTER_EMAIL": "jane@princeton.edu",
}
COPILOT = {
    "GIT_AUTHOR_NAME": "copilot-swe-agent[bot]",
    "GIT_AUTHOR_EMAIL": "198982749+Copilot@users.noreply.github.com",
}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base", env=ME)
    monkeypatch.chdir(tmp_path)
    for k, v in ME.items():
        monkeypatch.setenv(k, v)
    return tmp_path


def run(*args):
    return subprocess.run([sys.executable, str(HOOK), *args], capture_output=True, text=True)


def test_since_flags_only_bad_commits(repo):
    base = git(repo, "rev-parse", "HEAD")
    git(
        repo,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "ok\n\nAssisted-by: ClaudeCode:claude-opus-5-5",
        env=ME,
    )
    git(repo, "commit", "-q", "--allow-empty", "-m", "bot commit", env={**ME, **COPILOT})
    git(
        repo,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "x\n\nCo-authored-by: Copilot <1+Copilot@users.noreply.github.com>",
        env=ME,
    )
    r = run("--since", base)
    assert r.returncode == 1
    assert "checked 3 commit(s)" in r.stderr
    assert "bot commit" in r.stderr and "commit author" in r.stderr
    assert "Co-authored-by names" in r.stderr
    assert "ok\n" not in r.stderr


def test_since_clean_range(repo):
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "ok\n\nAssisted-by: Pi:glm-5.1", env=ME)
    r = run("--since", base)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("base", ["", "0" * 40, "deadbeef" * 5])
def test_since_unknown_base_checks_head_only(repo, base):
    git(repo, "commit", "-q", "--allow-empty", "-m", "bot commit", env={**ME, **COPILOT})
    git(repo, "commit", "-q", "--allow-empty", "-m", "fine", env=ME)
    r = run("--since", base)
    assert r.returncode == 0, r.stderr
    assert "checking HEAD only" in r.stderr and "checked 1 commit(s)" in r.stderr


def test_msg_file_checks_the_identity_about_to_be_used(repo, monkeypatch):
    msg = repo / "MSG"
    msg.write_text("fix: x\n\nAssisted-by: ClaudeCode:claude-opus-5-5\n")
    assert run(str(msg)).returncode == 0
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Claude")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "noreply@anthropic.com")
    r = run(str(msg))
    assert r.returncode == 1 and "commit author" in r.stderr


def test_as_a_real_commit_msg_hook(repo):
    hook = repo / ".git" / "hooks" / "commit-msg"
    hook.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HOOK}" "$1"\n')
    hook.chmod(0o755)
    ok = subprocess.run(
        [
            "git",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "a\n\nAssisted-by: ClaudeCode:claude-opus-5-5",
        ],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stderr
    bad = subprocess.run(
        [
            "git",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "b\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        ],
        capture_output=True,
        text=True,
    )
    assert bad.returncode != 0 and "not authors" in bad.stderr
    assert git(repo, "log", "-1", "--format=%s") == "a"


def test_since_with_head_skips_commits_after_it(repo):
    # On pull_request events HEAD is GitHub's merge commit; --head points at the PR tip.
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "pr tip", env=ME)
    tip = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "synthetic", env={**ME, **COPILOT})
    r = run("--since", base, "--head", tip)
    assert r.returncode == 0, r.stderr
    assert "checked 1 commit(s)" in r.stderr
    assert run("--since", base).returncode == 1


def test_since_empty_head_means_head(repo):
    # `--head ""` when the workflow expression has no value
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-q", "--allow-empty", "-m", "bot", env={**ME, **COPILOT})
    assert run("--since", base, "--head", "").returncode == 1
