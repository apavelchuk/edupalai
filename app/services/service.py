from time import perf_counter
from typing import Coroutine
from abc import ABC
from logging import Logger


class Service(ABC):
    def __init__(self, logger: Logger):
        self.logger = logger


def time_it(coroutine: Coroutine):
    async def inner_coro(*args, **kwargs):
        start_time = perf_counter()
        res = await coroutine(*args, **kwargs)
        end_time = perf_counter()
        approx_exec_time = round(end_time - start_time, 4)
        return approx_exec_time, res

    return inner_coro
