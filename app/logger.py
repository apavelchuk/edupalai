import logging

from time import perf_counter
from functools import lru_cache
from typing import Coroutine


class Logger:
    def __init__(self, name: str):
        self.writer = logging.getLogger(name)
        self.writer.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        self.writer.addHandler(handler)

    def log_error(self, message: str):
        self.writer.log(logging.ERROR, message)

    def log_debug(self, message: str):
        self.writer.log(logging.DEBUG, message)


@lru_cache
def logger_factory(name: str) -> Logger:
    return Logger(name)


def log_exec_time(func_description: str):
    def coro_wrap(coroutine: Coroutine):
        async def inner(*args, **kwargs):
            start_time = perf_counter()
            res = await coroutine(*args, **kwargs)
            end_time = perf_counter()
            logger: Logger = args[0].logger
            if logger:
                exec_time = end_time - start_time
                logger.log_debug(f"{func_description} executed in approx. {exec_time:.4f} sec.")
            return res

        return inner

    return coro_wrap
