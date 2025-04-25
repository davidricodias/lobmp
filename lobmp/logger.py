from __future__ import annotations

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from logging import (
    DEBUG,
    Formatter,
    Logger,
    LoggerAdapter,
    NullHandler,
    StreamHandler,
    getLogger,
)
from sys import stdout
from time import time
from types import TracebackType
from typing import Any

__author__ = "davidricodias"
__copyright__ = "davidricodias"
__license__ = "MIT"


package_logger = getLogger("lobmp")
package_logger.addHandler(
    NullHandler()
)  # By default start the logger pointing to the null handler, in essence doing nothing


def activate_logger() -> None:
    logFormatter = Formatter("%(asctime)s %(name)s [%(threadName)s] [%(levelname)s]  %(message)s")
    stream_handler = StreamHandler(stdout)  # Outputs to standard terminal
    stream_handler.setFormatter(logFormatter)
    if stream_handler not in package_logger.handlers:
        package_logger.removeHandler(NullHandler())
        package_logger.addHandler(stream_handler)


def get_logger() -> Logger:
    return package_logger


def set_logger_level(level: int | str) -> None:
    package_logger.setLevel(level)


# Custom logging class to enable both direct and context manager logging
class ContextLogger(LoggerAdapter):
    @contextmanager
    def timeit(self: ContextLogger, msg: str, level: int | str = DEBUG) -> Generator[Any, Any, Any]:
        self.logger.log(level, f"Started with timing: {msg}")
        try:
            start_time = time()
            yield
            elapsed_time = time() - start_time
            self.logger.log(level, f"Completed with timing: {msg} (Elapsed: {elapsed_time:.2f}s)")
        except Exception as e:
            self.logger.log(level, f"Error in {msg}: {e}", exc_info=True)
            raise e

    def debug(
        self: ContextLogger,
        msg: object,
        *args: object,
        exc_info: bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
        | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        self.logger.debug(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def info(
        self: ContextLogger,
        msg: object,
        *args: object,
        exc_info: bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
        | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        self.logger.info(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def warning(
        self: ContextLogger,
        msg: object,
        *args: object,
        exc_info: bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
        | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        self.logger.warning(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def error(
        self: ContextLogger,
        msg: object,
        *args: object,
        exc_info: bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
        | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        self.logger.error(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def critical(
        self: ContextLogger,
        msg: object,
        *args: object,
        exc_info: bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
        | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        self.logger.critical(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )


log = ContextLogger(get_logger(), {})

__all__ = ["log"]
