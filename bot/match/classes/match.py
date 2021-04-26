from logging import getLogger
from lib.tasks import loop
from display.strings import AllStrings as disp

from classes import Base, Team, TeamScore
import modules.database as db
import modules.roles as roles
import modules.config as cfg
import modules.accounts_handler as accounts
from modules.tools import UnexpectedError
import modules.lobby as lobby

from match.processes import *
from match.commands import CommandFactory
from match.match_status import MatchStatus
from .base_selector import on_match_over
from match.plugins.manager import PluginManager

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

    # TODO: dev, remove
    @property
    def data(self):
        return self.__data

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
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'teams'")
        return self.__objects.teams

    @property
    def round_no(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'round_no'")
        return self.__objects.round_no

    @property
    def base(self):
        return self.__data.base

    @property
    def round_stamps(self):
        return self.__data.round_stamps

    @property
    def round_length(self):
        return self.__data.round_length

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
            self.teams = [TeamScore.from_data(0, match, data["teams"][0]),
                          TeamScore.from_data(1, match, data["teams"][1])]
            self.base = Base.get(data["base_id"])
            self.round_length = data["round_length"]
            self.round_stamps = data["round_stamps"]
        else:
            self.id = 0
            self.teams = [None, None]
            self.base = None
            self.round_length = cfg.general["round_length"]
            self.round_stamps = list()

    def get_data(self):
        dta = dict()
        dta["_id"] = self.id
        dta["round_stamps"] = self.round_stamps
        dta["round_length"] = self.round_length
        dta["base_id"] = self.base.id
        dta["teams"] = [tm.get_data() for tm in self.teams]
        return dta

    def clean(self):
        self.id = 0
        self.teams = [None, None]
        self.base = None
        self.round_stamps = list()

    async def push_db(self):
        await db.async_db_call(db.set_element, "matches", self.id, self.get_data())
        for tm in self.teams:
            for p in tm.players:
                await p.db_update_stats()


_process_list = [CaptainSelection, PlayerPicking, FactionPicking, BasePicking, GettingReady, MatchPlaying,
                 GettingReady, MatchPlaying]


class MatchObjects:
    def __init__(self, match: Match, data: MatchData, channel: int):
        self.__status = MatchStatus.IS_FREE
        self.data = data
        self.proxy = match
        self.teams = [None, None]
        self.channel = channel
        self.current_process = None
        self.base_selector = None
        self.progress_index = 0
        self.result_msg = None
        self.check_offline = True
        self.check_validated = True
        self.players_with_account = list()
        self.command_factory = CommandFactory(self)
        self.plugin_manager = PluginManager(self)
        self.clean_channel.start(display=False)

    @property
    def status(self):
        return self.__status

    @property
    def round_no(self):
        if self.next_status in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING):
            return len(self.data.round_stamps) + 1
        else:
            return len(self.data.round_stamps)

    @property
    def last_start_stamp(self):
        return self.data.round_stamps[-1]

    @status.setter
    def status(self, value):
        self.__status = value
        if self.__status is not MatchStatus.IS_RUNNING:
            self.command_factory.on_status_update(value)

    def ready_next_process(self, *args):
        self.status = MatchStatus.IS_RUNNING
        if self.progress_index == len(_process_list):
            self.current_process = None
            self.plugin_manager.on_match_over()
            self.clean_critical()
        else:
            self.current_process = _process_list[self.progress_index](self, *args)
        self.progress_index += 1

    def start_next_process(self):
        if self.current_process:
            self.current_process.initialize()
        else:
            self.match_over_loop.start()

    def on_spin_up(self, p_list):
        self.data.id = Match._last_match_id
        self.ready_next_process(p_list)
        self.clean_channel.cancel()
        self.plugin_manager.on_match_launching()
        self.start_next_process()

    @loop(count=1)
    async def match_over_loop(self):
        await disp.MATCH_OVER.send(self.match.channel)
        await self.data.push_db()
        await self.clean_async()
        await disp.MATCH_CLEARED.send(self.match.channel)

    @property
    def command(self):
        return self.command_factory

    def get_process_attr(self, name):
        if name in self.current_process.attributes:
            return self.current_process.attributes[name]
        else:
            raise AttributeError(f"Current process has no attribute '{name}'")

    def clean_critical(self):
        self.status = MatchStatus.IS_RUNNING
        self.command_factory.on_clean()
        if self.base_selector:
            self.base_selector.clean()
            self.base_selector = None
        for tm in self.teams:
            if tm is not None:
                tm.clean()
        self.teams = [None, None]
        self.current_process = None

    async def clean_all_auto(self):
        self.clean_critical()
        await self.clean_async()

    async def clean_async(self):
        await self.plugin_manager.clean()
        on_match_over(self.data.id)
        for a_player in self.players_with_account:
            await accounts.terminate_account(a_player)
        self.data.clean()
        self.players_with_account = list()
        self.result_msg = None
        self.check_offline = True
        self.check_validated = True
        self.clean_channel.change_interval(minutes=2)
        self.clean_channel.start(display=True)
        self.progress_index = 0
        self.status = MatchStatus.IS_FREE
        lobby.on_match_free()

    @loop(count=2, delay=1)
    async def clean_channel(self, display):
        if display:
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
