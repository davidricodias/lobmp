from logging import NOTSET, _levelToName
from pathlib import Path

from lobmp import run, run_l10
from lobmp.logger import activate_logger, log, set_logger_level

__author__ = "davidricodias"
__copyright__ = "davidricodias"
__license__ = "MIT"


def main(filepath: str, targetdir: str, verbose: int | str = "NOTSET", format: str = "mbp") -> int:
    status: int = 0
    if verbose != _levelToName[NOTSET]:
        activate_logger()
        set_logger_level(verbose)

    input_file_path = Path(filepath)
    output_directory_path = (Path(targetdir) / input_file_path.stem).with_suffix(".parquet")

    if format == "l10":
        with log.timeit("Execute run_l10"):
            status = run_l10(input_file_path, output_directory_path)
    else:
        with log.timeit("Execute run"):
            status = run(input_file_path, output_directory_path)
    return status
