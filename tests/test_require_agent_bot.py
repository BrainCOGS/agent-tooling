"""Tests for claude-hooks/require_agent_bot.py.

Run with: uv run --no-project --with pytest pytest
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "claude-hooks" / "require_agent_bot.py"
BOT = "GH_TOKEN=$(mint-agent-token)"


def run(payload, raw=None):
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw if raw is not None else json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stderr


def bash(command, cwd=None):
    return run({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})


@pytest.fixture
def braincogs_checkout(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "git@github.com:BrainCOGS/U19-pipeline-python.git",
        ],
        check=True,
    )
    return str(tmp_path)


@pytest.fixture
def other_checkout(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "https://github.com/someone/else.git",
        ],
        check=True,
    )
    return str(tmp_path)


@pytest.mark.parametrize(
    "command",
    [
        f'{BOT} gh issue create -R BrainCOGS/U19-pipeline-python --title "[BUG] x" --body-file b.md',
        f"{BOT} gh pr create -R BrainCOGS/ViRMEn --head b --draft --reviewer tabedzki --body-file p.md",
        'GH_TOKEN="$(mint-agent-token)" gh issue create -R BrainCOGS/x --title t --body b',
        "GH_TOKEN=`mint-agent-token` gh issue create -R BrainCOGS/x -t t -b b",
        f"{BOT} gh issue create --repo=BrainCOGS/x -t t -b b",
        f"{BOT} gh issue create -RBrainCOGS/x -t t -b b",
        f"{BOT} gh issue create -R github.com/BrainCOGS/x -t t -b b",
        f"{BOT} gh issue create -R https://github.com/BrainCOGS/x -t t -b b",
        f"env {BOT} gh issue create -R BrainCOGS/x -t t -b b",
        f"cd /tmp && {BOT} gh issue create -R BrainCOGS/x -t t -b b && echo done",
        f"{BOT} gh api -X POST repos/BrainCOGS/x/issues -f title=t",
        f"{BOT} gh pr create -R BrainCOGS/x --body-file - <<'EOF'\nIt's a body with gh issue create in it\nEOF",
        # PRs are opened by the user, not the bot:
        "gh pr create -R BrainCOGS/x --draft --title t --body b",
        "gh pr new -R BrainCOGS/x -t t -b b",
        "gh pr create -R BrainCOGS/x --body-file - <<'EOF'\nbody\nEOF",
        'bash -c "gh pr create -R BrainCOGS/x -t t -b b"',
        "gh api repos/BrainCOGS/x/pulls -f title=t -f head=b -f base=main",
        "gh api -X POST repos/BrainCOGS/x/pulls -f title=t -f head=b -f base=main",
        # Not creating anything, or not BrainCOGS:
        "gh issue view 12 -R BrainCOGS/x",
        "gh issue list -R BrainCOGS/x",
        "gh pr view 165 -R BrainCOGS/U19-pipeline-python --json body",
        "gh pr checks 13 -R BrainCOGS/x",
        "gh api repos/BrainCOGS/x/issues",  # GET
        "gh api repos/BrainCOGS/x/pulls/3/comments -f body=hi",  # not a create path
        "gh issue create -R someone/else -t t -b b",
        "gh pr create -R datajoint/element-array-ephys -t t -b b",
        "git push -u origin my-branch",
        "echo 'gh issue create -R BrainCOGS/x'",  # quoted text, not a command
        "grep -rn 'gh pr create' ~/code/agent-tooling",
        f'bash -c "{BOT} gh issue create -R BrainCOGS/x -t t -b b"',
        "ls -la",
        "",
    ],
)
def test_allowed(command):
    code, err = bash(command)
    assert code == 0, err


@pytest.mark.parametrize(
    ("command", "hint"),
    [
        (
            'gh issue create -R BrainCOGS/U19-pipeline-python --title "[BUG] x" --body-file b.md',
            "your account",
        ),
        ("gh issue create -R braincogs/x -t t -b b", "your account"),  # owner case
        ("gh issue new -R BrainCOGS/x -t t -b b", "your account"),
        ("gh issue create --repo BrainCOGS/x -t t -b b", "your account"),
        (
            "gh issue create -R https://github.com/BrainCOGS/x.git -t t -b b",
            "your account",
        ),
        ("GH_TOKEN=$GH_TOKEN gh issue create -R BrainCOGS/x -t t -b b", "must be"),
        ("GH_TOKEN=ghp_abc gh issue create -R BrainCOGS/x -t t -b b", "must be"),
        (
            "export GH_TOKEN=$(mint-agent-token); gh issue create -R BrainCOGS/x -t t -b b",
            "your account",
        ),
        (
            "GH_TOKEN=$(mint-agent-token) echo hi && gh issue create -R BrainCOGS/x -t t -b b",
            "your account",
        ),
        ("cd ~/code/U19 && gh issue create -R BrainCOGS/x -t t -b b", "your account"),
        (
            "gh issue create -R BrainCOGS/x -t t --body-file - <<'EOF'\nbody\nEOF",
            "your account",
        ),
        ('bash -c "gh issue create -R BrainCOGS/x -t t -b b"', "your account"),
        (
            "sh -c 'cd /tmp && gh issue create -R BrainCOGS/x -t t -b b'",
            "your account",
        ),
        ('eval "gh issue create -R BrainCOGS/x -t t -b b"', "your account"),
        ("/usr/bin/gh issue create -R BrainCOGS/x -t t -b b", "your account"),
        ("gh api -X POST repos/BrainCOGS/x/issues -f title=t", "your account"),
        (
            "gh api repos/BrainCOGS/x/issues -f title=t -f body=b",  # -f implies POST
            "your account",
        ),
        (
            "gh api --method=POST /repos/BrainCOGS/x/issues --input body.json",
            "your account",
        ),
        ("gh issue create -R BrainCOGS/x -t \"it's broken", "could not parse"),
    ],
)
def test_blocked(command, hint):
    code, err = bash(command)
    assert code == 2
    assert hint in err
    assert "mint-agent-token" in err  # always says how to do it right


def test_braincogs_checkout_requires_explicit_repo(braincogs_checkout):
    code, err = bash(f"{BOT} gh issue create -t t -b b", cwd=braincogs_checkout)
    assert code == 2 and "-R BrainCOGS/<repo>" in err
    code, err = bash("gh issue create -t t -b b", cwd=braincogs_checkout)
    assert code == 2
    code, _ = bash(
        f"{BOT} gh issue create -R BrainCOGS/x -t t -b b", cwd=braincogs_checkout
    )
    assert code == 0


def test_braincogs_checkout_pr_needs_no_bot_or_repo(braincogs_checkout):
    for cmd in ("gh pr create --draft -t t -b b", "gh pr create -R BrainCOGS/x --fill"):
        code, err = bash(cmd, cwd=braincogs_checkout)
        assert code == 0, err


def test_braincogs_checkout_api_placeholder(braincogs_checkout):
    code, _ = bash(
        "gh api -X POST repos/{owner}/{repo}/issues -f title=t", cwd=braincogs_checkout
    )
    assert code == 2
    code, _ = bash(
        f"{BOT} gh api -X POST repos/{{owner}}/{{repo}}/issues -f title=t",
        cwd=braincogs_checkout,
    )
    assert code == 0


def test_other_checkout_untouched(other_checkout):
    for cmd in (
        "gh issue create -t t -b b",
        "gh pr create --fill",
        "gh api -X POST repos/{owner}/{repo}/issues -f title=t",
    ):
        code, err = bash(cmd, cwd=other_checkout)
        assert code == 0, err


def test_missing_or_bad_cwd_is_not_braincogs(tmp_path):
    assert bash("gh issue create -t t -b b", cwd=str(tmp_path / "missing"))[0] == 0
    assert bash("gh issue create -t t -b b", cwd=None)[0] == 0


@pytest.mark.parametrize(
    ("tool", "tool_input", "code"),
    [
        (
            "mcp__github__create_issue",
            {"owner": "BrainCOGS", "repo": "x", "title": "t"},
            2,
        ),
        ("mcp__github__create_pull_request", {"owner": "braincogs", "repo": "x"}, 0),
        (
            "mcp__github__pull_request_write",
            {"method": "create", "owner": "BrainCOGS", "repo": "x"},
            0,
        ),
        (
            "mcp__github__issue_write",
            {"method": "create", "owner": "BrainCOGS", "repo": "x"},
            2,
        ),
        (
            "mcp__github__issue_write",
            {"method": "update", "owner": "BrainCOGS", "repo": "x"},
            0,
        ),
        ("mcp__github__create_issue", {"owner": "someone", "repo": "x"}, 0),
        ("mcp__github__get_issue", {"owner": "BrainCOGS", "repo": "x"}, 0),
        ("mcp__slack__create_issue_thing", {"owner": "BrainCOGS"}, 0),  # not GitHub
        ("Read", {"file_path": "/tmp/x"}, 0),
    ],
)
def test_mcp_and_other_tools(tool, tool_input, code):
    assert run({"tool_name": tool, "tool_input": tool_input})[0] == code


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "{}",
        '{"tool_name": "Bash"}',
        '{"tool_name": "Bash", "tool_input": "x"}',
    ],
)
def test_malformed_payload_fails_closed(raw):
    code, err = run(None, raw=raw)
    assert code == 2 and "could not read the hook payload" in err
