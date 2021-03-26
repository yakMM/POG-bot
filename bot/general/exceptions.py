"""Custom exceptions classes
"""

# Others:
from logging import getLogger

log = getLogger("pog_bot")


class UnexpectedError(Exception):
    def __init__(self, msg):
        self.reason = msg
        message = "Encountered unexpected error: " + msg
        log.error(message)
        super().__init__(message)
