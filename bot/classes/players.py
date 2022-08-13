# @CHECK 2.0 features OK

"""Contains player classes
"""
# Others

# Custom modules
import modules.config as cfg
from modules.asynchttp import api_request_and_retry as http_request, ApiNotReachable
from modules.tools import UnexpectedError
from lib.tasks import loop
from modules.roles import role_update
import modules.database as db
import modules.tools as tools
import re

from .stats import PlayerStat
from .scores import PlayerScore

from logging import getLogger
from datetime import datetime as dt

log = getLogger("pog_bot")

WORLD_ID = 19  # Jaeger ID




class CharNotFound(Exception):
    def __init__(self, char):
        self.char = char
        super().__init__(f"Character not found: {char}")


class CharInvalidWorld(Exception):
    def __init__(self, char):
        self.char = char
        super().__init__(f"Character in invalid world: {char}")


class CharAlreadyExists(Exception):
    def __init__(self, char, p):
        self.char = char
        self.player = p  # player who already registered the char
        super().__init__(f"Character {char} is already registered!")


class CharMissingFaction(Exception):
    def __init__(self, faction):
        self.faction = faction
        super().__init__(f"Can't find a character for faction: {faction}")


class Player:
    """ Basic player class, every registered user matches a Player object contained in the dictionary
    """

    _all_players = dict()
    # to store VS, NC and TR names to check for duplicates
    _names_checking = [dict(), dict(), dict()]

    @classmethod
    def get(cls, p_id):
        return cls._all_players.get(p_id)

    def remove(self):
        if self.__has_own_account:
            Player.name_check_remove(self)
        del Player._all_players[self.__id]

    @classmethod
    def get_all_players_list(cls):
        return cls._all_players.values()

    @classmethod
    def name_check_add(cls, p):
        for i in range(3):
            cls._names_checking[i][p.ig_ids[i]] = p

    @classmethod
    def name_check_remove(cls, p):
        for i in range(3):
            try:
                del cls._names_checking[i][p.ig_ids[i]]
            except KeyError:
                log.warning(f"name_check_remove KeyError for player [id={p.id}], [key={p.ig_ids[i]}]")

    def __init__(self, p_id, name):
        if not re.match(cfg.name_regex, name):
            name = "N/A"
        self.__name = name
        self.__id = p_id
        self.__ig_names = ["N/A", "N/A", "N/A"]
        self.__ig_ids = [0, 0, 0]
        self.__notify = False
        self.__dm = False
        self.__away = False
        self.__timeout = 0
        self.__is_registered = False
        self.__has_own_account = False
        self.__lobby_stamp = 0
        self.__lobby_expiration = 0
        self.__last_lobby_timeout = 0
        self.__active = None
        self.__match = None
        self.__stats = None
        Player._all_players[p_id] = self  # Add to dictionary on creation

    @classmethod
    def new_from_data(cls, data):  # make a new Player object from database data
        obj = cls(data["_id"], data["name"])
        obj.__name = data["name"]
        obj.__notify = data["notify"]
        obj.__is_registered = data["is_registered"]
        if "ig_ids" in data:
            obj.__has_own_account = True
            obj.__ig_names = data["ig_names"]
            obj.__ig_ids = data["ig_ids"]
            Player.name_check_add(obj)
        else:
            obj.__has_own_account = False
            obj.__ig_names = ["N/A", "N/A", "N/A"]
            obj.__ig_ids = [0, 0, 0]
        if "timeout" in data:
            obj.__timeout = data["timeout"]
        if "away" in data:
            obj.__away = data["away"]
        if "dm" in data:
            obj.__dm = data["dm"]
        return obj

    def get_data(self):  # get data for database push
        data = {"_id": self.__id, "name": self.__name, "notify": self.__notify, "is_registered": self.__is_registered}
        if self.__has_own_account:
            data["ig_names"] = self.__ig_names
            data["ig_ids"] = self.__ig_ids
        if self.__timeout != 0:
            data["timeout"] = self.__timeout
        if self.__away:
            data["away"] = self.__away
        if self.__dm:
            data["dm"] = self.__dm
        return data

    async def db_update(self, arg):
        if arg == "notify":
            await db.async_db_call(db.set_field, "users", self.id, {"notify": self.__notify})
        elif arg == "away":
            await db.async_db_call(db.set_field, "users", self.id, {"away": self.__away})
        elif arg == "dm":
            await db.async_db_call(db.set_field, "users", self.id, {"dm": self.__dm})
        elif arg == "register":
            doc = {"is_registered": self.__is_registered}
            await db.async_db_call(db.set_field, "users", self.id, doc)
        elif arg == "account":
            doc = {"ig_names": self.__ig_names, "ig_ids": self.__ig_ids}
            if self.__has_own_account:
                await db.async_db_call(db.set_field, "users", self.id, doc)
            else:
                await db.async_db_call(db.unset_field, "users", self.id, doc)
        elif arg == "timeout":
            await db.async_db_call(db.set_field, "users", self.id, {"timeout": self.__timeout})
        elif arg == "name":
            await db.async_db_call(db.set_field, "users", self.id, {"name": self.__name})
        else:
            raise UnexpectedError("db_update: Unknown field!")

    @property
    def active(self):  # "Active player" object, when player is in a match, contains more info
        return self.__active

    @property
    def name(self):
        return self.__name

    async def change_name(self, new_name):
        if not re.match(cfg.name_regex, new_name):
            return False
        self.__name = new_name
        await self.db_update("name")
        return True

    @property
    def timeout(self):
        return self.__timeout

    @timeout.setter
    def timeout(self, time):
        self.__timeout = time

    # TODO
    # DEV
    def cheat_name(self, name):
        self.__ig_names = [name, name, name]

    @property
    def is_timeout(self):
        return self.__timeout > tools.timestamp_now()

    @property
    def is_notify(self):
        return self.__notify

    @property
    def is_dm(self):
        return self.__dm

    @property
    def is_away(self):
        return self.__away

    @is_away.setter
    def is_away(self, value):
        self.__away = value

    @is_notify.setter
    def is_notify(self, value):
        self.__notify = value

    @is_dm.setter
    def is_dm(self, value):
        self.__dm = value

    @property
    def is_lobbied(self):
        return self.__lobby_stamp != 0

    @property
    def lobby_stamp(self):
        return self.__lobby_stamp

    @property
    def lobby_expiration(self):
        return self.__lobby_expiration

    @lobby_expiration.setter
    def lobby_expiration(self, value):
        self.__lobby_expiration = tools.timestamp_now() + value
        self.__last_lobby_timeout = value

    @property
    def should_be_warned(self):
        # If last timeout set is more than 1h30 (5400)
        if self.__last_lobby_timeout >= 5400:
            # And expiration is less than 10 minutes away (600)
            return tools.timestamp_now() + 600 >= self.__lobby_expiration
        return False

    @property
    def is_lobby_expired(self):
        return tools.timestamp_now() >= self.__lobby_expiration

    @property
    def lobby_remaining(self):
        diff_sec = self.__lobby_expiration - tools.timestamp_now()
        if diff_sec < 60:
            return "1min"
        diff_min = diff_sec // 60
        if diff_sec % 60 > 30:
            diff_min += 1
        diff_hours = diff_min // 60
        if diff_hours != 0:
            diff_min = diff_min - (diff_hours * 60)
            if diff_min:
                return f"{diff_hours}h{diff_min:02d}"
            else:
                return f"{diff_hours}h"
        else:
            return f"{diff_min}min"

    @property
    def stats(self):
        return self.__stats

    @property
    def id(self):
        return self.__id

    @property
    def mention(self):
        return f"<@{self.__id}>"

    @property
    def ig_names(self):
        return self.__ig_names

    @property
    def ig_ids(self):
        return self.__ig_ids

    @property
    def is_registered(self):
        return self.__is_registered

    @property
    def match(self):  # when in match
        return self.__match

    @property
    def has_own_account(self):
        return self.__has_own_account

    @property
    def accounts_flipped(self):
        accs = list()
        if not self.__has_own_account:
            return accs
        for i in range(3):
            if self.__ig_ids[i] == 0:
                accs.append(self.__ig_names[i])
        return accs

    def update_role(self):
        try:
            self.role_task.start()
        except RuntimeError:  # if task is already active
            log.warning(f"Player task conflict: {self.name}")

    @loop(count=1)
    async def role_task(self):
        await role_update(self)

    def on_lobby_leave(self):
        self.__lobby_stamp = 0
        self.__lobby_expiration = 0
        self.__last_lobby_timeout = 0
        self.update_role()

    def reset_lobby_expiration(self):
        self.lobby_expiration = 7200

    def on_lobby_add(self, expiration=0):
        self.__lobby_stamp = tools.timestamp_now()
        if expiration == 0:
            expiration = 7200
        self.__lobby_expiration = self.__lobby_stamp + expiration
        self.__last_lobby_timeout = expiration
        self.update_role()

    def on_player_clean(self):
        self.__match = None
        self.__active = None
        self.__stats = None
        if not self.__has_own_account:
            self.__ig_names = ["N/A", "N/A", "N/A"]
            self.__ig_ids = [0, 0, 0]
        self.update_role()

    def on_picked(self, active):
        self.__active = active

    async def on_match_selected(self, m):
        self.__match = m
        self.__lobby_stamp = 0
        self.__lobby_expiration = 0
        self.__last_lobby_timeout = 0
        self.__stats = await PlayerStat.get_from_database(self.__id, self.__name)

    def copy_ig_info(self, player):
        self.__ig_names = player.ig_names.copy()
        self.__ig_ids = player.ig_ids.copy()

    async def register(self, char_list: list) -> bool:
        """
        Register the player with char_list.

        :param char_list: List of character names to be added.
        :return: Whether there was an update in the player profile.
        :raise: UnexpectedError, when something unexpected happens.
        :raise: CharNotFound, when a character name is not found in the API.
        :raise: CharInvalidWorld, when a character doesn't belongs to Jaeger.
        :raise: CharAlreadyExists, when a character is already registered by another player
        :raise: CharMissingFaction, when no character was provided for one of the faction.
        """
        # If "no account"
        if char_list is None:
            if self.__has_own_account:
                # If player had an account, updated = True
                # Remove old chars from name check
                Player.name_check_remove(self)
                # "no account" data
                self.__ig_ids = [0, 0, 0]
                self.__ig_names = ["N/A", "N/A", "N/A"]
                self.__has_own_account = False
                await self.db_update("account")
                try:
                    await self.__match.give_account(self.active, update=True)
                except AttributeError:
                    pass
                return True
            elif not self.__is_registered:
                # If player was not registered, updated = True
                self.__is_registered = True
                await self.db_update("register")
                return True
            else:
                # Else updated = False
                return False
        else:
            # Else there are characters
            # If not updated, return
            if not await self._add_characters(char_list):
                return False
            else:
                if not self.__is_registered:
                    self.__is_registered = True
                    # Push to db
                    await self.db_update("register")
                else:
                    try:
                        await self.__match.try_remove_account(self.active, self.__match.objects, update=True)
                    except AttributeError:
                        pass
                # If updated
                await self.db_update("account")
                return True

    async def _add_characters(self, char_list: list) -> bool:
        """ Add Jaeger character names to the player.
            Check if characters are valid thanks to ps2 api.

            Parameters
            ----------
            char_list : list
                List of character names to be added.

            Raises
            ------
            UnexpectedError
                When something unexpected happens.
            CharNotFound
                When a character name is not found in the API.
            CharInvalidWorld
                When a character doesn't belongs to Jaeger.
            CharAlreadyExists
                When a character is already registered by another player.
            CharMissingFaction
                When no character was provided for one of the faction.

            Returns
            -------
            updated : bool
                Wether there was an update in the character names of the
                player.

        """

        # If something changed
        updated = False

        # If only 1 string, we add faction names
        if len(char_list) == 1:
            char_name = char_list[0]
            if char_name[-2::].lower() in ('vs', 'nc', 'tr'):
                char_name = char_name[:-2:]
            char_list = [char_name + 'VS', char_name + 'NC', char_name + 'TR']

        # Else it should be 3 strings
        if len(char_list) != 3:
            # Should not happen, we checked earlier
            raise UnexpectedError("char_list is not the good size!")

        # Intializing
        new_ids = [0, 0, 0]
        new_names = ["N/A", "N/A", "N/A"]

        for i_name in char_list:
            try:
                # Query API
                url = \
                    f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}' \
                    f'/get/ps2:v2/character/?name.first_lower={i_name.lower()}' \
                    f'&c:show=character_id,faction_id,name&c:resolve=world'
                j_data = await http_request(url)

                # Check if something returned
                if j_data["returned"] == 0:
                    raise CharNotFound(i_name)

                # Check char world
                try:
                    world = int(j_data["character_list"][0]["world_id"])
                except ValueError:
                    log.error(f'Received unexpected value for world_id: {j_data["character_list"][0]["world_id"]}')
                    raise ApiNotReachable(url)
                if world != WORLD_ID:
                    raise CharInvalidWorld(j_data["character_list"][0]["name"]["first"])

                # Get faction, id and name from API
                faction = int(j_data["character_list"][0]["faction_id"])
                curr_id = int(j_data["character_list"][0]["character_id"])
                curr_name = j_data["character_list"][0]["name"]["first"]

                # Check if the char is already registered:
                if curr_id in Player._names_checking[faction - 1]:
                    p = Player._names_checking[faction - 1][curr_id]
                    if p != self:
                        raise CharAlreadyExists(curr_name, p)

                # Add current id to new ids list
                new_ids[faction - 1] = curr_id

                # If it changed, updated=True
                updated = updated or new_ids[faction - 1] != self.__ig_ids[faction - 1]

                # Add current name to new names list
                new_names[faction - 1] = j_data["character_list"][0]["name"]["first"]
            except IndexError:
                # Should not happen, we checked earlier
                raise UnexpectedError(f'IndexError when setting player name: {i_name}')
            except KeyError:
                # Don't know when this should happen either
                raise UnexpectedError(f'KeyError when setting player name: {i_name}')

        # Check if user submitted one char per faction
        for i in range(3):
            if new_ids[i] == 0:
                raise CharMissingFaction(cfg.factions[i + 1])

        # If updated, we validate
        if updated:
            if self.__has_own_account:
                Player.name_check_remove(self)
            self.__ig_ids = new_ids.copy()
            self.__ig_names = new_names.copy()
            Player.name_check_add(self)
            self.__has_own_account = True

        return updated


