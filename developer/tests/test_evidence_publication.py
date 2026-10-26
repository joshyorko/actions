"""Real shell regression: failed scans/commits must never reach publication."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WRAPPER = Path(__file__).resolve().parents[2] / "scripts/publish_evidence.sh"

# Shell commands use the controlled Git function. The native Python scanner
# receives only the real Git directory and still reads the actual staged index.
PUBLICATION_SHELL = r"""
set -euo pipefail
fixture_python=$1
fixture_git_script=$2
fixture_native_git_dir=$3
fixture_bin=$4
fixture_fallback=$5
shift 5
git() { "$fixture_python" "$fixture_git_script" "$@"; }
fixture_run_python() { PATH="$fixture_native_git_dir" "$fixture_python" "$@"; }
python() { fixture_run_python "$@"; }
if [ "$fixture_fallback" = 1 ]; then
    PATH="$fixture_bin"
    unset -f python3 2>/dev/null || true
    if command -v python3 >/dev/null; then
        echo 'fixture unexpectedly exposes python3' >&2
        exit 98
    fi
else
    PATH="$fixture_bin:$PATH"
    python3() { fixture_run_python "$@"; }
fi
export PATH
if [ "$(type -t git)" != function ]; then
    echo 'fixture Git interception unavailable' >&2
    exit 97
