from display import AllStrings as disp, ContextWrapper, InteractionContext, views
from lib.tasks import loop

from classes import ActivePlayer, Player, Team

from match.common import get_substitute, after_pick_sub, switch_turn, get_check_captain
from match import MatchStatus
from .process import Process
from match.classes import BaseSelector

import modules.interactions as interactions


class PlayerPicking(Process, status=MatchStatus.IS_PICKING):

    def __init__(self, match, p_list):
        self.match = match
        self.players = dict()

        self.match.base_selector = BaseSelector(self.match, base_pool=True)

        self.interaction_handler = interactions.InteractionHandler(
            views.players_buttons,
            disable_after_use=False,
            single_callback=self.interaction_callback
        )

        self.match.teams[0].captain.is_turn = True
        self.match.teams[1].captain.is_turn = False

        for p in p_list:
            self.players[p.id] = p

        super().__init__(match)

    async def interaction_callback(self, player, interaction_id, interaction, values):
        i_ctx = InteractionContext(interaction)
        captain = await get_check_captain(i_ctx, self.match.proxy)
        if not captain:
            raise interactions.InteractionNotAllowed
        try:
            picked = self.players[int(interaction_id)]
        except (ValueError, KeyError):
            raise interactions.InteractionInvalid(
                f"could not find a player matching interaction_id: {interaction_id}"
            )

        ctx = ContextWrapper.wrap(self.match.channel, author=interaction.user)
        await self.pick_end(ctx, picked, captain, ping_player=True)

    @Process.init_loop
    async def init(self):
        """ Init the match channel, ping players, find two captains \
            and ask them to start picking players.
        """
        # Ready for players to pick
        ctx = self.interaction_handler.get_new_context(self.match.channel)
        await disp.MATCH_SHOW_PICKS.send(ctx, self.match.teams[0].captain.mention,
                                         match=self.match.proxy)

    @property
    def picking_captain(self):
        for tm in self.match.teams:
            if tm.captain.is_turn:
                return tm.captain

    @Process.public
    async def do_sub(self, subbed, force_player=None):
        """ Substitute a player by another one picked at random \
            in the lobby.

            Parameters
            ----------
            subbed : Player
                Player to be substituted
        """
        ctx = self.interaction_handler.get_new_context(self.match.channel)
        # If subbed one has already been picked
        if subbed.active:
            await after_pick_sub(self.match.proxy, subbed.active, force_player, ctx=ctx)
        else:
            # Get a new player for substitution
            new_player = await get_substitute(self.match.proxy, subbed, player=force_player)
            if not new_player:
                return
            # Remove them fro the player list
            del self.players[subbed.id]
            # Put the new player instead
            self.players[new_player.id] = new_player
            # Clean subbed one and send message
            subbed.on_player_clean()
            await disp.SUB_OKAY.send(ctx, new_player.mention, subbed.mention, match=self.match.proxy)
            return

    @Process.public
    def get_left_players(self) -> list:
        """ The list of mentions of all players left to pick.
        """
        return list(self.players.values())

    @Process.public
    def get_current_context(self, ctx):
        return self.interaction_handler.get_new_context(ctx)

    @Process.public
    async def clear(self, ctx):
        for p in self.players.values():
            p.on_player_clean()
        self.interaction_handler.clean()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def pick_status(self, ctx):
        """ Displays the picking status/help
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
        """
        await disp.PK_PLAYERS_HELP.send(ctx, self.picking_captain.mention)

    @Process.public
    async def pick(self, ctx, captain, args):
        """ Pick a player, and display what happened.
            
            Parameters
            ----------
            ctx : Context
                discord command context, contains the message received
            captain : ActivePlayer
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
        await self.pick_end(ctx, picked, captain)

    async def pick_end(self, ctx, picked, captain, ping_player=False):
        # Do selection
        team = captain.team
        self.do_pick(team, picked)

        # If player pick is over
        if len(self.players) == 0:
            if ping_player:
                await disp.PK_P_OK_2.send(ctx, picked.mention, match=self.match.proxy)
            else:
                await disp.PK_OK_2.send(ctx, match=self.match.proxy)
        # Else ping the other captain
        else:
            other = self.match.teams[team.id - 1]
            ctx = self.interaction_handler.get_new_context(ctx)
            if ping_player:
                await disp.PK_P_OK.send(ctx, picked.mention, other.captain.mention, match=self.match.proxy)
            else:
                await disp.PK_OK.send(ctx, other.captain.mention, match=self.match.proxy)

    def do_pick(self, team: Team, player):
        """
        Pick a player.

        :param team: The team picking the player.
        :param player: Player picked.
        """
        # Remove player from the list and add them to the team
        team.add_player(ActivePlayer, player)
        self.players.pop(player.id)

        # It's other team captain's time to pick
        other = switch_turn(self, team)

        # Check if no player left to pick
        self.pick_check(other)

    def pick_check(self, other):
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
            self.match.ready_next_process()
            self.interaction_handler.clean()
            self.match.plugin_manager.on_teams_done()
            self.match.start_next_process()

    @loop(count=1)
    async def ping_last_player(self, team, p):
        await disp.PK_LAST.send(self.match.channel, p.mention, team.name, match=self.match.proxy)
