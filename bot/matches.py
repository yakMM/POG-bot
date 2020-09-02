import modules.config as cfg
from modules.exceptions import UnexpectedError, AccountsNotEnough, ElementNotFound
from modules.display import channelSend, edit
from modules.enumerations import PlayerStatus, MatchStatus, SelStatus
from datetime import datetime as dt
from modules import ts3

from classes.teams import Team  # ok
from classes.players import TeamCaptain, ActivePlayer  # ok
from classes.maps import MapSelection  # ok
from classes.accounts import AccountHander  # ok

from random import choice as randomChoice
from lib import tasks
from asyncio import sleep
from logging import getLogger

log = getLogger(__name__)

_lobbyList = list()
_lobbyStuck = False
_allMatches = dict()


def getMatch(id):
    if id not in _allMatches:
        raise ElementNotFound(id)  # should never happen
    return _allMatches[id]


def isLobbyStuck():
    global _lobbyStuck
    return _lobbyStuck


def addToLobby(player):
    _lobbyList.append(player)
    player.status = PlayerStatus.IS_LOBBIED
    if len(_lobbyList) == cfg.general["lobby_size"]:
        _autoPing.cancel()
        startMatchFromFullLobby.start()
    elif len(_lobbyList) >= cfg.general["lobby_size"] - 4:
        if not _autoPing.is_running():
            _autoPing.start()


@tasks.loop(seconds=100, delay=1, count=2)
async def _autoPing():
    await channelSend("LB_NOTIFY", cfg.discord_ids["lobby"], f'<@&{cfg.discord_ids["notify_role"]}>')


def getLobbyLen():
    return len(_lobbyList)


def getAllNamesInLobby():
    names = [p.mention for p in _lobbyList]
    return names


def removeFromLobby(player):
    _lobbyList.remove(player)
    _onLobbyRemove()
    player.status = PlayerStatus.IS_REGISTERED


def _onMatchFree():
    if len(_lobbyList) == cfg.general["lobby_size"]:
        startMatchFromFullLobby.start()


def _onLobbyRemove():
    global _lobbyStuck
    _lobbyStuck = False
    if len(_lobbyList) < cfg.general["lobby_size"]-4:
        _autoPing.cancel()


@tasks.loop(count=1)
async def startMatchFromFullLobby():
    global _lobbyStuck
    match = _findSpotForMatch()
    if match is None:
        _lobbyStuck = True
        _autoPing.cancel()
        await channelSend("LB_STUCK", cfg.discord_ids["lobby"])
        return
    _lobbyStuck = False
    match._setPlayerList(_lobbyList)
    for p in _lobbyList:
        p.match = match  # Player status is modified automatically in IS_MATCHED
    _lobbyList.clear()
    match._launch.start()
    await channelSend("LB_MATCH_STARTING", cfg.discord_ids["lobby"], match.id)
    # ts3: lobby full
    if match.id == cfg.discord_ids["matches"][0]:  # if match 1
        ts3.bot1.move(cfg.teamspeak_ids["ts_lobby"])  # IF IT HANGS HERE MAKE SURE webapi.js IS ENABLED FOR SINUSBOT
        ts3.bot1.enqueue(cfg.audio_ids["drop_match_1_picks"])
        await sleep(ts3.bot1.get_duration(cfg.audio_ids["drop_match_1_picks"]))
        ts3.bot1.move(cfg.teamspeak_ids["ts_match_1_picks"])
    elif match.id == cfg.discord_ids["matches"][1]:  # if match 2
        ts3.bot2.move(cfg.teamspeak_ids["ts_lobby"])
        ts3.bot2.enqueue(cfg.audio_ids["drop_match_2_picks"])
        await sleep(ts3.bot2.get_duration(cfg.audio_ids["drop_match_2_picks"]))
        ts3.bot2.move(cfg.teamspeak_ids["ts_match_2_picks"])
    elif match.id == cfg.discord_ids["matches"][2]:  # if match 3
        ts3.bot2.move(cfg.teamspeak_ids["ts_lobby"])
        ts3.bot2.enqueue(cfg.audio_ids["drop_match_3_picks"])
        await sleep(ts3.bot2.get_duration(cfg.audio_ids["drop_match_3_picks"]))
        ts3.bot2.move(cfg.teamspeak_ids["ts_match_3_picks"])


