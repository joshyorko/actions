"""Exercise Git's actual checkout conversion for Runtime distribution inputs."""

import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).parents[2]
RULES = (
    "action_server/src/**/*.py text eol=lf",
    "action_server/frontend/apps/runtime/index.html text eol=lf",
    "action_server/src/actions/server/README.md text eol=lf",
    "action_server/src/actions/server/bin/.gitignore text eol=lf",
    "action_server/src/actions/server/index.html text eol=lf",
    "action_server/src/actions/server/templates/action-templates.yaml text eol=lf",
    "action_server/src/actions/server/vendored_deps/README.md text eol=lf",
)
TEXT_PATHS = tuple(rule.split()[0] for rule in RULES[1:])


def git(repository, *arguments, **kwargs):
    environment = os.environ.copy()
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    ).stdout


def source_inputs():
    entries = {}
    for record in git(ROOT, "ls-tree", "-rz", "HEAD", "action_server/src").split(b"\0"):
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        path = path_bytes.decode()
        if kind == "blob" and (path.endswith(".py") or path in TEXT_PATHS):
            entries[path] = (mode, blob)
    for path in TEXT_PATHS:
        if path not in entries:
            mode, kind, blob = (
                git(ROOT, "ls-tree", "HEAD", "--", path).decode().split()[:3]
            )
            assert kind == "blob"
            entries[path] = (mode, blob)
    return {
        path: (mode, git(ROOT, "cat-file", "blob", blob))
        for path, (mode, blob) in entries.items()
    }


@contextmanager
def checkout(inputs, attributes, autocrlf):
    """Index exact blobs without clean filters, then apply real checkout filters."""
    with tempfile.TemporaryDirectory(prefix="runtime-checkout-") as directory:
        repository = Path(directory)
        git(repository, "init", "--quiet")
        git(repository, "config", "core.autocrlf", str(autocrlf).lower())
        git(repository, "config", "core.safecrlf", "false")
        bodies = dict(inputs, **{".gitattributes": ("100644", attributes)})
        for path, (_, body) in bodies.items():
            target = repository / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        paths = list(bodies)
        blobs = (
            git(
                repository,
                "hash-object",
                "--no-filters",
                "-w",
                "--stdin-paths",
                input="".join(path + "\n" for path in paths).encode(),
            )
            .decode()
            .splitlines()
        )
        assert len(blobs) == len(paths)
        index = "".join(
            "{} {}\t{}\n".format(bodies[path][0], blob, path)
            for path, blob in zip(paths, blobs)
        )
        git(repository, "update-index", "--index-info", input=index.encode())
        actual_modes = {
            entry.split(b"\t")[1].decode(): entry.split()[0].decode()
            for entry in git(repository, "ls-files", "--stage", "-z").split(b"\0")
            if entry
        }
        assert actual_modes == {path: mode for path, (mode, _) in bodies.items()}
        git(repository, "checkout-index", "--all", "--force")
        yield repository


class RuntimeCheckoutBytesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = source_inputs()
        cls.attributes = (ROOT / ".gitattributes").read_bytes()
        cls.baseline = b"\n".join(
            line for line in cls.attributes.split(b"\n") if line.decode() not in RULES
        )

    def assert_exact_inputs(self, repository, paths=None):
        differences = [
            path
            for path in (paths if paths is not None else self.inputs)
            if (repository / path).read_bytes() != self.inputs[path][1]
        ]
        self.assertEqual(differences, [], "Git checkout changed selected input bytes")

    def test_all_selected_inputs_are_exact_under_both_checkout_settings(self):
        for setting in (True, False):
            with self.subTest(autocrlf=setting):
                with checkout(self.inputs, self.attributes, setting) as repository:
                    self.assert_exact_inputs(repository)
                    attributes = (
                        git(
                            repository,
                            "check-attr",
                            "--stdin",
                            "eol",
                            input="\n".join(self.inputs).encode(),
                        )
                        .decode()
                        .splitlines()
                    )
                    self.assertEqual(len(attributes), len(self.inputs))
                    self.assertTrue(
                        all(line.endswith(": eol: lf") for line in attributes)
                    )

    def test_old_policy_reproduces_selected_text_conversion(self):
        with checkout(self.inputs, self.baseline, True) as repository:
            for path in TEXT_PATHS:
                with self.subTest(path=path):
                    self.assertNotEqual(
                        (repository / path).read_bytes(), self.inputs[path][1]
                    )
            python = "action_server/src/actions/server/_actions_run.py"
            self.assertNotEqual(
                (repository / python).read_bytes(), self.inputs[python][1]
            )

    def test_each_independent_rule_removal_breaks_valid_byte_parity(self):
        with checkout(self.inputs, self.attributes, True) as repository:
            self.assert_exact_inputs(repository)
        for rule in RULES:
            with self.subTest(removed_rule=rule):
                self.assertIn(rule.encode(), self.attributes.splitlines())
                poisoned = b"\n".join(
                    line
                    for line in self.attributes.split(b"\n")
                    if line != rule.encode()
                )
                affected = (
                    ["action_server/src/actions/server/_actions_run.py"]
                    if rule == RULES[0]
                    else [rule.split()[0]]
                )
                with checkout(self.inputs, poisoned, True) as repository:
                    with self.assertRaises(AssertionError):
                        self.assert_exact_inputs(repository, affected)

    def test_unrelated_binary_platform_fixtures_and_packages_keep_their_policy(self):
        archives = (
            git(ROOT, "ls-tree", "-r", "--name-only", "HEAD", "action_server/src")
            .decode()
            .splitlines()
        )
        protected = {
            path: ("100644", git(ROOT, "show", "HEAD:" + path))
            for path in archives
            if path.endswith(".zip")
        }
        binary_paths = list(protected)
        self.assertTrue(binary_paths)
        protected.update(
            {
                "unrelated/windows.bat": ("100644", b"@echo off\r\necho fixture\r\n"),
                "action_server/tests/intentional-crlf.dat": (
                    "100644",
                    b"literal\r\nfixture\r\n",
                ),
                "actions/src/actions/unrelated.py": ("100644", b"value = 1\n"),
                "action_server/tests/unrelated.py": ("100644", b"value = 2\n"),
            }
        )
        for setting in (True, False):
            with self.subTest(autocrlf=setting):
                with checkout(protected, self.baseline, setting) as old:
                    old_bodies = {path: (old / path).read_bytes() for path in protected}
                    old_attributes = git(old, "check-attr", "--all", "--", *protected)
                with checkout(protected, self.attributes, setting) as new:
                    self.assertEqual(
                        old_bodies,
                        {path: (new / path).read_bytes() for path in protected},
                    )
                    self.assertEqual(
                        old_attributes,
                        git(new, "check-attr", "--all", "--", *protected),
                    )
                    for binary in binary_paths:
                        self.assertEqual(
                            (new / binary).read_bytes(), protected[binary][1]
                        )


if __name__ == "__main__":
    unittest.main()
