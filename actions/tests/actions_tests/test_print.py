def test_print_result(datadir):
    from devutils.fixtures import actions_run

    args = [
        "run",
        "-a",
        "greet_fail_with_action_error",
        datadir,
        "--print-input",
        "--print-result",
    ]

    result = actions_run(args, returncode=1, cwd=str(datadir))
    output = result.stdout.decode("utf-8")
    assert "result:" in output
    assert '"result": null' in output
    assert '"error": "Sorry, this must fail."' in output
