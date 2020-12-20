
from display import send, SendCtx
from lib.tasks import loop

import modules.config as cfg

from modules.enumerations import MatchStatus, PlayerStatus
from modules.reactions import ReactionHandler, add_handler, rem_handler
from modules.exceptions import UserLackingPermission, AlreadyPicked

import match_process.common as common
from asyncio import sleep

class MapPicking(common.Process, status=MatchStatus.IS_MAPPING):

    def __init__(self, match):
        self.match = match
        self.last_msg = None
        self.picking_captain = None
        self.reaction_handler = ReactionHandler(rem_bot_react = True)
        self.add_callbacks(self.reaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        self.picking_captain = self.match.teams[1].captain

        super().__init__(match, self.picking_captain)


    @common.init_loop
    async def init(self, picker):
        await sleep(0)
        self.match.audio_bot.select_factions()
        msg = await send("PK_OK_FACTION", self.match.channel, picker.mention, match=self.match.proxy)
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
                    ctx = SendCtx.wrap(self.match.channel)
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

    @common.is_public
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
        args = [self.match.channel, new_player.mention, a_sub.mention,\
                team.name]

        # Sub the player
        team.sub(a_sub, new_player)

        # Set display according to the context
        if new_player.active.is_captain:
            display = "SUB_OKAY_CAP"
        else:
            display = "SUB_OKAY_TEAM"

        # Display what happened
        await send(display, *args, match=self.match.proxy)


    @common.is_public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        msg = await send("PK_FACTION_HELP", ctx, self.picking_captain.mention)
        await self.set_faction_msg(msg)


    @common.is_public
    async def pick(self, ctx, captain, args):
        # Don't want a mentioned player
        if len(ctx.message.mentions) != 0:
            msg = await send("PK_FACTION_NOT_PLAYER", ctx)

        # All factions are in one word
        elif len(args) != 1:
            msg = await send("PK_NOT_VALID_FACTION", ctx)

        # Check for faction string
        elif args[0].upper() not in cfg.i_factions:
            msg = await send("PK_NOT_VALID_FACTION", ctx)

        # Else do the pick
        else:
            msg = await self.do_pick(ctx, captain.team, args[0])

        if msg:
            await self.set_faction_msg(msg)


    async def do_pick(self, ctx, team, arg):
        # Get the faction an other team
        faction = cfg.i_factions[arg.upper()]
        other = self.match.teams[team.id-1]

        # Check if the other team already picked it
        if other.faction == faction:
            msg = await send("PK_FACTION_ALREADY", ctx)
            return msg

        # If not, select the faction and give turn to other team
        team.faction = faction
        common.switch_turn(self, team)
        self.match.audio_bot.faction_pick(team)

        # If other team didn't pick yet:
        if other.faction == 0:
            msg = await send("PK_FACTION_OK_NEXT", self.match.channel, team.name, cfg.factions[team.faction], other.captain.mention)
            self.reaction_handler.rem_reaction(cfg.emojis[arg.lower()])
            return msg

        # Else, over, all teams have selected a faction
        await send("PK_FACTION_OK", ctx, team.name, cfg.factions[team.faction])
        await self.last_msg.clear_reactions()
        rem_handler(self.last_msg.id)
        self.match.on_faction_pick_over()