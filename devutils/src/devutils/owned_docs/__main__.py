"""Command-line entrypoint for owned documentation tooling."""

import argparse

from . import generate_docs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--no-watermark", action="store_true")
    parser.add_argument("--remove-package-prefix", action="store_true")
    parser.add_argument("--src-base-url")
    parser.add_argument("--src-root-path")
    parser.add_argument("--overview-file")
    parser.add_argument("--output-path", default="./docs")
    args = vars(parser.parse_args())
    args["watermark"] = not args.pop("no_watermark")
    generate_docs(**args)


if __name__ == "__main__":
    main()