def onPlayerInactive(player):
    if player.status == PlayerStatus.IS_LOBBIED:
        player.onInactive.start(onInactiveConfirmed)


def onPlayerActive(player):
    if player.status == PlayerStatus.IS_LOBBIED:
        player.onInactive.cancel()


async def onInactiveConfirmed(player):
    removeFromLobby(player)
    await channelSend("LB_WENT_INACTIVE", cfg.discord_ids["lobby"], player.mention, namesInLobby=getAllNamesInLobby())


def clearLobby():
    if len(_lobbyList) == 0:
        return False
    for p in _lobbyList:
        p.status = PlayerStatus.IS_REGISTERED
    _lobbyList.clear()
    _onLobbyRemove()
    return True


def _findSpotForMatch():
    for match in _allMatches.values():
        if match.status == MatchStatus.IS_FREE:
            return match
    return None


def which_bot(match_id):
    ts3bot = None
    if match_id == cfg.discord_ids["matches"][0]:
        ts3bot = ts3.bot1
    elif match_id == cfg.discord_ids["matches"][1] or match_id == cfg.discord_ids["matches"][2]:
        ts3bot = ts3.bot2
    return ts3bot


def which_pick_channels(match_id):
    pick_channel = ""
    for i in range(0, 3):
        if match_id == cfg.discord_ids["matches"][i]:
            pick_channel = cfg.teamspeak_ids[f"ts_match_{i+1}_picks"]
    return pick_channel


def which_team_channels(match_id):
    team_channels = ("", "")
    for i in range(0, 3):
        if match_id == cfg.discord_ids["matches"][i]:
            team_channels = (cfg.teamspeak_ids[f"ts_match_{i+1}_team_1"], cfg.teamspeak_ids[f"ts_match_{i+1}_team_2"])
    return team_channels


def init(list):
    for id in list:
        Match(id)


