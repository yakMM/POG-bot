from display.strings import AllStrings as display
from lib.tasks import loop

from general.enumerations import MatchStatus, PlayerStatus
from general.exceptions import ElementNotFound
from random import choice as random_choice

from classes.teams import Team
from classes.players import TeamCaptain, ActivePlayer, get_player

import match_process.common_picking as common
import match_process.meta as meta


class PlayerPicking(meta.Process, status=MatchStatus.IS_PICKING):

    def __init__(self, match, p_list):
        self.match = match
        self.players = dict()
        self.picking_captain = None

        for p in p_list:
            self.players[p.id] = p
            p.on_match_selected(self.match.proxy)

        super().__init__(match)

    @meta.public
    def get_left_players_pings(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        pings = [p.mention for p in self.players.values()]
        return pings

    @meta.public
    async def clear(self, ctx):
        await self.match.clean()
        await display.MATCH_CLEARED.send(ctx)

    def find_captain(self):
        """ Pick at random a captain.
            TODO: Base this pick on some kind of stats or a role

            Returns
            -------
            captain : Player
                The player designated as captain.
        """
        return random_choice(list(self.players))

    @meta.init_loop
    async def init(self):
        """ Init the match channel, ping players, find two captains \
            and ask them to start picking players.
        """
        # Inform players of match init
        players_ping = " ".join(p.mention for p in self.players.values())
        self.match.audio_bot.drop_match()
        await display.MATCH_INIT.send(self.match.channel, players_ping)

        # Initialize teams
        self.match.teams[0] = Team(0, f"Team 1", self.match.proxy)
        self.match.teams[1] = Team(1, f"Team 2", self.match.proxy)

        # Find two captains, first one will pick first
        for i in range(2):
            p_key = self.find_captain()
            self.match.teams[i].add_player(TeamCaptain, self.players.pop(p_key))
        self.match.teams[0].captain.is_turn = True
        self.picking_captain = self.match.teams[0].captain

        # Ready for players to pick
        self.match.audio_bot.select_teams()
        await display.MATCH_SHOW_PICKS.send(self.match.channel, self.match.teams[0].captain.mention,
                                            match=self.match.proxy)

    @meta.public
    def demote(self, captain: TeamCaptain):
        """ Demote player from its TeamCaptain position.
            Put the demoted player in the team as a regular player.
            
            Parameters
            ----------
            captain : TeamCaptain
                Player to be demoted
        """
        # Check if some players were already picked
        team = captain.team

        # Get a new captain
        key = self.find_captain()
        # Sub the old captain for the new one
        team.sub(captain, self.players.pop(key))

        # Add demoted player to team, update its status
        player = captain.on_resign()
        team.add_player(ActivePlayer, player)

        # It's other team captain's time to pick
        other = common.switch_turn(self, team)

        # Check if no player left to pick
        self.pick_check(other)

    @meta.public
    async def sub(self, ctx, subbed):
        """ Substitute a player by another one picked at random \
            in the lobby.
            
            Parameters
            ----------
            subbed : Player
                Player to be substituted
        """
        # Get a new player for substitution
        new_player = await common.get_substitute(ctx, self.match)
        if not new_player:
            return

        # If subbed one has not been picked
        if subbed.status is PlayerStatus.IS_MATCHED:
            # Remove them fro the player list
            del self.players[subbed.id]
            # Put the new player instead
            self.players[new_player.id] = new_player
            # Clean subbed one and send message
            subbed.on_player_clean()
            await display.SUB_OKAY.send(self.match.channel, new_player.mention, subbed.mention, match=self.match.proxy)
            return

            # If subbed one has already been picked
        if subbed.status is PlayerStatus.IS_PICKED:
            # Get active version of the player and clean the player object
            a_sub = subbed.active
            subbed.on_player_clean()
            team = a_sub.team
            # Args for the display later
            args = [self.match.channel, new_player.mention, a_sub.mention, team.name]
            # If subbed is a captain
            if a_sub.is_captain:
                # Add the new player in the pool of players
                self.players[new_player.id] = new_player
                # Elect a new captain from the list
                key = self.find_captain()
                # Replace subbed by the new captain
                team.sub(a_sub, self.players.pop(key))
                # If new player is captain
                if key == new_player.id:
                    await display.SUB_OKAY_CAP.send(*args, match=self.match.proxy)
                # Else if captain is someone else
                else:
                    args.append(team.captain.mention)
                    args.append(team.name)
                    await display.SUB_OKAY_NO_CAP.send(*args, match=self.match.proxy)
            # If subbed is not a captain, just replace them by new player
            # in their team
            else:
                team.sub(a_sub, new_player)
                await display.SUB_OKAY_TEAM.send(*args, match=self.match.proxy)

    @meta.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        await display.PK_PLAYERS_HELP.send(ctx, self.picking_captain.mention)

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
            await display.PK_NO_ARG.send(ctx)
            return

        # If more than one mention, can'pick a player
        if len(ctx.message.mentions) > 1:
            await display.PK_TOO_MUCH.send(ctx)
            return

        # Try to get the player object from the mention
        try:
            picked = get_player(ctx.message.mentions[0].id)
        except ElementNotFound:
            # Player isn't even registered in the system...
            await display.PK_INVALID.send(ctx)
            return

        # If the player is not in the list, can'be picked
        if picked.id not in self.players:
            await display.PK_INVALID.send(ctx)
            return

        # Do selection
        team = captain.team
        self.do_pick(team, picked)

        # If player pick is over
        if len(self.players) == 0:
            await display.PK_OK_2.send(ctx, match=self.match.proxy)
        # Else ping the other captain
        else:
            other = self.match.teams[team.id - 1]
            await display.PK_OK.send(ctx, other.captain.mention, match=self.match.proxy)

    def do_pick(self, team: Team, player) -> TeamCaptain:
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
        await display.PK_LAST.send(self.match.channel, p.mention, team.name, match=self.match.proxy)
