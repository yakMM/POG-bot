from display.strings import AllStrings as disp
from display.classes import ContextWrapper

import modules.config as cfg

from match_process import MatchStatus
import modules.reactions as reactions

import match_process.common_picking as common
import match_process.meta as meta
from asyncio import sleep


class FactionPicking(meta.Process, status=MatchStatus.IS_FACTION):

    def __init__(self, match):
        self.match = match

        self.reaction_handler = reactions.SingleMessageReactionHandler()
        self.add_callbacks(self.reaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        self.picking_captain = self.match.teams[1].captain

        super().__init__(match, self.picking_captain)

    @meta.init_loop
    async def init_loop(self, picker):
        await sleep(0)
        self.match.audio_bot.select_factions()
        msg = await disp.PK_OK_FACTION.send(self.match.channel, picker.mention, match=self.match.proxy)
        await self.reaction_handler.set_new_msg(msg)

    def add_callbacks(self, rh):

        @rh.reaction(cfg.emojis["vs"], cfg.emojis["nc"], cfg.emojis["tr"])
        def check(reaction, player, user):
            if not player.active:
                raise reactions.UserLackingPermission
            if player.match is not self.match.proxy:
                raise reactions.UserLackingPermission
            a_p = player.active
            if not a_p.is_captain:
                raise reactions.UserLackingPermission
            if not a_p.is_turn:
                raise reactions.UserLackingPermission

        @rh.reaction(cfg.emojis["vs"], cfg.emojis["nc"], cfg.emojis["tr"])
        async def pick_faction(reaction, player, user):
            for faction in ["vs", "nc", "tr"]:
                if str(reaction) == cfg.emojis[faction]:
                    ctx = ContextWrapper.wrap(self.match.channel)
                    ctx.author = user
                    msg = await self.do_pick(ctx, player.active.team, faction)
                    if msg:
                        await self.reaction_handler.set_new_msg(msg)
                    break

    @meta.public
    async def sub(self, ctx, subbed):
        await common.after_pick_sub(ctx, self.match, subbed)

    @meta.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        msg = await disp.PK_FACTION_HELP.send(ctx, self.picking_captain.mention)
        await self.reaction_handler.set_new_msg(msg)

    @meta.public
    async def clear(self, ctx):
        await self.reaction_handler.destroy()
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @meta.public
    async def pick(self, ctx, captain, args):
        msg = await common.check_faction(ctx, args)

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
        common.switch_turn(self, team)
        self.match.audio_bot.faction_pick(team)

        # If other team didn't pick yet:
        if other.faction == 0:
            msg = await disp.PK_FACTION_OK_NEXT.send(self.match.channel, team.name, cfg.factions[team.faction],
                                                     other.captain.mention)
            self.reaction_handler.rem_reaction(cfg.emojis[arg.lower()])
            return msg

        # Else, over, all teams have selected a faction
        await disp.PK_FACTION_OK.send(ctx, team.name, cfg.factions[team.faction])
        await self.reaction_handler.destroy()
        self.match.on_faction_pick_over()