class Match:
    def __init__(self, id):
        self.__id = id
        self.__players = dict()
        self.__status = MatchStatus.IS_FREE
        self.__teams = [None, None]
        self.__mapSelector = None
        self.__number = 0
        _allMatches[id] = self
        self.__accounts = None
        self.__roundsStamps = list()

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
    def statusString(self):
        return self.__status.value

    @property
    def number(self):
        return self.__number

    @number.setter
    def number(self, num):
        self.__number = num

    @property
    def playerPings(self):
        pings = [p.mention for p in self.__players.values()]
        return pings

    def _setPlayerList(self, pList):
        self.__status = MatchStatus.IS_RUNNING
        for p in pList:
            self.__players[p.id] = p

    def pick(self, team, player):
        team.addPlayer(ActivePlayer, player)
        self.__players.pop(player.id)
        team.captain.isTurn = False
        other = self.__teams[team.id - 1]
        other.captain.isTurn = True
        if len(self.__players) == 1:
            # Auto pick last player
            p = [*self.__players.values()][0]
            self.__pingLastPlayer.start(other, p)
            return self.pick(other, p)
        if len(self.__players) == 0:
            self.__status = MatchStatus.IS_FACTION
            self.__teams[1].captain.isTurn = True
            self.__teams[0].captain.isTurn = False
            picker = self.__teams[1].captain
            self.__playerPickOver.start(picker)
            return self.__teams[1].captain
        return other.captain

    def confirmMap(self):
        self.__mapSelector.confirm()
        if self.__status == MatchStatus.IS_MAPPING:
            self.__ready.start()

    def pickMap(self, captain):
        if self.__mapSelector.status == SelStatus.IS_SELECTED:
            captain.isTurn = False
            other = self.__teams[captain.team.id - 1]
            other.captain.isTurn = True
            return other.captain
        return captain

    @tasks.loop(count=1)
    async def __pingLastPlayer(self, team, p):
        await channelSend("PK_LAST", self.__id, p.mention, team.name)

    @tasks.loop(count=1)
    async def __playerPickOver(self, picker):
        await channelSend("PK_OK_FACTION", self.__id, picker.mention, match=self)
        # ts3: select faction
        ts3bot = which_bot(self.__id)
        pick_channel = which_pick_channels(self.__id)
        ts3bot.move(pick_channel)
        ts3bot.enqueue(cfg.audio_ids["select_factions"])

    def factionPick(self, team, str):
        faction = cfg.i_factions[str]
        other = self.__teams[team.id - 1]
        if other.faction == faction:
            return team.captain
        team.faction = faction
        team.captain.isTurn = False
        if other.faction != 0:
            self.__status = MatchStatus.IS_MAPPING
            self.__findMap.start()
        else:
            other.captain.isTurn = True
        return other.captain

    def onTeamReady(self, team):
        # ts3: ready up
        notReady = list()
        for p in team.players:
            if p.hasOwnAccount:
                continue
            if p.account is None:
                log.error(f"Debug: {p.name} has no account")
            if p.account.isValidated:
                continue
            notReady.append(p.mention)
        if len(notReady) != 0:
            return notReady
        team.captain.isTurn = False
        other = self.__teams[team.id - 1]
        # If other isTurn, then not ready
        # Else everyone ready
        if not other.captain.isTurn:
            self.__status = MatchStatus.IS_STARTING
            self.__startMatch.start()

    @tasks.loop(count=1)
    async def __findMap(self):  # legacy way of picking maps using "=p <map name>" and "=p confirm"
        # LEGACY CODE
        # Disabling map at random:
        # if self.__map == None:
        #     try:
        #         sel = getMapSelection(self.__id)
        #     except ElementNotFound:
        #         sel = MapSelection(self.__id)
        #     sel.selectFromIdList(cfg.PIL_MAPS_IDS)
        #     if sel.status not in (SelStatus.IS_SELECTED, SelStatus.IS_SELECTION):
        #         await channelSend("UNKNOWN_ERROR", self.__id, "Can't find a map at random!")
        #         return
        #     self.__map = randomChoice(sel.selection)
        ts3bot = which_bot(self.__id)
        for tm in self.__teams:
            tm.captain.isTurn = True
        if self.__mapSelector.status == SelStatus.IS_CONFIRMED:
            await channelSend("MATCH_MAP_AUTO", self.__id, self.__mapSelector.map.name)
            # ts3: map selected
            pick_channel = which_pick_channels(self.__id)
            ts3bot.move(pick_channel)
            ts3bot.enqueue(cfg.audio_ids["map_selected"])
            self.__ready.start()
            return
        captainPings = [tm.captain.mention for tm in self.__teams]
        self.__status = MatchStatus.IS_MAPPING
        # ts3: select map
        pick_channel = which_pick_channels(self.__id)
        ts3bot.move(pick_channel)
        await sleep(1)  # prevents playing this before faction announce
        ts3bot.enqueue(cfg.audio_ids["select_map"])
        await channelSend("PK_WAIT_MAP", self.__id, *captainPings)
        # await channelSend("MAP_DISPLAY_LIST", self.__id, sel=self.__mapSelector.__selection)

    # @tasks.loop(count=1)
    # async def __findMapFromCal(self):  # new way of picking maps from availability in jaeger calendar
    #     ts3bot = which_bot(self.__id)
    #     for tm in self.__teams:
    #         tm.captain.isTurn = True
    #     if self.__mapSelector.status == SelStatus.IS_CONFIRMED:
    #         await channelSend("MATCH_MAP_AUTO", self.__id, self.__mapSelector.map.name)
    #         # ts3: map selected
    #         pick_channel = which_pick_channels(self.__id)
    #         ts3bot.move(pick_channel)
    #         ts3bot.enqueue(cfg.audio_ids["map_selected"])
    #         self.__ready.start()
    #         return
    #     captainPings = [tm.captain.mention for tm in self.__teams]
    #     self.__status = MatchStatus.IS_MAPPING
    #     # ts3: select map
    #     pick_channel = which_pick_channels(self.__id)
    #     ts3bot.move(pick_channel)
    #     await sleep(1)  # prevents playing this before faction announce
    #     ts3bot.enqueue(cfg.audio_ids["select_map"])
    #     # await channelSend("PK_WAIT_MAP", self.__id, *captainPings)
    #     await channelSend("MAP_DISPLAY_LIST", self.__id, sel=self.__mapSelector.__selection)

    @tasks.loop(count=1)
    async def __ready(self):
        for tm in self.__teams:
            tm.matchReady()
            tm.captain.isTurn = True
        captainPings = [tm.captain.mention for tm in self.__teams]
        try:
            await self.__accounts.give_accounts()
        except AccountsNotEnough:
            await channelSend("ACC_NOT_ENOUGH", self.__id)
            await self.clear()
            return
        self.__status = MatchStatus.IS_WAITING
        await channelSend("MATCH_CONFIRM", self.__id, *captainPings, match=self)
        # ts3: type =ready
        await sleep(10)  # waits long enough for people to move to their team's channels
        team_channels = which_team_channels(self.__id)
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        ts3.bot1.enqueue(cfg.audio_ids["type_ready"])
        ts3.bot2.enqueue(cfg.audio_ids["type_ready"])

    @tasks.loop(minutes=cfg.ROUND_LENGTH, delay=1, count=2)
    async def __onMatchOver(self):

        playerPings = [tm.allPings for tm in self.__teams]
        await channelSend("MATCH_ROUND_OVER", self.__id, *playerPings, self.roundNo)
        # ts3: round over
        team_channels = which_team_channels(self.__id)
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        ts3.bot1.play(cfg.audio_ids["round_over"])
        ts3.bot2.play(cfg.audio_ids["round_over"])
        for tm in self.__teams:
            tm.captain.isTurn = True
        if self.roundNo < 2:
            await channelSend("MATCH_SWAP", self.__id)
            # ts3: swap sundies
            ts3.bot1.move(team_channels[0])
            ts3.bot2.move(team_channels[1])
            await sleep(0.1)  # prevents bug when enqueuing songs too quickly
            ts3.bot1.enqueue(cfg.audio_ids["switch_sides"])
            ts3.bot2.enqueue(cfg.audio_ids["switch_sides"])
            self.__status = MatchStatus.IS_WAITING
            captainPings = [tm.captain.mention for tm in self.__teams]
            await channelSend("MATCH_CONFIRM", self.__id, *captainPings, match=self)
            ts3.bot1.move(team_channels[0])
            ts3.bot2.move(team_channels[1])
            ts3.bot1.enqueue(cfg.audio_ids["type_ready"])
            ts3.bot2.enqueue(cfg.audio_ids["type_ready"])
            return
        await channelSend("MATCH_OVER", self.__id)
        self.__status = MatchStatus.IS_RUNNING
        await self.clear()

    @tasks.loop(count=1)
    async def __startMatch(self):
        # ts3: ensure bots are in match team channels -- ideally add a check to ensure no matches start within 30s of each other
        team_channels = which_team_channels(self.__id)
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        await channelSend("MATCH_STARTING_1", self.__id, self.roundNo, "30")
        # ts3: 30s
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        ts3.bot1.play(cfg.audio_ids["30s"])
        ts3.bot2.play(cfg.audio_ids["30s"])
        await sleep(10)
        await channelSend("MATCH_STARTING_2", self.__id, self.roundNo, "20")
        # ts3: 10s
        await sleep(8)
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        ts3.bot1.play(cfg.audio_ids["10s"])
        ts3.bot2.play(cfg.audio_ids["10s"])
        await sleep(2)
        await channelSend("MATCH_STARTING_2", self.__id, self.roundNo, "10")
        await sleep(3.2)  # odd timings make sure the voice line plays at the right time
        # ts3: 5s
        ts3.bot1.move(team_channels[0])
        ts3.bot2.move(team_channels[1])
        ts3.bot1.play(cfg.audio_ids["5s"])
        ts3.bot2.play(cfg.audio_ids["5s"])
        await sleep(6.8)
        playerPings = [tm.allPings for tm in self.__teams]
        await channelSend("MATCH_STARTED", self.__id, *playerPings, self.roundNo)
        self.__roundsStamps.append(int(dt.timestamp(dt.now())))
        self.__status = MatchStatus.IS_PLAYING
        self._onMatchOver.start()

    @tasks.loop(count=1)
    async def _launch(self):
        await channelSend("MATCH_INIT", self.__id, " ".join(self.playerPings))
        self.__accounts = AccountHander(self)
        self.__mapSelector = MapSelection(self)
        for i in range(len(self.__teams)):
            self.__teams[i] = Team(i, f"Team {i + 1}", self)
            key = randomChoice(list(self.__players))
            self.__teams[i].addPlayer(TeamCaptain, self.__players.pop(key))
        self.__teams[0].captain.isTurn = True
        self.__status = MatchStatus.IS_PICKING
        await channelSend("MATCH_SHOW_PICKS", self.__id, self.__teams[0].captain.mention, match=self)
        # ts3: select teams
        await sleep(17)  # wait some time after the bot moves before announcing to select players for teams
        ts3bot = which_bot(self.__id)
        pick_channel = which_pick_channels(self.__id)
        ts3bot.move(pick_channel)
        ts3bot.enqueue(cfg.audio_ids["select_teams"])

    async def clear(self):
        """ Clearing match and base player objetcts
        Team and ActivePlayer objects should get garbage collected, nothing is referencing them anymore"""

        if self.status == MatchStatus.IS_PLAYING:
            self._onMatchOver.cancel()
            playerPings = [tm.allPings for tm in self.__teams]
            await channelSend("MATCH_ROUND_OVER", self.__id, *playerPings, self.roundNo)
            # ts3: round over
            team_channels = which_team_channels(self.__id)
            ts3.bot1.move(team_channels[0])
            ts3.bot2.move(team_channels[1])
            ts3.bot1.play(cfg.audio_ids["round_over"])
            ts3.bot2.play(cfg.audio_ids["round_over"])
            await channelSend("MATCH_OVER", self.__id)
            # ts3: round over

        # Updating account sheet with current match
        await self.__accounts.doUpdate()

        # Clean players if left in the list
        for p in self.__players.values():
            p.clean()

        # Clean players if in teams
        for tm in self.__teams:
            for p in tm.players:
                p.clean()

        # Clean mapSelector
        self.__mapSelector.clean()

        # Release all objects:
        self.__accounts = None
        self.__mapSelector = None
        self.__teams = [None, None]
        self.__roundsStamps.clear()
        self.__players.clear()
        await channelSend("MATCH_CLEARED", self.__id)
        self.__status = MatchStatus.IS_FREE
        _onMatchFree()
        await sleep(ts3.bot1.get_duration(cfg.audio_ids["round_over"]))
        ts3.bot1.move(cfg.teamspeak_ids["ts_lobby"])
        ts3.bot2.move(cfg.teamspeak_ids["ts_lobby"])

    @property
    def map(self):
        if self.__mapSelector.status == SelStatus.IS_CONFIRMED:
            return self.__mapSelector.map

    # TODO: testing only
    @property
    def players(self):
        return self.__players

    @property
    def roundNo(self):
        if self.__status == MatchStatus.IS_PLAYING:
            return len(self.__roundsStamps)
        if self.__status in (MatchStatus.IS_STARTING, MatchStatus.IS_WAITING):
            return len(self.__roundsStamps) + 1
        return 0

    @property
    def mapSelector(self):
        return self.__mapSelector
