from display import AllStrings as disp, ContextWrapper, InteractionContext, views
from asyncio import sleep
from logging import getLogger

import modules.config as cfg

from match import MatchStatus
from .process import Process
import match.classes.interactions as interactions

from match.common import check_faction, switch_turn, get_check_captain

log = getLogger("pog_bot")


class FactionPicking(Process, status=MatchStatus.IS_FACTION):
    def __init__(self, match):
        self.match = match

        self.picked_faction = ""

        self.interaction_handler = interactions.CaptainInteractionHandler(self.match, views.faction_buttons,
                                                                          disable_after_use=False)
        self.add_callbacks(self.interaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False

        super().__init__(match)

    @Process.init_loop
    async def init_loop(self):
        await sleep(0)
        ctx = self.interaction_handler.get_new_context(self.match.channel)
        await disp.PK_OK_FACTION.send(ctx, self.picking_captain.mention)

    def add_callbacks(self, ih):

        @ih.callback('VS', 'NC', 'TR')
        async def check(captain, interaction_id, interaction, interaction_values):
            ctx = self.interaction_handler.get_new_context(self.match.channel)
            await self.do_pick(ctx, captain.team, interaction_id)

    @Process.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        ctx = self.interaction_handler.get_new_context(ctx)
        await disp.PK_FACTION_HELP.send(ctx, self.picking_captain.mention)

    @Process.public
    def get_current_context(self, ctx):
        return self.interaction_handler.get_new_context(ctx)

    @Process.public
    def get_picked_faction(self):
        return self.picked_faction

    @property
    def picking_captain(self):
        for tm in self.match.teams:
            if tm.captain.is_turn:
                return tm.captain

    @Process.public
    async def clear(self, ctx):
        self.interaction_handler.clean()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def pick(self, ctx, captain, args):
        ctx = self.interaction_handler.get_new_context(ctx)
        if await check_faction(ctx, args):
            await self.do_pick(ctx, captain.team, args[0])

    async def do_pick(self, ctx, team, arg):
        # Get the faction an other team
        faction = cfg.i_factions[arg.upper()]
        other = self.match.teams[team.id - 1]

        # Check if the other team already picked it
        if other.faction == faction:
            await disp.PK_FACTION_OTHER.send(ctx)

        # If not, select the faction and give turn to other team
        team.faction = faction
        switch_turn(self.match, team)

        self.match.plugin_manager.on_faction_pick(team)

        # If other team didn't pick yet:
        if other.faction == 0:
            self.picked_faction = faction
            await disp.PK_FACTION_OK_NEXT.send(ctx, team.name, cfg.factions[team.faction],
                                                     other.captain.mention)
        else:
            # Else, over, all teams have selected a faction
            self.match.ready_next_process()
            self.interaction_handler.clean()
            await disp.PK_FACTION_OK.send(self.match.channel, team.name, cfg.factions[team.faction])
            self.match.plugin_manager.on_factions_picked()
            self.match.start_next_process()
