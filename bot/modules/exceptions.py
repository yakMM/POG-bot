"""Custom exceptions classes
"""

# TODO: Implement proper logging?

# Others:
from logging import error
from datetime import datetime as dt
from datetime import timezone as tz

class CharNotFound(Exception):
    def __init__(self, char):
        self.char = char
        super().__init__(f"Character not found: {char}")

class CharInvalidWorld(Exception):
    def __init__(self, char):
        self.char = char
        super().__init__(f"Character in invalid world: {char}")

class CharAlreadyExists(Exception):
    def __init__(self, char, id):
        self.char = char
        self.id = id # id of player who already registered the char
        super().__init__(f"Character {char} is already registered!")

class AccountNotFound(Exception):
    def __init__(self, id):
        self.id = id
        super().__init__(f"Account not found in database: {id}")


class CharMissingFaction(Exception):
    def __init__(self, faction):
        self.faction = faction
        super().__init__(f"Can't find a character for faction: {faction}")

class UnexpectedError(Exception):
    def __init__(self, msg):
        self.message = "Encountered unexpected error: "+msg
        self.reason = msg
        date = dt.now(tz.utc)
        error(date.strftime("%Y-%m-%d %H:%M:%S %z ") + self.message)
        super().__init__(self.message)

class ConfigError(Exception):
    def __init__(self, msg):
        self.message = "Error in config file: "+msg
        super().__init__(self.message)

class DatabaseError(Exception):
    def __init__(self, msg):
        self.message = "Error in user database: "+msg
        super().__init__(self.message)

class StatusNotAllowed(Exception):
    def __init__(self, name):
        self.message = "This status is not allowed: "+name
        super().__init__(self.message)

class AccountsNotEnough(Exception):
    pass

class InvalidTag(Exception):
    def __init__(self, tag):
        self.tag = tag
        super().__init__(f"Invalid tag: {tag}")

class ElementNotFound(Exception):
    def __init__(self, id):
        self.id = id
        super().__init__(f"Element not found: {id}")

class AlreadyExists(Exception):
    def __init__(self, name):
        self.name = name
        super().__init__(f"Element already exists: {name}")

class LobbyStuck(Exception):
    def __init__(self):
        super().__init__(f"Lobby stuck!")