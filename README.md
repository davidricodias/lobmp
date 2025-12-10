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
- Supports LSEG (also known as Refinitiv) provider formats:
  - **Market By Price (MBP)**: Raw nested message format
  - **L10 (Normalized LL2)**: Level 10 market depth flat CSV format
- Outputs data in `part-*` Parquet format
- High-performance parallel processing using Rust
- Adjustable verbosity for logging

Please keep in mind this a package under development, so bugs are expected and functionality is not guaranteed to be 100% correct.

## Usage

```sh
lobmp <filepath> <targetdir> [--format FORMAT] [--verbose LEVEL]
```

Required Arguments

- `filepath`: Path to the CSV file to be processed.
- `targetdir`: Directory where the processed file will be saved.

Optional Arguments
- `--format`: Input file format. Choose from: `mbp` (Market By Price) or `l10` (L10/Normalized LL2). Default is `mbp`.
- `--verbose`: Logging level. Choose from: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` or `NOTSET` (default)

### Examples

**Process Market By Price (MBP) file:**
```sh
lobmp raw_messages.csv ./output --verbose DEBUG
```

**Process L10/Normalized LL2 file:**
```sh
lobmp euro_data.csv ./output --format l10 --verbose INFO
```

Will process the input file and output the processed messages in the `output` folder as partitioned Parquet files.

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
