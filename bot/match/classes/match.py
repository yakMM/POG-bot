from logging import getLogger
from lib.tasks import loop
from display.strings import AllStrings as disp

from classes import Base, Team
import modules.database as db
import modules.roles as roles
import modules.accounts_handler as accounts
from modules.tools import UnexpectedError

from match.processes import PlayerPicking, FactionPicking, BasePicking, GettingReady, MatchPlaying, CaptainSelection
from match.commands import CommandFactory
from match.match_status import MatchStatus

log = getLogger("pog_bot")


class Match:
    __bound_matches = dict()
    _last_match_id = 0

    @classmethod
    def get(cls, ch_id: int):
        if ch_id not in cls.__bound_matches:
            raise UnexpectedError(f"Can't find bound match {ch_id}")
        return cls.__bound_matches[ch_id]

    @classmethod
    def init_channels(cls, client, ch_list: list):
        for ch_id in ch_list:
            channel = client.get_channel(ch_id)
            instance = cls()
            instance.bind(channel)
            cls.__bound_matches[ch_id] = instance
        cls._last_match_id = db.get_field("restart_data", 0, "last_match_id")

    @classmethod
    def find_empty(cls):
        for match in cls.__bound_matches.values():
            if match.status is MatchStatus.IS_FREE:
                return match
        return None

    @classmethod
    async def get_from_database(cls, m_id: int):
        data = await db.async_db_call(db.get_element, "matches", m_id)
        instance = cls(data)
        return instance

    def __init__(self, data=None):
        self.__data = MatchData(self, data)
        self.__objects = None

    def bind(self, channel):
        self.__objects = MatchObjects(self, self.__data, channel)

    @property
    def channel(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound,\
                                  no attribute 'channel'")
        return self.__objects.channel

    @property
    def status(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status'")
        return self.__objects.status

    @property
    def next_status(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status'")
        return self.__objects.next_status

    @property
    def status_str(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status_str'")
        return self.__objects.status_str

    @property
    def id(self):
        return self.__data.id

    @property
    def teams(self):
        return self.__data.teams

    @property
    def round_no(self):
        return self.__data.round_no

    @property
    def base(self):
        return self.__data.base

    def change_check(self, arg):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'change_check'")
        if arg == "online":
            self.__objects.check_offline = not self.__objects.check_offline
            return self.__objects.check_offline
        elif arg == "account":
            self.__objects.check_validated = not self.__objects.check_validated
            return self.__objects.check_validated
        else:
            raise KeyError

    def spin_up(self, p_list):
        Match._last_match_id += 1
        self.__objects.on_spin_up(p_list)
        db.set_field("restart_data", 0, {"last_match_id": Match._last_match_id})

    @property
    def command(self):
        if not self.__objects:
            raise AttributeError(f"Match instance is not bound, no attribute 'command'")
        return self.__objects.command

    def __getattr__(self, name):
        if not self.__objects:
            raise AttributeError(f"Match instance is not bound, no attribute '{name}'")
        return self.__objects.get_process_attr(name)


class MatchData:
    def __init__(self, match: Match, data: dict):
        self.match = match
        if data:
            self.id = data["_id"]
            self.teams = [Team.from_data(self.match, 0, data["teams"][0]), Team.from_data(self.match, 1, data["teams"][1])]
            self.base = Base.get(data["base_id"])
            self.round_stamps = data["round_stamps"]
        else:
            self.id = 0
            self.teams = [None, None]
            self.base = None
            self.round_stamps = list()

    def clean(self):
        # Clean players if in teams
        for tm in self.teams:
            if tm is not None:
                tm.clean()

        self.id = 0
        self.teams = [None, None]
        self.base = None
        self.round_stamps = list()

    @property
    def round_no(self):
        if self.match.next_status is MatchStatus.IS_PLAYING:
            return len(self.round_stamps)
        if self.match.next_status in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING):
            return len(self.round_stamps) + 1
        return 0


_process_list = [CaptainSelection, PlayerPicking, FactionPicking, BasePicking, GettingReady, MatchPlaying]


class MatchObjects:
    def __init__(self, match: Match, data: MatchData, channel: int):
        self.__status = MatchStatus.IS_FREE
        self.data = data
        self.proxy = match
        self.channel = channel
        self.current_process = None
        self.base_selector = None
        self.progress_index = 0
        self.result_msg = None
        self.clean_channel.start()
        self.check_offline = True
        self.check_validated = True
        self.players_with_account = list()
        self.command_factory = CommandFactory(self)

    @property
    def status(self):
        return self.__status

    async def set_status(self, value):
        self.__status = value
        await self.match.command.on_status_update(value)

    async def next_process(self, *args):
        await self.set_status(MatchStatus.IS_RUNNING)
        self.progress_index += 1
        self.current_process = _process_list[self.progress_index](self, *args)

    def on_spin_up(self, p_list):
        self.data.id = Match._last_match_id
        self.current_process = _process_list[self.progress_index](self, p_list)

    @property
    def command(self):
        return self.command_factory

    def get_process_attr(self, name):
        if name in self.current_process.attributes:
            return self.current_process.attributes[name]
        else:
            raise AttributeError(f"Current process has no attribute '{name}'")

    async def clean(self):
        if self.base_selector:
            await self.base_selector.clean()
            self.base_selector = None
        for a_player in self.players_with_account:
            await accounts.terminate_account(a_player)
        self.data.clean()
        self.current_process = None
        self.players_with_account = list()
        self.result_msg = None
        self.check_offline = True
        self.check_validated = True
        await self.set_status(MatchStatus.IS_FREE)
        self.clean_channel.start()
        self.progress_index = 0

    @loop(count=1)
    async def clean_channel(self):
        await disp.MATCH_CHANNEL_OVER.send(self.channel)
        await roles.modify_match_channel(self.match.channel, view=False)

    @property
    def status_str(self):
        return self.next_status.value

    @property
    def next_status(self):
        if not self.current_process:
            return MatchStatus.IS_FREE
        else:
            return self.current_process.status

    def __getattr__(self, name):
        try:
            return getattr(self.data, name)
        except AttributeError:
            raise AttributeError(f"'MatchObjects' object has no attribute '{name}'")