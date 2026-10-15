#!/usr/bin/env python3
"""Claude Code PreToolUse hook: BrainCOGS issues and PRs are opened by the bot.

The agent opens issues and pull requests in BrainCOGS repos as the
braincogs-claude-agent GitHub App, never with the user's account:

    GH_TOKEN=$(mint-agent-token) gh issue create -R BrainCOGS/<repo> ...
    GH_TOKEN=$(mint-agent-token) gh pr create    -R BrainCOGS/<repo> ...

This hook blocks (exit 2, reason on stderr for the agent) any Bash command that
creates an issue or PR in a BrainCOGS repo without that inline token:
`gh issue create`, `gh pr create`, and `gh api` POSTs to .../issues or .../pulls.
It also requires an explicit `-R BrainCOGS/<repo>` in a BrainCOGS checkout,
because the element repos are forks and a bare `gh pr create` targets the
upstream. GitHub MCP tools that create issues or PRs in BrainCOGS are blocked
outright, since they always act as the user.

Commands that don't create issues or PRs, and repos outside BrainCOGS, pass
untouched. A payload the hook can't read fails closed.

Registered in ~/.claude/settings.json (see agent-tooling's install.sh).
Standard library only.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys

ORG = "braincogs"
MINT = "__MINT_AGENT_TOKEN__"
MINT_RE = re.compile(r"\$\(\s*mint-agent-token\s*\)|`\s*mint-agent-token\s*`")
TOKEN_VARS = {"GH_TOKEN", "GITHUB_TOKEN"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", ";;", "|&"}
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# A heredoc body: `<<'EOF'` ... `EOF`. The text inside is data, not commands.
HEREDOC_RE = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)", re.S
)
QUICK_RE = re.compile(r"\bgh\b")
CREATE_PATH_RE = re.compile(
    r"^/?repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?:issues|pulls)/?$", re.I
)

HOW = (
    "Open BrainCOGS issues and PRs as the braincogs-claude-agent bot, with the "
    "token inline in the same command: "
    "`GH_TOKEN=$(mint-agent-token) gh issue create -R BrainCOGS/<repo> ...` "
    "(or `gh pr create ... --draft --reviewer tabedzki`). See the bugfix-from-slack skill."
)


class Blocked(Exception):
    pass


def _is_braincogs(repo: str) -> bool:
    """OWNER/REPO, HOST/OWNER/REPO or a URL: the owner is the second-to-last part."""
    parts = [
        p for p in re.sub(r"^\w+://", "", repo).removesuffix(".git").split("/") if p
    ]
    return len(parts) >= 2 and parts[-2].lower() == ORG


def _cwd_is_braincogs(cwd: str | None) -> bool:
    if not cwd:
        return False
    try:
        remotes = subprocess.run(
            ["git", "-C", cwd, "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return re.search(r"github\.com[:/]braincogs/", remotes, re.I) is not None


def _segments(command: str) -> list[list[str]]:
    """Split a shell command into simple commands (token lists)."""
    command = HEREDOC_RE.sub("", command)
    command = MINT_RE.sub(MINT, command)
    lexer = shlex.shlex(
        command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()"
    )
    lexer.whitespace_split = True
    tokens = list(lexer)  # ValueError on unbalanced quotes: the caller fails closed
    segs, cur = [], []
    for t in tokens:
        if t in SEPARATORS:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def _flag(args: list[str], *names: str) -> str | None:
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if n.startswith("--") and a.startswith(n + "="):
                return a.split("=", 1)[1]
            if not n.startswith("--") and a.startswith(n) and len(a) > len(n):
                return a[len(n) :]  # -RBrainCOGS/x
    return None


def check_segment(seg: list[str], cwd_braincogs: bool) -> None:
    env: dict[str, str] = {}
    i = 0
    while i < len(seg):
        t = seg[i]
        if t in ("env", "command", "exec", "time", "nohup", "sudo"):
            i += 1
        elif ASSIGN_RE.match(t):
            k, v = t.split("=", 1)
            env[k] = v
            i += 1
        else:
            break
    words = seg[i:]
    # Nested shells: bash -c "gh issue create ...", eval "...". Plain arguments
    # (echo '...gh issue create...') are data and stay unchecked.
    if words and words[0].rsplit("/", 1)[-1] in SHELLS and "-c" in words:
        i = words.index("-c")
        if i + 1 < len(words):
            check_command(words[i + 1], cwd_braincogs)
    elif words and words[0] == "eval":
        check_command(" ".join(words[1:]), cwd_braincogs)
    if not words or words[0].rsplit("/", 1)[-1] != "gh":
        return
    args = words[1:]
    kind = None
    if args[:2] in (["issue", "create"], ["issue", "new"]):
        kind = "an issue"
    elif args[:2] in (["pr", "create"], ["pr", "new"]):
        kind = "a PR"
    elif args[:1] == ["api"]:
        path = next(
            (
                a
                for a in args[1:]
                if CREATE_PATH_RE.match(a.replace("{owner}", "OWNER"))
            ),
            None,
        )
        method = (_flag(args, "-X", "--method") or "").upper()
        has_fields = any(
            a in ("-f", "-F", "--field", "--raw-field", "--input")
            or re.match(r"^(-f|-F|--field=|--raw-field=)", a)
            for a in args
        )
        if path and (method == "POST" or (not method and has_fields)):
            m = CREATE_PATH_RE.match(path)
            owner = m["owner"]
            if owner.lower() == ORG or (owner == "{owner}" and cwd_braincogs):
                kind = "an issue or PR (gh api)"
                if env.get("GH_TOKEN") != MINT and env.get("GITHUB_TOKEN") != MINT:
                    raise Blocked(
                        f"Blocked: this would create {kind} in a BrainCOGS repo with your account. {HOW}"
                    )
        return
    if kind is None:
        return
    repo = _flag(args, "-R", "--repo")
    if repo is None:
        if cwd_braincogs:
            raise Blocked(
                f"Blocked: pass `-R BrainCOGS/<repo>` explicitly when opening {kind} "
                "from a BrainCOGS checkout (the element repos are forks; a bare "
                f"`gh {args[0]} create` can target the upstream). {HOW}"
            )
        return
    if not _is_braincogs(repo):
        return
    for var in TOKEN_VARS:
        if var in env and env[var] != MINT:
            raise Blocked(
                f"Blocked: {var} for {kind} must be `$(mint-agent-token)`, inline. "
                f"Never pass a stored or exported token. {HOW}"
            )
    if env.get("GH_TOKEN") != MINT and env.get("GITHUB_TOKEN") != MINT:
        raise Blocked(
            f"Blocked: this would open {kind} in {repo} with your account, not the bot's. {HOW}"
        )


def check_command(command: str, cwd_braincogs: bool) -> None:
    if not QUICK_RE.search(command):
        return
    try:
        segs = _segments(command)
    except ValueError as e:
        if re.search(r"\bgh\s+(issue|pr)\s+(create|new)\b|\bgh\s+api\b", command):
            raise Blocked(
                f"Blocked: could not parse this command ({e}) to check who opens the "
                f"issue or PR. Write it as one plain command. {HOW}"
            ) from e
        return
    for seg in segs:
        check_segment(seg, cwd_braincogs)


MCP_CREATE_RE = re.compile(
    r"create_(issue|pull_request)|issue_write|pull_request_write|create_pr\b", re.I
)


def check_mcp(tool: str, tool_input: dict) -> None:
    if "github" not in tool.lower() or not MCP_CREATE_RE.search(tool):
        return
    if re.search(r"issue_write|pull_request_write", tool, re.I) and tool_input.get(
        "method"
    ) not in (None, "create"):
        return
    owner = str(tool_input.get("owner", ""))
    if owner.lower() == ORG:
        raise Blocked(
            f"Blocked: {tool} would open this issue or PR in BrainCOGS with your account. {HOW}"
        )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool = payload["tool_name"]
        tool_input = payload["tool_input"]
        if not isinstance(tool_input, dict):
            raise TypeError("tool_input is not an object")
    except (ValueError, KeyError, TypeError) as e:
        print(
            f"Blocked: could not read the hook payload ({e}). (agent-tooling require_agent_bot.py)",
            file=sys.stderr,
        )
        return 2
    try:
        if tool == "Bash":
            command = tool_input.get("command", "")
            if QUICK_RE.search(command):
                check_command(command, _cwd_is_braincogs(payload.get("cwd")))
        elif tool.startswith("mcp__"):
            check_mcp(tool, tool_input)
    except Blocked as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
