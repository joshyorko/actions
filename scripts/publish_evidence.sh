#!/usr/bin/env bash
# Explicitly staged campaign checkpoint only; never stages files or force pushes.
set -euo pipefail
if [[ $# != 2 && $# != 3 ]] || [[ $# == 3 && "$3" != "--commit-only" ]]; then
    echo "usage: publish_evidence.sh <existing-branch> <commit-message> [--commit-only]" >&2
    exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo="$(git rev-parse --show-toplevel)"
evidence_python="$(command -v python3 || command -v python || true)"
if [[ -z "$evidence_python" ]]; then
    echo "Python 3 interpreter required (looked for python3 and python)" >&2
    exit 127
fi
"$evidence_python" "$script_dir/scan_staged_evidence.py" --repo "$repo"
git -C "$repo" diff --cached --check
git -C "$repo" commit -m "$2"
if [[ "${3:-}" == "--commit-only" ]]; then
    exit 0
fi
git -C "$repo" push origin "HEAD:refs/heads/$1"
