import modules.config as cfg
from display import SendCtx, send
from match_process import MatchStatus, SelStatus
from modules.image_maker import publish_match_image
from modules.census import process_score, get_offline_players
from modules.database import update_match
from datetime import datetime as dt, timezone as tz
from modules.ts_interface import AudioBot

from classes.teams import Team  # ok
from classes.players import TeamCaptain  # ok
from classes.bases import MapSelection, bases_pool  # ok
from classes.accounts import AccountHander  # ok

from random import choice as random_choice
from lib.tasks import loop
from asyncio import sleep
from logging import getLogger

# THIS IS LEGACY CODE, WILL BE REMOVED IN A NEAR UPDATE


class Match():

    def __init__(self, m_id, ch, from_data = False):
        self.__id = m_id
        self.__players = dict()
        self.__teams = [None, None]
        self.__base_selector = None
        self.__result_msg = None
        _all_matches[m_id] = self
        self.__accounts = None
        self.__round_stamps = list()
        if from_data:
            self.__number = m_id
            return
        self.__number = 0
        self.__status = MatchStatus.IS_FREE
        self.__channel = ch
        self.__audio_bot = AudioBot(self)

    @classmethod
    def new_from_data(cls, data):
        obj = cls(data["_id"], None, from_data=True)
        obj.__round_stamps = data["round_stamps"]
        obj.__base_selector = MapSelection.new_from_id(obj, data["base_id"])
        for i in range(len(data["teams"])):
            obj.__teams[i] = Team.new_from_data(i, data["teams"][i], obj)
        return obj

    @property
    def channel(self):
        return self.__channel

    @property
    def msg(self):
        return self.__result_msg

    @property
    def status(self):
        return self.__status

    @property
    def id(self):
        return self.__id

    @property
    def teams(self):
        return self.__teams

    @property
    def status_string(self):
        return self.__status.value

    @property
    def number(self):
        return self.__number

    @number.setter
    def number(self, num):
        self.__number = num

    @property
    def player_pings(self):
        pings = [p.mention for p in self.__players.values()]
        return pings

    @property
    def seconds_to_round_end(self):
        time_delta = self._on_match_over.next_iteration - dt.now(tz.utc)
        return int(time_delta.total_seconds())

    @property
    def formated_time_to_round_end(self):
        secs = self.seconds_to_round_end
        return f"{secs//60}m {secs%60}s"

    def get_data(self):
        teams_data = list()
        for tm in self.__teams:
            teams_data.append(tm.get_data())
        data = {"_id": self.__number,
                "round_stamps": self.__round_stamps,
                "round_length": cfg.general['round_length'],
                "base_id": self.__base_selector.base.id,
                "teams": teams_data
                }
        return data


    # def _set_player_list(self, p_list):
    #     self.__status = MatchStatus.IS_RUNNING
    #     for p in p_list:
    #         self.__players[p.id] = p

    # def pick(self, team, player):
    #     team.add_player(ActivePlayer, player)
    #     self.__players.pop(player.id)
    #     team.captain.is_turn = False
    #     other = self.__teams[team.id - 1]
    #     other.captain.is_turn = True
    #     if len(self.__players) == 1:
    #         # Auto pick last player
    #         p = [*self.__players.values()][0]
    #         self.__ping_last_player.start(other, p)
    #         return self.pick(other, p)
    #     if len(self.__players) == 0:
    #         self.__status = MatchStatus.IS_FACTION
    #         self.__teams[1].captain.is_turn = True
    #         self.__teams[0].captain.is_turn = False
    #         picker = self.__teams[1].captain
    #         self.__player_pick_over.start(picker)
    #         return self.__teams[1].captain
    #     return other.captain

    # def confirm_base(self):
    #     self.__base_selector.confirm()
    #     self.__audio_bot.base_selected(self.__base_selector.base)
    #     if self.__status is MatchStatus.IS_BASING:
    #         self.__ready.start()
    #
    # def pick_base(self, captain):
    #     captain.is_turn = False
    #     other = self.__teams[captain.team.id - 1]
    #     other.captain.is_turn = True
    #     return other.captain

    # def resign(self, captain):
    #     team = captain.team
    #     if team.is_players:
    #         return False
    #     else:
    #         player = captain.on_resign()
    #         key = random_choice(list(self.__players))
    #         self.__players[player.id] = player
    #         team.clear()
    #         team.add_player(TeamCaptain, self.__players.pop(key))
    #         team.captain.is_turn = captain.is_turn
    #         return True

    # @loop(count=1)
    # async def __ping_last_player(self, team, p):
    #     await send("PK_LAST", self.__channel, p.mention, team.name)

    # @loop(count=1)
    # async def __player_pick_over(self, picker):
    #     self.__audio_bot.select_factions()
    #     msg = await send("PK_OK_FACTION", self.__channel, picker.mention, match=self)

    #     rh = ReactionHandler(rem_bot_react = True)

    #     @rh.reaction(cfg.emojis["vs"], cfg.emojis["nc"], cfg.emojis["tr"])
    #     def pick_faction(reaction, player, user):
    #         if player.active and isinstance(player.active, TeamCaptain) and player.active.is_turn:
    #             for faction in ["vs", "nc", "tr"]:
    #                 if str(reaction) == cfg.emojis[faction]:
    #                     self.faction_pick(player.active.team, faction)
    #                     await self.__msg.clear_reactions()
    #         else:
    #             raise UserLackingPermission

    #     add_handler(msg.id, rh)
    #     await rh.auto_add_reactions(msg)

    # async def faction_pick(self, team, arg):
    #     faction = cfg.i_factions[arg.upper()]
    #     other = self.__teams[team.id-1]
    #     if other.faction == faction:
    #         raise AlreadyPicked
    #     team.faction = faction
    #     team.captain.is_turn = False
    #     self.__audio_bot.faction_pick(team)
    #     if other.faction != 0:
    #         msg = await send("PK_FACTION_OK", self.channel, team.name, cfg.factions[team.faction])
    #         self.__status = MatchStatus.IS_BASING
    #         self.__find_base.start()
    #     else:
    #         other.captain.is_turn = True
    #         msg = await send("PK_FACTION_OK_NEXT", self.channel, team.name, cfg.factions[team.faction], other.captain.mention)
    #     return msg
    #
    # def faction_change(self, team, arg):
    #     faction = cfg.i_factions[arg.upper()]
    #     other = self.__teams[team.id-1]
    #     if other.faction == faction:
    #         return False
    #     team.faction = faction
    #     return True

    # def on_player_sub(self, subbed):
    #     new_player = _get_sub()
    #     if new_player is None:
    #         return
    #     new_player.on_match_selected(self)
    #     if subbed.status is PlayerStatus.IS_MATCHED:
    #         del self.__players[subbed.id]
    #         self.__players[new_player.id] = new_player
    #     elif subbed.status is PlayerStatus.IS_PICKED:
    #         a_sub = subbed.active
    #         a_sub.team.on_player_sub(a_sub, new_player)
    #     subbed.on_player_clean()
    #     return new_player

    def ts3_test(self):
        self.__audio_bot.drop_match()

    #
    # def on_team_ready(self, team):
    #     team.captain.is_turn = False
    #     team.on_team_ready()
    #     self.__audio_bot.team_ready(team)
    #     other = self.__teams[team.id-1]
    #     # If other is_turn, then not ready
    #     # Else everyone ready
    #     if not other.captain.is_turn:
    #         self.__status = MatchStatus.IS_STARTING
    #         self.__start_match.start()

    @loop(count=1)
    async def __find_base(self):
        for tm in self.__teams:
            tm.captain.is_turn = True
        if self.__base_selector.status is SelStatus.IS_CONFIRMED:
            await send("MATCH_BASE_AUTO", self.__channel, self.__base_selector.base.name)
            self.__ready.start()
            return
        captain_pings = [tm.captain.mention for tm in self.__teams]
        self.__status = MatchStatus.IS_BASING
        self.__audio_bot.select_base()
        await send("PK_WAIT_BASE", self.__channel, *captain_pings)
        await self.__base_selector.on_pick_start()

    # @loop(count=1)
    # async def __ready(self):
    #     self.__status = MatchStatus.IS_RUNNING
    #     for tm in self.__teams:
    #         tm.captain.is_turn = True
    #     captain_pings = [tm.captain.mention for tm in self.__teams]
    #     try:
    #         await self.__accounts.give_accounts()
    #     except AccountsNotEnough:
    #         await send("ACC_NOT_ENOUGH", self.__channel)
    #         await self.clear()
    #         return
    #     except Exception as e:
    #         log.error(f"Error in account giving function!\n{e}")
    #         await send("ACC_ERROR", self.__channel)
    #         await self.clear()
    #         return
    #
    #     self.__status = MatchStatus.IS_WAITING
    #     self.__audio_bot.match_confirm()
    #     await send("MATCH_CONFIRM", self.__channel, *captain_pings, match=self)

    @loop(minutes=10, delay=1, count=2)
    async def _on_match_over(self):
        player_pings = [" ".join(tm.all_pings) for tm in self.__teams]
        self.__audio_bot.round_over()
        await send("MATCH_ROUND_OVER", self.__channel, *player_pings, self.round_no)
        for tm in self.__teams:
            tm.captain.is_turn = True
        if self.round_no < 2:
            self.__audio_bot.switch_sides()
            await send("MATCH_SWAP", self.__channel)
            self.__status = MatchStatus.IS_WAITING
            captain_pings = [tm.captain.mention for tm in self.__teams]
            self.__audio_bot.match_confirm()
            await send("MATCH_CONFIRM", self.__channel, *captain_pings, match=self)
            self._score_calculation.start()
            return
        await send("MATCH_OVER", self.__channel)
        self.__status = MatchStatus.IS_RESULT
        try:
            await process_score(self)
            self.__result_msg = await publish_match_image(self)
        except Exception as e:
            log.error(f"Error in score or publish function!\n{e}")
        try:
            await update_match(self)
        except Exception as e:
            log.error(f"Error in match database push!\n{e}")
        await self.clear()

    @loop(count=1)
    async def _score_calculation(self):
        try:
            await process_score(self)
            self.__result_msg = await publish_match_image(self)
        except Exception as e:
            log.error(f"Error in score or publish function!\n{e}")


    # @loop(count=1)
    # async def __start_match(self):
    #     self.__audio_bot.countdown()
    #     await send("MATCH_STARTING_1", self.__channel, self.round_no, "30")
    #     await sleep(10)
    #     await send("MATCH_STARTING_2", self.__channel, self.round_no, "20")
    #     await sleep(10)
    #     await send("MATCH_STARTING_2", self.__channel, self.round_no, "10")
    #     await sleep(10)
    #     player_pings = [" ".join(tm.all_pings) for tm in self.__teams]
    #     await send("MATCH_STARTED", self.__channel, *player_pings, self.round_no)
    #     self.__round_stamps.append(int(dt.timestamp(dt.now())))
    #     self.__status = MatchStatus.IS_PLAYING
    #     self._on_match_over.start()

    @loop(count=1)
    async def _launch(self):
        self.__audio_bot.drop_match()
        await send("MATCH_INIT", self.__channel, " ".join(self.player_pings))
        self.__accounts = AccountHander(self)
        self.__base_selector = MapSelection(self, bases_pool)
        for i in range(len(self.__teams)):
            self.__teams[i] = Team(i, f"Team {i + 1}", self)
            key = random_choice(list(self.__players))
            self.__teams[i].add_player(TeamCaptain, self.__players.pop(key))
        self.__teams[0].captain.is_turn = True
        self.__status = MatchStatus.IS_PICKING
        self.__audio_bot.select_teams()
        await send("MATCH_SHOW_PICKS", self.__channel, self.__teams[0].captain.mention, match=self)

    async def clear(self):
        """ Clearing match and base player objetcts
        Team and ActivePlayer objects should get garbage collected, nothing is referencing them anymore"""

        if self.status is MatchStatus.IS_PLAYING:
            self._on_match_over.cancel()
            player_pings = [" ".join(tm.all_pings) for tm in self.__teams]
            self.__audio_bot.round_over()
            await send("MATCH_ROUND_OVER", self.__channel, *player_pings, self.round_no)
            await send("MATCH_OVER", self.__channel)

        # Updating account sheet with current match
        await self.__accounts.do_update()

        # Clean players if left in the list
        for p in self.__players.values():
            p.on_player_clean()

        # Clean players if in teams
        for tm in self.__teams:
            for a_player in tm.players:
                a_player.clean()

        # Clean base_selector
        self.__base_selector.clean()

        # Reset ingame check
        if get_offline_players.bypass:
                get_offline_players.bypass = False

        # Release all objects:
        self.__accounts = None
        self.__base_selector = None
        self.__teams = [None, None]
        self.__round_stamps.clear()
        self.__result_msg = None
        self.__players.clear()
        await send("MATCH_CLEARED", self.__channel)
        self.__status = MatchStatus.IS_FREE
        _on_match_free()

    @property
    def base(self):
        if self.__base_selector.status is SelStatus.IS_CONFIRMED:
            return self.__base_selector.base

    # TODO: testing only
    @property
    def players(self):
        return self.__players

    @property
    def round_no(self):
        if self.__status is MatchStatus.IS_PLAYING:
            return len(self.__round_stamps)
        if self.__status in (MatchStatus.IS_STARTING, MatchStatus.IS_WAITING):
            return len(self.__round_stamps) + 1
        return 0

    @property
    def start_stamp(self):
        return self.__round_stamps[-1]

    @property
    def round_stamps(self):
        return self.__round_stamps

    @property
    def base_selector(self):
        return self.__base_selector

    # # DEV
    # @teams.setter
    # def teams(self, tms):
    #     self.__teams=tms
    
    # # DEV
    # @start_stamp.setter
    # def start_stamp(self, st):
    #     self.__round_stamps = st
    
    # # DEV
    # @base_selector.setter
    # def base_selector(self, ms):
    #     self.__base_selector = ms

    # # DEV
    # @msg.setter
    # def msg(self, msg):
    #     self.__result_msg = msg
    
    # #DEV
    # @status.setter
    # def status(self, bl):
    #     if bl:
    #         self.__status = MatchStatus.IS_RESULT
    #     else:
    #         self.__status = MatchStatus.IS_PLAYING