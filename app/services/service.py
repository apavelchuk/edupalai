from abc import ABC
from logging import Logger


class Service(ABC):
    def __init__(self, logger: Logger):
        self.logger = logger
