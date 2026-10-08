"""Keep public generic-alias documentation stable across supported Pythons."""

import argparse
import importlib
import re
from pathlib import Path
from types import GenericAlias


def normalize_generic_alias_docs(output: Path, package_name: str) -> None:
    module = importlib.import_module(package_name)
    aliases = {
        name: value.__origin__.__name__
        for name in getattr(module, "__all__", ())
        if isinstance(value := getattr(module, name), GenericAlias)
    }
    if not aliases:
        return
    module_path = output / f"{package_name}.md"
    text = module_path.read_text()
    overview_path = output / "README.md"
    overview = overview_path.read_text()
    for name, origin in aliases.items():
        # Python 3.10 inspect.isclass treats GenericAlias as its origin class;
        # later versions render the same public alias as a variable.
        text = re.sub(
            rf"\n# Class `{re.escape(origin)}`\n.*?(?=\n# |\Z)",
            "",
            text,
            flags=re.S,
        )
        overview = "\n".join(
            line
            for line in overview.split("\n")
            if f"[`builtins.{origin}`]" not in line
        )
        entry = f"- **{name}**"
        if entry not in text:
            marker = "# Variables\n\n"
            if marker not in text:
                raise ValueError("Generated API guide lacks Variables section")
            text = text.replace(marker, marker + entry + "\n", 1)
    module_path.write_text(text)
    overview_path.write_text(overview)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    normalize_generic_alias_docs(args.output, args.package)
