"""
Command Line Interface Module
=================

This module provides functionality to let users call the message processor using a command
line interface.

The `cli` module implements an `argparse` with the follwing flags:
- `--filepath <path>`: path of the file to be processed.
- `--provider <str>`: provider of the data to be processed. Currently *only supports lseg*.

Example:
```
lobmp --filepath download_1.csv
```

Author: davidricodias
"""

from argparse import ArgumentParser
from sys import argv, exit, stderr

from lobmp.main import main

__author__ = "davidricodias"
__copyright__ = "davidricodias"
__license__ = "MIT"


def cli() -> int:
    parser = ArgumentParser(description="Limit Order Book Messages Processor")
    parser.add_argument("filepath", help="Path to the input file.", type=str)
    parser.add_argument("targetdir", help="Directory for the processed data.", type=str)
    parser.add_argument(
        "--verbose",
        default="NOTSET",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
        help="Level of logging desired. Default is NOTSET, which is no logging.",
        type=str,
    )

    # Show help if no arguments are provided
    if len(argv) == 1:
        parser.print_help(stderr)
        exit(1)

    args = parser.parse_args()
    return main(args.filepath, args.targetdir, args.verbose)


if __name__ == "__main__":
    cli()
