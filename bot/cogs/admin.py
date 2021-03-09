# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

import modules.config as cfg
from general.enumerations import SelStatus, MatchStatus, PlayerStatus
from display.strings import AllStrings as display
from display.classes import ContextWrapper
from general.exceptions import ElementNotFound, DatabaseError
from modules.database import remove_player as db_remove
from modules.loader import lock_all, unlock_all, is_all_locked
from modules.roles import force_info, role_update, is_admin, perms_muted, channel_freeze
from modules.census import get_offline_players
from modules.lobby import clear_lobby, get_all_names_in_lobby, remove_from_lobby, is_lobby_stuck, add_to_lobby, get_all_ids_in_lobby

from match_process import Match

from classes.players import remove_player, get_player, Player

log = getLogger("pog_bot")


class AdminCog(commands.Cog, name='admin'):
    """
    Register cog, handle the admin commands
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        return is_admin(ctx.author)

    """
    Admin Commands

    =clear (clear lobby or match)
    =base (select a base)

    """

    @commands.command()
    @commands.guild_only()
    async def clear(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:  # clear lobby
            if clear_lobby():
                await display.LB_CLEARED.send(ctx, names_in_lobby=get_all_names_in_lobby())
                return
            await display.LB_EMPTY.send(ctx)
            return
        # clear a match channel
        if ctx.channel.id in cfg.channels["matches"]:
            match = Match.get(ctx.channel.id)
            if match.status is MatchStatus.IS_FREE:
                await display.MATCH_NO_MATCH.send(ctx, ctx.command.name)
                return
            if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_RESULT, MatchStatus.IS_RUNNING):
                await display.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
                return
            await display.MATCH_CLEAR.send(ctx)
            await match.clear(ctx)
            return
        await display.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")

    @commands.command()
    @commands.guild_only()
    async def basea(self, ctx, *args):
        channel_id = ctx.channel.id
        if channel_id not in cfg.channels["matches"]:
            await display.WRONG_CHANNEL.send(ctx, ctx.command.name, " channels " + ", ".join(f'<#{id}>' for id in cfg.channels["matches"]))
            return
        match = Match.get(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            await display.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT, MatchStatus.IS_RUNNING):
            await display.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return
        sel = match.base_selector
        if len(args) == 1 and args[0] ==  "confirm":
            match.confirm_base()
            await display.MATCH_BASE_SELECTED.send(ctx, sel.base.name, sel=sel)
            return
        # Handle the actual base selection
        result = await sel.do_selection_process(ctx, args)
        if sel.status is not SelStatus.IS_SELECTED:
            return
        if sel.is_booked:
            await display.BASE_BOOKED.send(ctx, ctx.author.mention, sel.base.name)
            return
        elif result:
            match.confirm_base()
            await display.MATCH_BASE_SELECTED.send(ctx, sel.base.name, sel=sel)

    @commands.command()
    @commands.guild_only()
    async def unregister(self, ctx):
        player = await _remove_checks(ctx, cfg.channels["register"])
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            remove_from_lobby(player)
            await display.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention, names_in_lobby=get_all_names_in_lobby())
        if player.status in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            try:
                await db_remove(player)
            except DatabaseError:
                pass  # ignored if not yet in db
            await force_info(player.id)
            remove_player(player)
            await display.RM_OK.send(ctx)
            return
        await display.RM_IN_MATCH.send(ctx)
    
    @commands.command()
    @commands.guild_only()
    async def remove(self, ctx):
        player = await _remove_checks(ctx, cfg.channels["lobby"])
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            remove_from_lobby(player)
            await display.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention, names_in_lobby=get_all_names_in_lobby())
            return
        await display.RM_NOT_LOBBIED.send(ctx)
    
    @commands.command()
    @commands.guild_only()
    async def demote(self, ctx):
        player = await _remove_checks(ctx, cfg.channels["matches"])
        if player is None:
            return
        if player.status is not PlayerStatus.IS_PICKED:
            await display.RM_DEMOTE_NO.send(ctx)
            return
        match = Match.get(ctx.channel.id)
        if player.match.channel.id != match.channel.id:
            await display.PK_WRONG_CHANNEL.send(ctx,  player.match.channel.id)
            return
        a_player = player.active
        if not a_player.is_captain:
            await display.RM_DEMOTE_NO.send(ctx)
            return
        if not a_player.is_turn:
            await display.RM_DEMOTE_NO_TURN.send(ctx)
            return
        team = a_player.team
        match.demote(a_player)
        await display.RM_DEMOTE_OK.send(ctx, team.captain.mention, team.name, match = match)

    @commands.command()
    @commands.guild_only()
    async def ts3(self, ctx):
        if ctx.channel.id not in cfg.channels["matches"]:
            await display.WRONG_CHANNEL.send(ctx, ctx.command.name, ", ".join(f"<#{c_id}>" for c_id in cfg.channels["matches"]))
            return
        match = Match.get(ctx.channel.id)
        match.ts3_test()

    @commands.command()
    @commands.guild_only()
    async def lobby(self, ctx, *args):
        if ctx.channel.id != cfg.channels["lobby"]:
            await display.WRONG_CHANNEL.send(ctx, ctx.command.name, f'<#{cfg.channels["lobby"]}>')
            return
        if len(args)>0 and args[0] == "restore":
            for p_id in args[1:]:
                try:
                    player = get_player(int(p_id))
                    if not is_lobby_stuck() and player.status is PlayerStatus.IS_REGISTERED:
                        add_to_lobby(player)
                except (ElementNotFound, ValueError):
                    pass
            await display.LB_QUEUE.send(ctx, names_in_lobby=get_all_names_in_lobby())
            return
        if len(args)>0 and args[0] == "get":
            await display.LB_GET.send(ctx, " ".join(get_all_ids_in_lobby()))
            return
        await display.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def timeout(self, ctx, *args):
        if len(args) == 0:
            await display.RM_TIMEOUT_HELP.send(ctx)
            return
        if len(args) == 1 and args[0] == "help":
            await display.RM_TIMEOUT_HELP.send(ctx)
            return
        if len(ctx.message.mentions) != 1:
            await display.RM_MENTION_ONE.send(ctx)
            return
        try:
            player = get_player(ctx.message.mentions[0].id)
        except ElementNotFound:
            # player isn't even registered in the system...
            player = Player(ctx.message.mentions[0].id, ctx.message.mentions[0].name)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            remove_from_lobby(player)
            await display.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention, names_in_lobby=get_all_names_in_lobby())
        if player.status not in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            await display.RM_IN_MATCH.send(ctx)
            return
        if len(args) == 1:
            if player.is_timeout:
                await display.RM_TIMEOUT_INFO.send(ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
                return
            await role_update(player)
            await perms_muted(False, player.id)
            await display.RM_TIMEOUT_NO.send(ctx)
            return
        # =timeout @player remove
        if len(args) == 2 and args[1] == 'remove':
            if not player.is_timeout:
                await display.RM_TIMEOUT_ALREADY.send(ctx)
                return
            player.timeout = 0
            await player.db_update("timeout")
            await display.RM_TIMEOUT_FREE.send(ctx, player.mention)
            await role_update(player)
            await perms_muted(False, player.id)
            return
        # Check if command is correct (=timeout @player 12 d)
        if len(args) != 3:
            await display.RM_TIMEOUT_INVALID.send(ctx)
            return
        if args[2] in ['d', 'day', 'days']:
            time = 86400
        elif args[2] in ['h', 'hour', 'hours']:
            time = 3600
        elif args[2] in ['m', 'min', 'mins', 'minute', 'minutes']:
            time = 60
        else:
            await display.RM_TIMEOUT_INVALID.send(ctx)
            return
        try:
            time *= int(args[1])
            if time == 0:
                raise ValueError
        except ValueError:
            await display.RM_TIMEOUT_INVALID.send(ctx)
            return
        end_time = int(dt.timestamp(dt.now()))+time
        player.timeout = end_time
        await role_update(player)
        await player.db_update("timeout")
        await perms_muted(True, player.id)
        await display.RM_TIMEOUT.send(ctx, player.mention, dt.utcfromtimestamp(end_time).strftime("%Y-%m-%d %H:%M UTC"))

    @commands.command()
    @commands.guild_only()
    async def pog(self, ctx, *args):
        if len(args) == 0:
            await display.BOT_VERSION.send(ctx, cfg.VERSION, is_all_locked())
            return
        arg = args[0]
        if arg == "version":
            await display.BOT_VERSION.send(ctx, cfg.VERSION, is_all_locked())
            return
        if arg == "lock":
            if is_all_locked():
                await display.BOT_ALREADY.send(ctx, "locked")
                return
            lock_all(self.client)
            await display.BOT_LOCKED.send(ctx)
            return
        if arg == "unlock":
            if not is_all_locked():
                await display.BOT_ALREADY.send(ctx, "unlocked")
                return
            unlock_all(self.client)
            await display.BOT_UNLOCKED.send(ctx)
            return
        if arg == "ingame":
            if get_offline_players.bypass:
                get_offline_players.bypass = False
                await display.BOT_BP_OFF.send(ctx)
            else:
                get_offline_players.bypass = True
                await display.BOT_BP_ON.send(ctx)
            return
        await display.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def channel(self, ctx, *args):
        if ctx.channel.id not in [cfg.channels["register"], cfg.channels["lobby"], *cfg.channels["matches"]]:
            await display.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")
            return
        if len(args) == 1:
            arg = args[0]
            if arg == "freeze":
                await channel_freeze(True, ctx.channel.id)
                await display.BOT_FROZEN.send(ctx)
                return
            if arg == "unfreeze":
                await channel_freeze(False, ctx.channel.id)
                await display.BOT_UNFROZEN.send(ctx)
                return
        await display.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def sub(self, ctx, *args):
        # Check for match status first maybe?
        player = await _remove_checks(ctx, cfg.channels["matches"])
        if player is None:
            return
        if player.status not in (PlayerStatus.IS_MATCHED, PlayerStatus.IS_PICKED):
            await display.SUB_NO.send(ctx)
            return
        await player.match.sub(player)
        # Display is handled in the sub method, nothing to display here



def setup(client):
    client.add_cog(AdminCog(client))


async def _remove_checks(ctx, channels):
    if not isinstance(channels, list):
        channels = [channels]
    if ctx.channel.id not in channels:
        await display.WRONG_CHANNEL.send(ctx, ctx.command.name, ", ".join(f"<#{c_id}>" for c_id in channels))
        return
    if len(ctx.message.mentions) != 1:
        await display.RM_MENTION_ONE.send(ctx)
        return
    try:
        player = get_player(ctx.message.mentions[0].id)
    except ElementNotFound:
        # player isn't even registered in the system...
        await display.RM_NOT_IN_DB.send(ctx)
        return
    return player
