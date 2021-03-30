from display import AllStrings as disp, ContextWrapper
from lib.tasks import loop

from match_process import MatchStatus
from random import choice as random_choice

from classes.teams import Team
from classes import TeamCaptain, ActivePlayer, Player

import match_process.common_picking as common
import match_process.meta as meta
from .captain_validator import CaptainValidator

import modules.roles as roles

from modules.roles import modify_match_channel
import modules.config as cfg


class PlayerPicking(meta.Process, status=MatchStatus.IS_PICKING):

    def __init__(self, match, p_list):
        self.match = match
        self.players = dict()
        self.picking_captain = None

        self.sub_handler = common.SubHandler(self.match.proxy, self.do_sub)

        for p in p_list:
            self.players[p.id] = p

        super().__init__(match)

    @meta.init_loop
    async def init(self):
        """ Init the match channel, ping players, find two captains \
            and ask them to start picking players.
        """

        self.match.teams[0].captain.is_turn = True
        self.match.teams[1].captain.is_turn = False
        self.picking_captain = self.match.teams[0].captain

        # Ready for players to pick
        await disp.MATCH_SHOW_PICKS.send(self.match.channel, self.match.teams[0].captain.mention,
                                         match=self.match.proxy)

    async def do_sub(self, subbed, force_player=None):
        """ Substitute a player by another one picked at random \
            in the lobby.

            Parameters
            ----------
            subbed : Player
                Player to be substituted
        """

        # If subbed one has already been picked
        if subbed.active:
            await common.after_pick_sub(self.match, subbed, force_player)
        else:
            # Get a new player for substitution
            new_player = await common.get_substitute(self.match, subbed, force_player)
            if not new_player:
                return
            # Remove them fro the player list
            del self.players[subbed.id]
            # Put the new player instead
            self.players[new_player.id] = new_player
            # Clean subbed one and send message
            subbed.on_player_clean()
            await disp.SUB_OKAY.send(self.match.channel, new_player.mention, subbed.mention, match=self.match.proxy)
            return

    @meta.public
    def get_left_players_pings(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        pings = [f"{p.mention} ({p.name})" for p in self.players.values()]
        return pings

    @meta.public
    async def clear(self, ctx):
        await self.sub_handler.clean()
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @meta.public
    async def sub_request(self, ctx, captain, args):
        await self.sub_handler.sub_request(ctx, captain, args)

    @meta.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        await disp.PK_PLAYERS_HELP.send(ctx, self.picking_captain.mention)

    @meta.public
    async def pick(self, ctx, captain, args):
        """ Pick a player, and display what happened.
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
            captain : TeamCaptain
                The captain currently picking
            args : list
                Differents arguments found in the command (not used in this case)
        """

        # If no mention, can't pick a player
        if len(ctx.message.mentions) == 0:
            await disp.PK_NO_ARG.send(ctx)
            return

        # If more than one mention, can't pick a player
        if len(ctx.message.mentions) > 1:
            await disp.PK_TOO_MUCH.send(ctx)
            return

        # Try to get the player object from the mention
        picked = Player.get(ctx.message.mentions[0].id)
        if not picked:
            # Player isn't even registered in the system...
            await disp.PK_INVALID.send(ctx)
            return

        # If the player is not in the list, can'be picked
        if picked.id not in self.players:
            await disp.PK_INVALID.send(ctx)
            return

        # Do selection
        team = captain.team
        self.do_pick(team, picked)

        # If player pick is over
        if len(self.players) == 0:
            await disp.PK_OK_2.send(ctx, match=self.match.proxy)
        # Else ping the other captain
        else:
            other = self.match.teams[team.id - 1]
            await disp.PK_OK.send(ctx, other.captain.mention, match=self.match.proxy)

    def do_pick(self, team: Team, player):
        """ Pick a player.
            
            Parameters
            ----------
            team : Team
                The team picking the player.
            player : Player
                Player picked.
        """
        # Remove player from the list and add them to the team
        team.add_player(ActivePlayer, player)
        self.players.pop(player.id)

        # It's other team captain's time to pick
        other = common.switch_turn(self, team)

        # Check if no player left to pick
        self.pick_check(other)

    def pick_check(self, other):
        """ Check pick progress, auto pick players if needed.
            
            Parameters
            ----------
            team : Team
                The team picking the player.
            player : Player
                Player picked.

            Returns
            -------
            other.captain : TeamCaptain
                The captain of the next team who can pick.
        """
        # If only one player left, auto-pick them
        if len(self.players) == 1:
            # Get last player
            p = [*self.players.values()][0]
            # Pick them
            self.do_pick(other, p)
            # Ping them
            self.ping_last_player.start(other, p)
        # If no player left, trigger the next step
        elif len(self.players) == 0:
            # Start next step
            self.match.on_player_pick_over()

    @loop(count=1)
    async def ping_last_player(self, team, p):
        await disp.PK_LAST.send(self.match.channel, p.mention, team.name, match=self.match.proxy)