class ActivePlayer:
    """ ActivePlayer class, with more data than Player class, for when match is happening
    """

    def __init__(self, player, team):
        self.__player = player
        self.__team = team
        self.__account = None
        self.__unique_usages = None
        self.__is_playing = False
        self.__match = player.match
        self.__player.on_picked(self)
        self.__player_score = None
        self.__is_benched = False

    @property
    def player_score(self):
        return self.__player_score

    @property
    def is_benched(self):
        return self.__is_benched

    @property
    def is_captain(self):
        return self.__team.is_captain(self)

    @property
    def is_turn(self):
        return self.__team.is_turn

    @is_turn.setter
    def is_turn(self, bl):
        self.__team.is_turn = bl

    @property
    def is_playing(self):
        return self.__is_playing

    @property
    def name(self):
        return self.__player.name

    @property
    def id(self):
        return self.__player.id

    @property
    def has_own_account(self):
        return self.__player.has_own_account

    @property
    def unique_usages(self):
        return self.__unique_usages

    @unique_usages.setter
    def unique_usages(self, value):
        self.__unique_usages = value

    @property
    def mention(self):
        return self.__player.mention

    @property
    def faction(self):
        return self.__team.faction

    @property
    def ig_id(self):
        faction = self.__team.faction
        if faction != 0:
            return self.__player.ig_ids[faction - 1]

    @property
    def ig_name(self):
        faction = self.__team.faction
        if faction != 0:
            return self.__player.ig_names[faction - 1]

    @property
    def account(self):
        return self.__account

    @account.setter
    def account(self, acc):
        self.__account = acc
        fake_player = Player.get(acc.id)
        if fake_player is None:
            log.fatal(f"Player object not found for account {acc.id}")
        else:
            self.__player.copy_ig_info(fake_player)

    @property
    def team(self):
        return self.__team

    @property
    def match(self):
        return self.__match

    def bench(self, bench):
        self.__is_benched = bench
        self.__team.on_player_bench(self)
        if self.__player_score:
            if bench:
                self.__player_score.disable()
            else:
                self.__player_score.enable()

    def clean(self, team_clean=False):
        if not team_clean and self.__player_score:
            self.__player_score.disable()
        self.__player.on_player_clean()

    def change_team(self, team):
        self.__team = team

    def on_team_ready(self, ready):
        self.__is_playing = ready

    def on_match_starting(self):
        team_score = self.team.team_score
        if self.__player_score and (self.__player_score.team is not team_score):
            self.__player_score.disable()
            self.__player_score = None
        if not self.__player_score and not self.__is_benched:
            self.__player_score = PlayerScore(self.id, team_score)
            self.__player_score.stats = self.__player.stats
            team_score.add_player(self.__player_score)
        if self.__player_score:
            self.__player_score.update(self.name, self.ig_name, self.ig_id)

    async def accept_account(self):
        account_id = self.__account.id
        if account_id not in self.__unique_usages:
            self.__unique_usages.append(account_id)
            try:
                await db.async_db_call(db.push_element, "accounts_usage", self.id,
                                                        {"unique_usages": account_id})
            except db.DatabaseError:
                pass
