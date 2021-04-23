from display.strings import AllStrings as disp
from display.classes import ContextWrapper
from asyncio import sleep
import discord

import modules.config as cfg

from match import MatchStatus
from .process import Process
import modules.reactions as reactions

from match.common import check_faction, switch_turn


class FactionPicking(Process, status=MatchStatus.IS_FACTION):
    def __init__(self, match):
        super().__init__(match)
        self.match = match

        self.reaction_handler = reactions.SingleMessageReactionHandler()
        self.add_callbacks(self.reaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False

    @Process.init_loop
    async def init_loop(self):
        await sleep(0)
        for i in range(3):
            try:
                msg = await disp.PK_OK_FACTION.send(self.match.channel, self.picking_captain.mention, match=self.match.proxy)
                await self.reaction_handler.set_new_msg(msg)
                break
            except discord.NotFound:
                pass

    def add_callbacks(self, rh):

        @rh.reaction(cfg.emojis["VS"], cfg.emojis["NC"], cfg.emojis["TR"])
        def check(reaction, player, user, msg):
            if not player.active:
                raise reactions.UserLackingPermission
            if player.match is not self.match.proxy:
                raise reactions.UserLackingPermission
            a_p = player.active
            if not a_p.is_captain:
                raise reactions.UserLackingPermission
            if not a_p.is_turn:
                raise reactions.UserLackingPermission

        @rh.reaction(cfg.emojis["VS"], cfg.emojis["NC"], cfg.emojis["TR"])
        async def pick_faction(reaction, player, user, msg):
            for faction in ["VS", "NC", "TR"]:
                if str(reaction) == cfg.emojis[faction]:
                    ctx = ContextWrapper.wrap(self.match.channel)
                    ctx.author = user
                    msg = await self.do_pick(ctx, player.active.team, faction)
                    if msg:
                        await self.reaction_handler.set_new_msg(msg)
                    break

    @Process.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        msg = await disp.PK_FACTION_HELP.send(ctx, self.picking_captain.mention)
        await self.reaction_handler.set_new_msg(msg)

    @property
    def picking_captain(self):
        for tm in self.match.teams:
            if tm.captain.is_turn:
                return tm.captain

    @Process.public
    async def clear(self, ctx):
        self.reaction_handler.clear()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def pick(self, ctx, captain, args):
        msg = await check_faction(ctx, args)

        # If no error msg, do the pick
        if not msg:
            msg = await self.do_pick(ctx, captain.team, args[0])

        # If a msg was sent, set it for reaction handling
        if msg:
            await self.reaction_handler.set_new_msg(msg)

    async def do_pick(self, ctx, team, arg):
        # Get the faction an other team
        faction = cfg.i_factions[arg.upper()]
        other = self.match.teams[team.id - 1]

        # Check if the other team already picked it
        if other.faction == faction:
            msg = await disp.PK_FACTION_OTHER.send(ctx)
            return msg

        # If not, select the faction and give turn to other team
        team.faction = faction
        switch_turn(self, team)

        self.match.plugin_manager.on_faction_pick(team)

        # If other team didn't pick yet:
        if other.faction == 0:
            self.reaction_handler.rem_reaction(cfg.emojis[arg.upper()])
            msg = await disp.PK_FACTION_OK_NEXT.send(self.match.channel, team.name, cfg.factions[team.faction],
                                                     other.captain.mention)
            return msg

        # Else, over, all teams have selected a faction
        self.match.ready_next_process()
        self.reaction_handler.clear()
        await disp.PK_FACTION_OK.send(ctx, team.name, cfg.factions[team.faction])
        self.match.plugin_manager.on_factions_picked()
        self.match.start_next_process()
