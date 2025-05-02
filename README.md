|    |    |
| --- | --- |
| CI/CD | [![Build Status](https://github.com/davidricodias/lobmp/actions/workflows/pypi_publish.yml/badge.svg)](https://github.com/davidricodias/lobmp/actions/workflows/pypi_publish.yml) [![Test Status](https://github.com/davidricodias/lobmp/actions/workflows/testing.yml/badge.svg)](https://github.com/davidricodias/lobmp/actions/workflows/testing.yml) |
| Latest release | [![Github release](https://img.shields.io/github/release/davidricodias/lobmp.svg?label=tag&colorB=11ccbb)](https://github.com/davidricodias/lobmp/releases) [![PyPI version](https://img.shields.io/pypi/v/lobmp.svg?colorB=cc77dd)](https://pypi.python.org/pypi/lobmp) |
| Python | [![Python support](https://img.shields.io/pypi/pyversions/lobmp.svg)](https://pypi.org/project/lobmp/) [![PyPI Downloads](https://static.pepy.tech/badge/lobmp)](https://pepy.tech/projects/lobmp) |
| Docs | [![gh-pages](https://img.shields.io/github/last-commit/davidricodias/lobmp/gh-pages.svg)](https://github.com/davidricodias/lobmp/tree/gh-pages) |

# lobmp

Limit Order Book Message Processor is a Python package designed to transform raw lseg(aka Refinitiv) high frequency trading data into convenient formats such as parquet.

## Install
The package is available through PyPi
```sh
pip install --upgrade lobmp
```

## Features
The package is intended to be used as a Command Line Interface (CLI) program. The main features are
- CLI for processing message files
- Supports LSEG (also known as Refinitiv) provider (with potential for future expansion)
- Outputs data in `part-*` Parquet format
- Adjustable verbosity for logging

Please keep in mind this a package under development, so bugs are expected and functionality is not guaranteed to be 100% correct.

## Usage
```sh
lobmp <filepath> <targetdir> [--verbose LEVEL]
```
Required Arguments
- `filepath`: Path to the CSV file to be processed.
- `targetdir`: Directory where the processed file will be saved.
Optional Arguments
- `--verbose`: Logging level. Choose from: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` or `NOTSET` (default)

For example
```sh
lobmp raw_messages.csv ./output --verbose DEBUG
```
Will process the `raw_messages.csv` file and output the processed messages in the `output` folder.

## Contributing
Please fork the project and clone it into your computer. Then install the required dependencies:
```sh
python -m venv .venv
```
```sh
. .venv/bin/activate
```
```sh
uv lock
```
```sh
just develop
```
```sh
pre-commit install
```
```sh
rustup component add llvm-tools-preview
```
```sh
cargo install cargo-llvm-cov
```
