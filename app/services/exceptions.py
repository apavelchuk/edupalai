from typing import Optional

from app.logger import Logger


class ServiceException(Exception):
    def __init__(self, message, logger: Optional[Logger] = None):
        if logger:
            logger.log_error(message)
        super().__init__(message)