fi
readonly -f git
# Stay in this shell: a second Bash process could rewrite PATH at startup.
source "$@"
"""


def _resolve_bash_executable(real_git, *, windows=None):
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return "bash"
    if not real_git:
        raise FileNotFoundError("Git for Windows Bash requires a resolved Git path")

    git_path = Path(real_git).resolve()
    git_directory = git_path.parent
    if git_directory.name.casefold() in {"bin", "cmd"}:
        git_root = git_directory.parent
    else:
        git_root = git_directory
    bash_path = git_root / "bin" / "bash.exe"
    if not bash_path.is_file():
        raise FileNotFoundError(
            f"Git for Windows Bash was not found beside resolved Git: {bash_path}"
        )
    return str(bash_path)


def _path_for_bash(path, *, windows=None):
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return str(path)

    normalized = str(path).replace("\\", "/")
    if len(normalized) >= 3 and normalized[1:3] == ":/":
        return f"/{normalized[0].lower()}{normalized[2:]}"
    return normalized


def test_windows_bash_resolver_uses_git_install_layout(tmp_path):
    git_root = tmp_path / "Git"
    git_executable = git_root / "cmd" / "git.exe"
    git_executable.parent.mkdir(parents=True)
    git_executable.touch()
    bash_executable = git_root / "bin" / "bash.exe"
    bash_executable.parent.mkdir(parents=True)
    bash_executable.touch()

    assert _resolve_bash_executable(str(git_executable), windows=True) == str(
        bash_executable
    )

    assert _resolve_bash_executable("unused", windows=False) == "bash"
    assert _path_for_bash(
        r"C:\work\repo\scripts\publish_evidence.sh", windows=True
    ) == ("/c/work/repo/scripts/publish_evidence.sh")


def test_windows_bash_resolver_fails_without_git_bash(tmp_path):
    git_executable = tmp_path / "Git" / "cmd" / "git.exe"
    git_executable.parent.mkdir(parents=True)
    git_executable.touch()

    try:
        _resolve_bash_executable(str(git_executable), windows=True)
    except FileNotFoundError as error:
        assert "Git for Windows Bash" in str(error)
    else:
        raise AssertionError("Windows must not fall back to PATH bash/WSL")


class EvidencePublicationTests(unittest.TestCase):
    def run_pipeline(
        self,
        payload,
        *,
        commit_exit=0,
        working_copy=None,
        raw_json=None,
        mode=None,
        python_fallback_only=False,
        rewrite_startup_path=False,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_git = shutil.which("git")
            subprocess.run([real_git, "init", "-q", str(root)], check=True)
            evidence = root / "docs/program/evidence/test/receipt.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                raw_json if raw_json is not None else json.dumps(payload)
            )
            subprocess.run([real_git, "-C", str(root), "add", "."], check=True)
            if working_copy is not None:
                evidence.write_text(json.dumps(working_copy))
            calls = root / "publication-calls"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            dirname = fake_bin / "dirname"
            dirname.write_text(
                "#!/bin/sh\n"
                '[ "$1" = -- ] && shift\n'
                "case $1 in */*) printf '%s\\n' \"${1%/*}\";; "
                "*) printf '.\\n';; esac\n"
            )
            dirname.chmod(0o755)
            fake_git_script = root / "fake_git.py"
            fake_git_script.write_text(
                "import os,subprocess,sys\n"
                "args=sys.argv[1:]\n"
                "operation=args[2] if args[:1]==['-C'] else args[0]\n"
                "if operation=='rev-parse':\n"
                " with open(os.environ['TEST_PUBLICATION_CALLS'],'a') as f: f.write('start\\n')\n"
                "if operation in ('commit','push'):\n"
                " with open(os.environ['TEST_PUBLICATION_CALLS'],'a') as f: f.write(operation+'\\n')\n"
                " sys.exit(int(os.environ['TEST_COMMIT_EXIT']) if operation=='commit' else 0)\n"
                "sys.exit(subprocess.call([os.environ['TEST_REAL_GIT'],*args]))\n"
            )
            environment = dict(
                os.environ,
                TEST_REAL_GIT=real_git,
                TEST_PUBLICATION_CALLS=str(calls),
                TEST_COMMIT_EXIT=str(commit_exit),
            )
            if rewrite_startup_path:
                startup = root / "bash-startup.sh"
                startup.write_text('export PATH="/usr/bin:/bin"\n')
                environment["BASH_ENV"] = _path_for_bash(startup)
            bash = _resolve_bash_executable(real_git)
            if not Path(bash).is_absolute():
                bash = shutil.which(bash)
            wrapper_path = _path_for_bash(WRAPPER)
            result = subprocess.run(
                [
                    bash,
                    "-c",
                    PUBLICATION_SHELL,
                    "publication-fixture",
                    _path_for_bash(sys.executable),
                    _path_for_bash(fake_git_script),
                    _path_for_bash(Path(real_git).parent),
                    _path_for_bash(fake_bin),
                    "1" if python_fallback_only else "0",
                    wrapper_path,
                    "existing-test-branch",
                    "test evidence",
                ]
                + ([mode] if mode is not None else []),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
            )
            return result, calls.read_text().splitlines() if calls.exists() else []

    def test_failed_scan_stops_shell_before_commit_and_push(self):
        secret = "synthetic-do-not-print-" + "x" * 43
        result, calls = self.run_pipeline({"_meta": {"token": secret}})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["start"])
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_scan_reads_index_even_if_working_copy_was_redacted(self):
        result, calls = self.run_pipeline(
            {"token": "synthetic-staged-value"},
            working_copy={"token": "[redacted]"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["start"])

    def test_failed_commit_stops_shell_before_push(self):
        result, calls = self.run_pipeline({"token": "[redacted]"}, commit_exit=23)
        self.assertEqual(result.returncode, 23)
        self.assertEqual(calls, ["start", "commit"])

    def test_duplicate_json_fields_cannot_hide_a_value(self):
        result, calls = self.run_pipeline(
            {}, raw_json='{"token":"synthetic-hidden-value","token":"[redacted]"}'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["start"])
        self.assertNotIn("synthetic-hidden-value", result.stdout + result.stderr)

    def test_invalid_json_stops_shell_before_commit_and_push(self):
        result, calls = self.run_pipeline({}, raw_json="{invalid evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["start"])

    def test_successful_scan_and_commit_allow_push_in_order(self):
        result, calls = self.run_pipeline({"token": "[redacted-stopped-session]"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["start", "commit", "push"])

    def test_commit_only_still_scans_and_never_pushes(self):
        result, calls = self.run_pipeline({"token": "[redacted]"}, mode="--commit-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, ["start", "commit"])
        result, calls = self.run_pipeline(
            {"token": "synthetic-secret"}, mode="--commit-only"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["start"])

    def test_python_fallback_allows_safe_scan_commit_and_push(self):
        result, calls = self.run_pipeline(
            {"token": "[redacted]"}, python_fallback_only=True
        )
        self.assertEqual(calls, ["start", "commit", "push"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_python_fallback_scan_failure_never_commits_or_pushes(self):
        secret = "synthetic-do-not-print-" + "x" * 43
        result, calls = self.run_pipeline({"token": secret}, python_fallback_only=True)
        self.assertEqual(calls, ["start"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("credential-valued field 'token'", result.stdout + result.stderr)
        self.assertIn("Evidence scan failed", result.stdout + result.stderr)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_shell_startup_path_cannot_bypass_git_interception(self):
        result, calls = self.run_pipeline(
            {"token": "[redacted]"}, rewrite_startup_path=True
        )
        self.assertEqual(calls, ["start", "commit", "push"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_mode_cannot_fall_through_to_push(self):
        result, calls = self.run_pipeline({}, mode="--unknown")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])
        self.assertIn("usage: publish_evidence.sh", result.stderr)


if __name__ == "__main__":
    unittest.main()
