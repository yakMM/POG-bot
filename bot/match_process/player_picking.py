from display import send, SendCtx
from lib.tasks import loop

from modules.enumerations import MatchStatus, PlayerStatus
from random import choice as random_choice

from classes.teams import Team
from classes.players import TeamCaptain, ActivePlayer

import match_process.common as common


class PlayerPicking:


    @classmethod
    def get_authorized_attributes(this):
        attr_list = list()
        attr_list.append("left_players_pings")
        attr_list.append("demote")
        attr_list.append("pick")
        attr_list.append("sub")
        return attr_list


    def __init__(self, match, p_list):
        self.players = dict()
        self.match = match

        for p in p_list:
            self.players[p.id] = p
            p.on_match_selected(self.match.proxy)

        self.init.start()


    @property
    def left_players_pings(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        pings = [p.mention for p in self.players.values()]
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


    @loop(count=1)
    async def init(self):
        """ Init the match channel, ping players, find two captains \
            and ask them to start picking players.
        """
        # Inform players of match init
        players_ping = " ".join(p.mention for p in self.players.values())
        self.match.audio_bot.drop_match()
        await send("MATCH_INIT", self.match.channel, players_ping)

        # Initialize teams
        self.match.teams[0] = Team(0, f"Team 1", self.match.proxy)
        self.match.teams[1] = Team(1, f"Team 2", self.match.proxy)

        # Find two captains, first one will pick first
        for i in range(2):
            p_key = self.find_captain()
            self.match.teams[i].add_player(TeamCaptain, self.players.pop(p_key))
        self.match.teams[0].captain.is_turn = True

        # Ready for players to pick
        self.match.status = MatchStatus.IS_PICKING
        self.match.audio_bot.select_teams()
        await send("MATCH_SHOW_PICKS", self.match.channel,\
            self.match.teams[0].captain.mention, match=self.match.proxy)


    def switch_turn(self, team):
        """ Change the team who can pick.

            Parameters
            ----------
            team : Team
                The team who is currently picking.

            Returns
            -------
            other : Team
                The other team who will pick now
        """
        # Toggle turn
        team.captain.is_turn = False
        
        # Get the other team
        other = self.match.teams[team.id - 1]
        other.captain.is_turn = True
        return other


    def demote(self, captain : TeamCaptain):
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
        other = self.switch_turn(team)

        # Check if no player left to pick
        self.pick_check(other)


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

        # If subbed one has not been picked
        if subbed.status is PlayerStatus.IS_MATCHED:
            # Remove them fro the player list
            del self.players[subbed.id]
            # Put the new player instead
            self.players[new_player.id] = new_player
            # Clean subbed one and send message
            subbed.on_player_clean()
            await send("SUB_OKAY", self.match.channel, new_player.mention,\
                                   subbed.mention, match=self.match.proxy)
            return 

        # If subbed one has already been picked
        if subbed.status is PlayerStatus.IS_PICKED:
            # Get active version of the player and clean the player object
            a_sub = subbed.active
            subbed.on_player_clean()
            team = a_sub.team
            # Args for the display later
            args = [self.match.channel, new_player.mention, a_sub.mention,\
                    team.name]
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
                    display = "SUB_OKAY_CAP"
                # Else if captain is someone else
                else:
                    args.append(team.captain.mention)
                    args.append(team.name)
                    display = "SUB_OKAY_NO_CAP"
            # If subbed is not a captain, just replace them by new player
            # in their team
            else:
                a_sub.team.sub(a_sub, new_player)
                display = "SUB_OKAY_TEAM"

            # Display what happened
            await send(display, *args, match=self.match.proxy)


    def pick(self, team : Team, player) -> TeamCaptain:
        """ Pick a player.
            
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
        # Remove player from the list and add them to the team
        team.add_player(ActivePlayer, player)
        self.players.pop(player.id)

        # It's other team captain's time to pick
        other = self.switch_turn(team)

        # Check if no player left to pick
        self.pick_check(other)

        # Return next picker
        return other.captain


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
            # Ping them
            self.ping_last_player.start(other, p)
            # Pick them
            self.pick(other, p)
        # If no player left, trigger the next step
        elif len(self.players) == 0:
            # Start next step
            self.match.on_player_pick_over()


    @loop(count=1)
    async def ping_last_player(self, team, p):
        await send("PK_LAST", self.match.channel, p.mention, team.name, match=self.match.proxy)