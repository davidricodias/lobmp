from pathlib import Path

from polars import DataFrame

def find_market_by_price_lines(path: Path) -> list: ...
def flatten_map_entry(map_entry: str) -> list[list]: ...
def flatten_market_by_price(market_by_price: str) -> DataFrame: ...
def run(input_file: Path, output_directory: Path) -> bool: ...
