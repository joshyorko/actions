#!/usr/bin/env bash
# Explicitly staged campaign checkpoint only; never stages files or force pushes.
set -euo pipefail
if [[ $# != 2 ]]; then
    echo "usage: publish_evidence.sh <existing-branch> <commit-message>" >&2
    exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo="$(git rev-parse --show-toplevel)"
python3 "$script_dir/scan_staged_evidence.py" --repo "$repo"
git -C "$repo" diff --cached --check
git -C "$repo" commit -m "$2"
git -C "$repo" push origin "HEAD:refs/heads/$1"
