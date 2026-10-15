#!/usr/bin/env bash
# Link this repo's tools into place, so `git pull` here updates them:
#   bin/*            -> ~/.local/bin/
#   skills/<name>/   -> ~/.claude/skills/<name>
# Re-run after adding a skill or a command. Safe to re-run.
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

link() {  # link <target> <link path>
    local target=$1 path=$2
    if [[ -L $path ]]; then
        ln -sfn "$target" "$path"
    elif [[ -e $path ]]; then
        # A real file or directory: move it aside rather than delete it.
        mv "$path" "$path.bak.$(date +%Y%m%d%H%M%S)"
        echo "moved the old $path aside" >&2
        ln -s "$target" "$path"
    else
        ln -s "$target" "$path"
    fi
    echo "$path -> $target"
}

mkdir -p ~/.local/bin ~/.claude/skills
for f in "$repo"/bin/*; do link "$f" ~/.local/bin/"$(basename "$f")"; done
for d in "$repo"/skills/*/; do d=${d%/}; link "$d" ~/.claude/skills/"$(basename "$d")"; done
