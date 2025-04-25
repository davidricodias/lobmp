# lobmp

Limit Order Book Message Processor is a Python package designed to transform raw lseg(aka Refinitiv) high frequency trading data into convinient formats such as parquet.

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
