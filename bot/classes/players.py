# @CHECK 2.0 features OK

"""Contains player classes
"""
# Others

# Custom modules
import modules.config as cfg
from modules.asynchttp import api_request_and_retry as http_request, ApiNotReachable
from general.exceptions import UnexpectedError, ElementNotFound
from lib.tasks import loop
from modules.roles import role_update
import modules.database as db

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


class AccountNotFound(Exception):
    def __init__(self, id):
        self.id = id
        super().__init__(f"Account not found in database: {id}")





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

    def __init__(self, id, name):
        self.__name = name
        self.__id = id
        self.__ig_names = ["N/A", "N/A", "N/A"]
        self.__ig_ids = [0, 0, 0]
        self.__notify = False
        self.__timeout = 0
        self.__is_registered = False
        self.__has_own_account = False
        self.__lobby_stamp = 0
        self.__active = None
        self.__match = None
        Player._all_players[id] = self  # Add to dictionary on creation

    @classmethod
    def new_from_data(cls, data):  # make a new Player object from database data
        obj = cls(data["_id"], data["name"])
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
        return obj

    async def db_update(self, arg):
        if arg == "notify":
            await db.async_db_call(db.update_element, "users", self.id, {"notify": self.__notify})
        elif arg == "register":
            doc = {"is_registered": self.__is_registered}
            if self.__has_own_account:
                doc["ig_names"] = self.__ig_names
                doc["ig_ids"] = self.__ig_ids
            await db.async_db_call(db.update_element, "users", self.id, doc)
        elif arg == "timeout":
            if self.__timeout != 0:
                await db.async_db_call(db.update_element, "users", self.id, {"timeout": self.__timeout})
        elif arg == "name":
            await db.async_db_call(db.update_element, "users", self.id, {"name": self.__name})
        else:
            raise UnexpectedError("db_update: Unknown field!")

    @property
    def active(self):  # "Active player" object, when player is in a match, contains more info
        return self.__active

    @property
    def name(self):
        return self.__name

    async def change_name(self, new_name):
        self.__name = new_name
        await self.db_update("name")

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
        return self.__timeout > int(dt.timestamp(dt.now()))

    @property
    def is_notify(self):
        return self.__notify

    @is_notify.setter
    def is_notify(self, value):
        self.__notify = value
        self.update_role()

    @property
    def is_lobbied(self):
        return self.__lobby_stamp != 0

    @property
    def accounts_flipped(self):
        accs = list()
        if not self.__has_own_account:
            return accs
        for i in range(3):
            if self.__ig_ids[i] == 0:
                accs.append(self.__ig_names[i])
        return accs

    def update_role(self, i=0):
        try:
            self.role_task.start()
        except RuntimeError:  # if task is already active
            log.warning(f"Player task conflict: {self.name}")
            pass

    @loop(count=1)
    async def role_task(self):
        await role_update(self)

    def on_lobby_leave(self):
        self.__lobby_stamp = 0
        self.inactive_task.stop()
        self.update_role()

    def on_lobby_add(self):
        self.__lobby_stamp = int(dt.timestamp(dt.now()))
        self.update_role()

    def on_player_clean(self):
        self.__match = None
        self.__active = None
        if not self.__has_own_account:
            self.__ig_names = ["N/A", "N/A", "N/A"]
            self.__ig_ids = [0, 0, 0]
        self.update_role()

    def on_picked(self, active):
        self.__active = active

    def on_match_selected(self, m):
        self.__match = m
        self.inactive_task.cancel()

    def on_inactive(self, fct):
        if self.__lobby_stamp != 0:
            self.inactive_task.start(fct)

    def on_active(self):
        if self.__lobby_stamp != 0:
            self.inactive_task.cancel()

    def on_resign(self):
        self.__active = None

    @loop(minutes=cfg.AFK_TIME, delay=1, count=2)
    async def inactive_task(self, fct):  # when inactive for cfg.AFK_TIME, execute fct
        await fct(self)

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

    def copy_ig_info(self, player):
        self.__ig_names = player.ig_names.copy()
        self.__ig_ids = player.ig_ids.copy()

    def get_data(self):  # get data for database push
        data = {"_id": self.__id, "name": self.__name, "notify": self.__notify, "is_registered": self.__is_registered}
        if self.__has_own_account:
            data["ig_names"] = self.__ig_names
            data["ig_ids"] = self.__ig_ids
        if self.__timeout != 0:
            data["timeout"] = self.__timeout
        return data

    async def register(self, char_list: list) -> bool:
        """ Register the player with char_list.

            Parameters
            ----------
            char_list : list
                List of character names to be added.

            Raises
            ------
            Check _add_characters.

            Returns
            -------
            updated : bool
                Wether there was an update in the player profile.

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
                await self.db_update("register")
                try:
                    await self.__match.give_account(self.active)
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
                # Push to db
                await self.db_update("register")

                # If updated
                if not self.__is_registered:
                    self.__is_registered = True
                else:
                    try:
                        await self.__match.remove_account(self.active)
                    except AttributeError:
                        pass
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
            char_list = [char_list[0] + 'VS', char_list[0] + 'NC', char_list[0] + 'TR']

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
                    # TODO: test, uncomment this
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


class DataPlayer:

    def __init__(self, p_id, ig_name, ig_id):
        self.id = p_id
        self.ig_names = [ig_name] * 3
        self.ig_ids = [ig_id] * 3


class ActivePlayer:
    """ ActivePlayer class, with more data than Player class, for when match is happening
    """

    def __init__(self, player, team, from_data=False):
        self.__player = player
        self.__illegal_weapons = dict()
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__team = team
        self.__account = None
        self.__unique_usages = None
        self.__is_playing = False
        if from_data:
            return
        self.__player.on_picked(self)

    @classmethod
    def new_from_data(cls, data, team):
        try:
            ig_name = data["ig_name"]
        except KeyError:
            ig_name = "N/A"
        pl = DataPlayer(data["discord_id"], ig_name, data["ig_id"])
        obj = cls(pl, team, from_data=True)
        obj.__score = data["score"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__ill_weapons_fromData(data["ill_weapons"])
        return obj

    def clean(self):
        self.__player.on_player_clean()

    def get_data(self):
        data = {"discord_id": self.__player.id,
                "ig_id": self.ig_id,
                "ig_name": self.ig_name,
                "ill_weapons": self.__get_ill_weaponsDoc(),
                "score": self.__score,
                "net": self.__net,
                "deaths": self.__deaths,
                "kills": self.__kills,
                }
        return data

    def __get_ill_weaponsDoc(self):
        data = list()
        for weap_id in self.__illegal_weapons.keys():
            doc = {"weap_id": weap_id,
                   "kills": self.__illegal_weapons[weap_id]
                   }
            data.append(doc)
        return data

    def __ill_weapons_fromData(self, data):
        for weap_doc in data:
            self.__illegal_weapons[weap_doc["weap_id"]] = weap_doc["kills"]

    @property
    def is_captain(self):
        return False

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

    async def accept_account(self):
        account_id = self.__account.id
        if account_id not in self.__unique_usages:
            self.__unique_usages.append(account_id)
            try:
                await db.async_db_call(db.push_element, "accounts_usage", self.id,
                                                        {"unique_usages": account_id})
            except db.DatabaseError:
                pass
        fake_player = Player.get(account_id)
        if fake_player is None:
            raise AccountNotFound(account_id)
        self.__player.copy_ig_info(fake_player)

    def on_resign(self):
        self.__player.on_resign()
        return self.__player

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

    @property
    def team(self):
        return self.__team

    @property
    def match(self):
        return self.__player.match

    @property
    def kills(self):
        return self.__kills

    @property
    def deaths(self):
        return self.__deaths

    @property
    def score(self):
        return self.__score

    @property
    def net(self):
        return self.__net

    @property
    def illegal_weapons(self):
        return self.__illegal_weapons

    def on_team_ready(self, ready):
        self.__is_playing = ready

    def add_illegal_weapon(self, weap_id):
        if weap_id in self.__illegal_weapons:
            self.__illegal_weapons[weap_id] += 1
        else:
            self.__illegal_weapons[weap_id] = 1

    def add_one_kill(self, points):
        self.__kills += 1
        self.__team.add_one_kill()
        self.__add_points(points)

    def add_one_death(self, points):
        self.__deaths += 1
        self.__team.add_one_death()
        points = -points
        self.__net += points
        self.__team.add_net(points)

    def add_one_t_k(self):
        self.__add_points(cfg.scores["teamkill"])

    def add_one_suicide(self):
        self.__deaths += 1
        self.__team.add_one_death()
        self.__add_points(cfg.scores["suicide"])

    def __add_points(self, points):
        self.__net += points
        self.__score += points
        self.__team.add_score(points)
        self.__team.add_net(points)


class TeamCaptain(ActivePlayer):
    """ Team Captain variant of the active player
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.__is_turn = False

    @property
    def is_captain(self):
        return True

    @property
    def is_turn(self):
        return self.__is_turn

    @is_turn.setter
    def is_turn(self, bool):
        self.__is_turn = bool
