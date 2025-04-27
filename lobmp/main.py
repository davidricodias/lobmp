from logging import NOTSET, _levelToName
from pathlib import Path

from lobmp import run
from lobmp.logger import activate_logger, log, set_logger_level

__author__ = "davidricodias"
__copyright__ = "davidricodias"
__license__ = "MIT"


def main(filepath: str, targetdir: str, verbose: int | str = "NOTSET") -> int:
    status: int = 0
    if verbose != _levelToName[NOTSET]:
        activate_logger()
        set_logger_level(verbose)

    input_file_path = Path(filepath)
    output_directory_path = (Path(targetdir) / input_file_path.stem).with_suffix(".parquet")

    with log.timeit("Execute run"):
        status = run(input_file_path, output_directory_path)
    return status
