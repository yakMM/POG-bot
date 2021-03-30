from display import AllStrings as disp, ContextWrapper
from lib.tasks import loop
import discord.errors
from logging import getLogger

from .match_status import MatchStatus
from random import choice as random_choice

from classes.teams import Team
from classes import TeamCaptain, ActivePlayer, Player

import match_process.common_picking as common
import match_process.meta as meta

from lib.tasks import Loop, loop

from modules.roles import modify_match_channel
import modules.config as cfg
import modules.reactions as reactions
from modules.tools import UnexpectedError

log = getLogger("pog_bot")


class CaptainSelection(meta.Process, status=MatchStatus.IS_CAPTAIN):

    def __init__(self, match, p_list):
        self.match = match
        self.p_list = p_list
        self.players = dict()

        for p in p_list:
            self.players[p.id] = p
            p.on_match_selected(self.match.proxy)

        self.captains = [None, None]

        self.volunteer_rh = reactions.SingleMessageReactionHandler()

        self.accept_rh = reactions.ReactionHandler(auto_destroy=True)
        self.accept_msg = [None, None]

        @self.volunteer_rh.reaction("🖐️")
        async def volunteer(reaction, player, user, msg):
            if player not in self.p_list:
                raise reactions.UserLackingPermission
            await self.on_volunteer(player)

        @self.accept_rh.reaction("✅", "❌")
        async def answer(reaction, player, user, msg):
            if player is self.captains[0]:
                i = 0
            elif player is self.captains[1]:
                i = 1
            else:
                raise reactions.UserLackingPermission
            if msg.id != self.accept_msg[i].id:
                raise reactions.UserLackingPermission
            if not await self.on_answer(player, is_accept=(str(reaction) == "✅")):
                raise reactions.UserLackingPermission

        super().__init__(match)

    @meta.init_loop
    async def init(self):
        # Open match channel
        await modify_match_channel(self.match.channel, view=True)
        await disp.LB_MATCH_STARTING.send(ContextWrapper.channel(cfg.channels["lobby"]), self.match.channel.id)

        for p in self.players.values():
            ctx = ContextWrapper.user(p.id)
            try:
                await disp.MATCH_DM_PING.send(ctx)
            except discord.errors.Forbidden:
                log.warning(f"Player id:[{p.id}], name:[{p.name}] is refusing DMs")

        players_ping = " ".join(p.mention for p in self.players.values())
        await disp.MATCH_INIT.send(self.match.channel, players_ping)

        # Initialize teams
        self.match.teams[0] = Team(0, f"Team 1", self.match.proxy)
        self.match.teams[1] = Team(1, f"Team 2", self.match.proxy)

        await self.info()

        self.auto_captain.start()
        await disp.CAP_AUTO_ANNOUNCE.send(self.match.channel)

    @meta.public
    async def clear(self, ctx):
        self.auto_captain.cancel()
        await self.clean_msg(0)
        await self.clean_msg(1)
        await self.volunteer_rh.destroy()
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @meta.public
    async def info(self):
        msg = await disp.CAP_WAITING.send(self.match.channel, match=self.match.proxy)
        await self.volunteer_rh.set_new_msg(msg)

    @meta.public
    async def on_volunteer(self, player):
        if not self.captains[0]:
            i = 0
        elif not self.captains[1]:
            i = 1
        elif not self.captains[0].active:
            i = 0
        elif not self.captains[1].active:
            i = 1
        else:
            raise UnexpectedError("No captain spot left!")
        if player not in self.p_list:
            raise UnexpectedError("Player not in player list!")
        await self.add_captain(i, player)

    @meta.public
    async def on_answer(self, player, is_accept):
        if player is self.captains[0] and not player.active:
            i = 0
        elif player is self.captains[1] and not player.active:
            i = 1
        else:
            return False
        if is_accept:
            await self.add_captain(i, player)
        else:
            self.captains[i] = None
            ctx = ContextWrapper.wrap(self.match.channel)
            ctx.author = player
            await disp.CAP_DENY_OK.send(ctx)
            self.auto_captain.restart()
            await self.get_new_auto(i)

        return True

    @loop(minutes=1, delay=1, count=2)
    async def auto_captain(self):
        for i in range(2):
            await self.get_new_auto(i)
        self.auto_captain.restart()

    async def get_new_auto(self, i):
        await self.clean_msg(i)
        captain = self.captains[i]
        if not captain or (captain and not captain.active):
            if not self.players:
                for p in self.p_list:
                    self.players[p.id] = p
            player = self.players.pop(self.find_captain())
            self.captains[i] = player
            msg = await disp.CAP_AUTO.send(self.match.channel, player.mention, self.match.teams[i].name)
            reactions.add_handler(msg.id, self.accept_rh)
            self.accept_msg[i] = msg
            await self.accept_rh.auto_add_reactions(msg)

    async def add_captain(self, i, player):
        self.match.teams[i].add_player(TeamCaptain, player)
        self.captains[i] = player
        self.p_list.remove(player)
        if player.id in self.players:
            del self.players[player.id]
        await self.clean_msg(i)
        await disp.CAP_OK.send(self.match.channel, player.mention, self.match.teams[i].name)
        if self.captains[i-1] and self.captains[i-1].active:
            self.auto_captain.cancel()
            await self.volunteer_rh.destroy()
            self.match.on_captain_over(self.p_list)
        else:
            await self.info()

    async def clean_msg(self, i):
        if self.accept_msg[i]:
            msg = self.accept_msg[i]
            reactions.rem_handler(msg.id)
            await msg.clear_reactions()
            self.accept_msg[i] = None

    @meta.public
    def get_left_players_pings(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        pings = [f"{p.mention} ({p.name})" for p in self.p_list]
        return pings

    def find_captain(self):
        """ Pick at random a captain.
            TODO: Base this pick on some kind of stats or a role

            Returns
            -------
            captain : Player
                The player designated as captain.
        """
        return random_choice(list(self.players))
