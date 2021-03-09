from display.strings import AllStrings as display
from display.classes import ContextWrapper

import modules.config as cfg

from general.enumerations import MatchStatus, PlayerStatus
from modules.reactions import ReactionHandler, add_handler, rem_handler
from general.exceptions import UserLackingPermission

import match_process.common as common
import match_process.meta as meta
from asyncio import sleep


class FactionPicking(meta.Process, status=MatchStatus.IS_FACTION):

    def __init__(self, match):
        self.match = match
        self.last_msg = None
        self.picking_captain = None
        self.reaction_handler = ReactionHandler()
        self.add_callbacks(self.reaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        self.picking_captain = self.match.teams[1].captain

        super().__init__(match, self.picking_captain)

    @meta.init_loop
    async def init_loop(self, picker):
        await sleep(0)
        self.match.audio_bot.select_factions()
        msg = await display.PK_OK_FACTION.send(self.match.channel, picker.mention, match=self.match.proxy)
        await self.set_faction_msg(msg)

    def add_callbacks(self, rh):

        @rh.reaction(cfg.emojis["vs"], cfg.emojis["nc"], cfg.emojis["tr"])
        def check(reaction, player, user):
            if player.status is not PlayerStatus.IS_PICKED:
                raise UserLackingPermission
            if player.match is not self.match.proxy:
                raise UserLackingPermission
            a_p = player.active
            if not a_p.is_captain:
                raise UserLackingPermission
            if not a_p.is_turn:
                raise UserLackingPermission

        @rh.reaction(cfg.emojis["vs"], cfg.emojis["nc"], cfg.emojis["tr"])
        async def pick_faction(reaction, player, user):
            for faction in ["vs", "nc", "tr"]:
                if str(reaction) == cfg.emojis[faction]:
                    ctx = ContextWrapper.wrap(self.match.channel)
                    ctx.author = user
                    msg = await self.do_pick(ctx, player.active.team, faction)
                    if msg:
                        await self.set_faction_msg(msg)
                    break

    async def set_faction_msg(self, msg):
        if self.last_msg:
            await self.last_msg.clear_reactions()
            rem_handler(self.last_msg.id)
        add_handler(msg.id, self.reaction_handler)
        self.last_msg = msg
        await self.reaction_handler.auto_add_reactions(msg)

    @meta.public
    async def sub(self, subbed):
        """ Substitute a player by another one picked at random \
            in the lobby.
            
            Parameters
            ----------
            subbed : Player
                Player to be substituted
        """
        # Get a new player for substitution
        new_player = await common.get_substitute(self.match)
        if not new_player:
            return

        # Get active version of the player and clean the player object
        a_sub = subbed.active
        subbed.on_player_clean()
        team = a_sub.team
        # Args for the display later
        args = [self.match.channel, new_player.mention, a_sub.mention, team.name]

        # Sub the player
        team.sub(a_sub, new_player)

        # Display what happened
        if new_player.active.is_captain:
            await display.SUB_OKAY_CAP.send(*args, match=self.match.proxy)
        else:
            await display.SUB_OKAY_TEAM.send(*args, match=self.match.proxy)

    @meta.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        msg = await display.PK_FACTION_HELP.send(ctx, self.picking_captain.mention)
        await self.set_faction_msg(msg)

    @meta.public
    async def clear(self, ctx):
        if self.last_msg is not None:
            await self.last_msg.clear_reactions()
            rem_handler(self.last_msg.id)
        self.match.clean()
        await display.MATCH_CLEARED.send(ctx)

    @meta.public
    async def pick(self, ctx, captain, args):
        # Don't want a mentioned player
        if len(ctx.message.mentions) != 0:
            msg = await display.PK_FACTION_NOT_PLAYER.send(ctx)

        # All factions are in one word
        elif len(args) != 1:
            msg = await display.PK_NOT_VALID_FACTION.send(ctx)

        # Check for faction string
        elif args[0].upper() not in cfg.i_factions:
            msg = await display.PK_NOT_VALID_FACTION.send(ctx)

        # Else do the pick
        else:
            msg = await self.do_pick(ctx, captain.team, args[0])

        if msg:
            await self.set_faction_msg(msg)

    async def do_pick(self, ctx, team, arg):
        # Get the faction an other team
        faction = cfg.i_factions[arg.upper()]
        other = self.match.teams[team.id - 1]

        # Check if the other team already picked it
        if other.faction == faction:
            msg = await display.PK_FACTION_ALREADY.send(ctx)
            return msg

        # If not, select the faction and give turn to other team
        team.faction = faction
        common.switch_turn(self, team)
        self.match.audio_bot.faction_pick(team)

        # If other team didn't pick yet:
        if other.faction == 0:
            msg = await display.PK_FACTION_OK_NEXT.send(self.match.channel, team.name, cfg.factions[team.faction],
                                                        other.captain.mention)
            self.reaction_handler.rem_reaction(cfg.emojis[arg.lower()])
            return msg

        # Else, over, all teams have selected a faction
        await display.PK_FACTION_OK.send(ctx, team.name, cfg.factions[team.faction])
        await self.last_msg.clear_reactions()
        rem_handler(self.last_msg.id)
        self.match.on_faction_pick_over()
