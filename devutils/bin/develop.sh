#!/usr/bin/env bash
set -Eeuo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
rcc_path=""
downloaded_rcc_path="$script_dir/rcc"
rcc_version="v18.19.3"
task=${1:-Bootstrap}

case "$(uname -s):$(uname -m)" in
    Darwin:arm64) asset=rcc-macosarm64 ;;
    Darwin:x86_64) asset=rcc-macos64 ;;
    Linux:x86_64 | Linux:amd64) asset=rcc-linux64 ;;
    *)
        printf 'Unsupported RCC developer platform: %s %s\n' "$(uname -s)" "$(uname -m)" >&2
        exit 2
        ;;
esac

download_rcc() {
    local temporary_path="${downloaded_rcc_path}.download.$$"
    trap 'rm -f -- "$temporary_path"' RETURN
    curl --fail --location --retry 3 --silent --show-error \
        "https://github.com/joshyorko/rcc/releases/download/${rcc_version}/${asset}" \
        --output "$temporary_path"
    chmod +x "$temporary_path"
    mv -f -- "$temporary_path" "$downloaded_rcc_path"
    if [[ $($downloaded_rcc_path version 2>/dev/null || true) != "$rcc_version" ]]; then
        rm -f -- "$downloaded_rcc_path"
        printf 'Downloaded RCC did not report version %s.\n' "$rcc_version" >&2
        return 1
    fi
    trap - RETURN
}

path_rcc=$(command -v rcc 2>/dev/null || true)
path_rcc_version=""
if [[ -n "$path_rcc" ]]; then
    path_rcc_version=$($path_rcc version 2>/dev/null || true)
fi

if command -v brew >/dev/null 2>&1; then
    brew_rcc=""
    brew_version=""
    if brew list --cask rcc >/dev/null 2>&1; then
        brew_rcc=$(command -v rcc 2>/dev/null || true)
        if [[ -n "$brew_rcc" ]]; then
            brew_version=$($brew_rcc version 2>/dev/null || true)
        fi
    fi
    if [[ "$brew_version" != "$rcc_version" ]]; then
        printf 'Installing RCC %s from joshyorko/tools...\n' "$rcc_version"
        brew tap joshyorko/tools
        if brew list --cask rcc >/dev/null 2>&1; then
            brew upgrade --cask joshyorko/tools/rcc || true
        else
            brew install --cask joshyorko/tools/rcc || true
        fi
        hash -r 2>/dev/null || true
        brew_rcc=$(command -v rcc 2>/dev/null || true)
        if [[ -n "$brew_rcc" ]]; then
            brew_version=$($brew_rcc version 2>/dev/null || true)
        fi
    fi
    if [[ "$brew_version" == "$rcc_version" ]]; then
        rcc_path=$brew_rcc
    else
        printf 'Homebrew did not provide RCC %s; using the release asset fallback.\n' "$rcc_version" >&2
    fi
fi

if [[ -z "$rcc_path" && "$path_rcc_version" == "$rcc_version" ]]; then
    rcc_path=$path_rcc
fi

if [[ -z "$rcc_path" ]]; then
    downloaded_version=""
    if [[ -x "$downloaded_rcc_path" ]]; then
        downloaded_version=$($downloaded_rcc_path version 2>/dev/null || true)
    fi
    if [[ "$downloaded_version" != "$rcc_version" ]]; then
        printf 'Installing RCC %s (%s)...\n' "$rcc_version" "$asset"
        download_rcc
    fi
    rcc_path=$downloaded_rcc_path
fi

exec "$rcc_path" run -r "$repo_root/developer/toolkit.yaml" --dev -t "$task"
