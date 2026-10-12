"""Run package-local Poetry through the repository's RCC environment boundary."""
import importlib.util
import sys
from pathlib import Path

root = Path('/workspace/actions')
spec = importlib.util.spec_from_file_location('actions_toolkit', root / 'developer/toolkit.py')
toolkit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolkit)
package, *arguments = sys.argv[1:]
if package not in toolkit.PACKAGES or not arguments:
    raise SystemExit('usage: package-command.py PACKAGE POETRY_ARGUMENTS...')
toolkit.poetry(package, *arguments)
