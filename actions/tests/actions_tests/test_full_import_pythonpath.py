def _fix_file(entry):
    import os.path

    entry["file"] = os.path.basename(entry["file"])


def test_actions_list_relative_import(datadir, data_regression):
    import json

    from devutils.fixtures import actions_run

    result = actions_run(["list", "--skip-lint"], returncode=0, cwd=str(datadir))
    found = json.loads(result.stdout)
    print(result.stderr.decode("utf-8"))
    for entry in found:
        _fix_file(entry)
    data_regression.check(
        sorted(found, key=lambda entry: (entry["name"], entry["line"]))
    )


def test_actions_run_relative_import(datadir, data_regression):
    from devutils.fixtures import actions_run

    # Just check that it runs.
    actions_run(["run", "-a", "my_action"], returncode=0, cwd=str(datadir))
