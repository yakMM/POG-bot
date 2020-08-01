"""Custom enumerations classes to define status of the objects
"""

from enum import Enum

class MatchStatus(Enum):
    IS_FREE = "No match"
    IS_RUNNING = "Processing..."
    IS_PICKING = "Waiting for captains to pick players"
    IS_FACTION = "Waiting for factions to pick players"
    IS_MAPPING = "Waiting for map pick"
    IS_WAITING = "Waiting for teams"
    IS_STARTING = "Match starting"
    IS_PLAYING = "Match is being played"
    IS_RESULT = "Result"

class SelStatus(Enum):
    IS_EMPTY = 0
    IS_SELECTED = 1
    IS_SELECTION = 2
    IS_TOO_MUCH = 3
    IS_CONFIRMED = 4

class PlayerStatus(Enum):
    IS_NOT_REGISTERED = 0
    IS_REGISTERED = 1
    IS_LOBBIED = 2
    IS_MATCHED = 3
    IS_PICKED = 4
    IS_PLAYING = 5