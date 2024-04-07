from display import AllStrings as disp, ContextWrapper, InteractionContext, views
from logging import getLogger
from random import choice as random_choice
import discord

from match import MatchStatus
from match.common import get_substitute, after_pick_sub, get_check_player
from .process import Process

from classes import ActivePlayer, Team

from lib.tasks import loop

import modules.config as cfg
import modules.roles as roles
from modules.tools import UnexpectedError
import match.classes.interactions as interactions

log = getLogger("pog_bot")

class CaptainSelection(Process, status=MatchStatus.IS_CAPTAIN):

    def __init__(self, match, p_list):
        self.match = match
        self.p_list = p_list
        self.players = dict()

        self.captains = [None, None]

        self.volunteer_ih = interactions.PlayerInteractionHandler(self.match, views.volunteer_button,
                                                                  disable_after_use=False)

        self.accept_ihs = [interactions.PlayerInteractionHandler(self.match, views.validation_buttons),
                           interactions.PlayerInteractionHandler(self.match, views.validation_buttons)]

        for i in range(2):
            self.add_callbacks(i, self.accept_ihs[i])

        @self.volunteer_ih.callback('volunteer')
        async def volunteer(player, interaction_id, interaction, interaction_values):
            if player.active:
                i_ctx = InteractionContext(interaction)
                await disp.CAP_ALREADY.send(i_ctx)
                raise interactions.InteractionNotAllowed
            if player not in self.p_list:
                # Should never happen
                raise interactions.InteractionInvalid("player is valid but not in player list")
            await self.on_volunteer(player)

        super().__init__(match)

    def add_callbacks(self, i, accept_ih):
        @accept_ih.callback('accept', 'decline')
        async def on_answer(player, interaction_id, interaction, interaction_values):
            i_ctx = InteractionContext(interaction)
            if player.active:
                await disp.CAP_ALREADY.send(i_ctx)
                raise interactions.InteractionNotAllowed
            if player not in self.captains:
                if interaction_id == 'accept':
                    await disp.CAP_ACCEPT_NO.send(i_ctx)
                elif interaction_id == 'decline':
                    await disp.CAP_DENY_NO.send(i_ctx)
                raise interactions.InteractionNotAllowed
            bl = await self.on_answer(player, is_accept=(interaction_id == 'accept'))
            bl = bl and player is self.captains[i]
            if not bl:
                raise interactions.InteractionNotAllowed

    @Process.init_loop
    async def init(self):
        for p in self.p_list:
            self.players[p.id] = p
            await p.on_match_selected(self.match.proxy)

        # Open match channel
        await roles.modify_match_channel(self.match.channel, view=True)
        await disp.LB_MATCH_STARTING.send(ContextWrapper.channel(cfg.channels["lobby"]), self.match.channel.id)

        players_ping = " ".join(p.mention for p in self.players.values())
        await disp.MATCH_INIT.send(self.match.channel, players_ping)

        # Initialize teams
        self.match.teams[0] = Team(0, f"Team 1", self.match.proxy)
        self.match.teams[1] = Team(1, f"Team 2", self.match.proxy)

        init_msg = await self.info()

        for p in self.p_list:
            if p.is_dm:
                ctx = await ContextWrapper.user(p.id)
                try:
                    await disp.MATCH_DM_PING.send(ctx, self.match.id,
                                                  self.match.channel.name,
                                                  init_msg.jump_url)
                except discord.errors.Forbidden:
                    log.warning(f"Player id:[{p.id}], name:[{p.name}] is refusing DMs")

        self.auto_captain.start()
        await disp.CAP_AUTO_ANNOUNCE.send(self.match.channel)

    @Process.public
    async def clear(self, ctx):
        self.auto_captain.cancel()
        for p in self.p_list:
            p.on_player_clean()
        for ih in self.accept_ihs:
            ih.clean()
        self.volunteer_ih.clean()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def info(self, ctx=None):
        ctx = self.volunteer_ih.get_new_context(self.match.channel)
        return await disp.CAP_WAITING.send(ctx, match=self.match.proxy)

    @Process.public
    async def on_volunteer(self, player):
        if player is self.captains[0]:
            i = 0
        elif player is self.captains[1]:
            i = 1
        elif not self.captains[0]:
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

    @Process.public
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
            ctx = ContextWrapper.wrap(self.match.channel, author=player)
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
        self.accept_ihs[i].clean()
        captain = self.captains[i]
        if not captain or (captain and not captain.active):
            if not self.players:
                for p in self.p_list:
                    self.players[p.id] = p
            player = self.players.pop(self.find_captain())
            self.captains[i] = player
            ctx = self.accept_ihs[i].get_new_context(self.match.channel)
            await disp.CAP_AUTO.send(ctx, player.mention, self.match.teams[i].name)

    async def add_captain(self, i, player):
        self.match.teams[i].add_player(ActivePlayer, player)
        self.captains[i] = player
        self.p_list.remove(player)
        if player.id in self.players:
            del self.players[player.id]
        self.accept_ihs[i].clean()
        self.match.plugin_manager.on_captain_selected(i, player)
        all_captains_selected = self.captains[i - 1] and self.captains[i - 1].active
        if all_captains_selected:
            self.match.ready_next_process(self.p_list)
            self.auto_captain.cancel()
            self.volunteer_ih.clean()
        await disp.CAP_OK.send(self.match.channel, player.mention, self.match.teams[i].name)
        if all_captains_selected:
            self.match.plugin_manager.on_captains_selected()
            self.match.start_next_process()
        else:
            await self.info()

    @Process.public
    def get_left_players(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        return self.p_list

    @Process.public
    def get_current_context(self, ctx):
        return self.volunteer_ih.get_new_context(ctx)

    def find_captain(self):
        """
        Pick at random a captain.

        :return: The player designated as captain.
        """
        potential = list()
        threshold = 20
        while not potential:
            for p in self.players.values():
                if p.stats.nb_matches_played >= threshold:
                    potential.append(p.id)
            threshold -= 5

        return random_choice(potential)

    @Process.public
    async def do_sub(self, subbed, force_player=None):
        """ Substitute a player by another one picked at random \
            in the lobby.

            Parameters
            ----------
            subbed : Player
                Player to be substituted
        """
        ctx = self.volunteer_ih.get_new_context(self.match.channel)
        # If subbed one has already been picked
        if subbed.active:
            player = await after_pick_sub(self.match, subbed.active, force_player, ctx=ctx)
            if player:
                if subbed is self.captains[0]:
                    self.captains[0] = player
                elif subbed is self.captains[1]:
                    self.captains[1] = player
                else:
                    raise UnexpectedError("Captain not found!")
        else:
            # Get a new player for substitution
            new_player = await get_substitute(self.match, subbed, player=force_player)
            if not new_player:
                return

            # Remove player suggestion
            i = -1
            if subbed is self.captains[0]:
                i = 0
            elif subbed is self.captains[1]:
                i = 1
            if i != -1:
                self.captains[i] = None
                self.auto_captain.restart()

            # Remove them from the player list
            if subbed.id in self.players:
                del self.players[subbed.id]
            self.p_list.remove(subbed)
            # Put the new player instead
            self.players[new_player.id] = new_player
            self.p_list.append(new_player)
            # Clean subbed one and send message
            subbed.on_player_clean()
            await disp.SUB_OKAY.send(ctx, new_player.mention,
                                     subbed.mention, match=self.match.proxy)

            if i != -1:
                await self.get_new_auto(i)
            return
