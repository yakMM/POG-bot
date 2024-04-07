# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus

import classes
import modules.config as cfg
import modules.database as db
import modules.loader as loader
import modules.roles as roles
import modules.census as census
import modules.lobby as lobby
import modules.tools as tools
import modules.accounts_handler as accounts_sheet
import modules.spam_checker as spam_checker
import asyncio
from lib.tasks import loop, Loop

from match.classes.match import Match

from classes import Player

log = getLogger("pog_bot")


class AdminCog(commands.Cog, name='admin'):
    """
    Register cog, handle the admin commands
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        can_use = roles.is_admin(ctx.author)
        if can_use:
            _log_command(ctx)
        return can_use

    """
    Admin commands

    =clear (clear lobby or match)
    =base (select a base)

    """

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def clear(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:  # clear lobby
            if lobby.clear_lobby():
                await disp.LB_CLEARED.send(ctx, names_in_lobby=lobby.get_all_names_in_lobby())
                return
            await disp.LB_EMPTY.send(ctx)
            return
        # clear a match channel
        if ctx.channel.id in cfg.channels["matches"]:
            match = Match.get(ctx.channel.id)
            await match.command.clear(ctx)
            return
        await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")

    @commands.command()
    @commands.guild_only()
    async def unregister(self, ctx):
        if not await _check_channels(ctx, cfg.channels["register"]):
            return
        player = await get_check_player(ctx)
        if not player:
            return
        if player.is_lobbied:
            lobby.remove_from_lobby(player)
            await disp.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention,
                                     names_in_lobby=lobby.get_all_names_in_lobby())
        if not player.match:
            try:
                await db.async_db_call(db.remove_element, "users", player.id)
            except db.DatabaseError:
                pass  # ignored if not yet in db
            await roles.remove_roles(player.id)
            player.remove()
            await disp.RM_OK.send(ctx)
            return
        await disp.RM_IN_MATCH.send(ctx)

    @commands.command()
    @commands.guild_only()
    async def rename(self, ctx, *args):
        if not _check_channels(ctx, cfg.channels["register"]):
            return
        player = await get_check_player(ctx)
        if not player:
            return
        if len(args) == 0:
            await disp.WRONG_USAGE.send(ctx, ctx.command.name)
            return
        new_name = " ".join(args)
        if await player.change_name(new_name):
            await disp.RM_NAME_CHANGED.send(ctx, player.mention, new_name)
        else:
            await disp.RM_NAME_INVALID.send(ctx)

    @commands.command()
    @commands.guild_only()
    async def check(self, ctx, *args):
        if not await _check_channels(ctx, cfg.channels["matches"]):
            return
        match = Match.get(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            # Match is not active
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        for arg in args:
            try:
                result = match.change_check(arg)
                await disp.MATCH_CHECK_CHANGED.send(ctx, arg, "enabled" if result else "disabled")
            except KeyError:
                await disp.INVALID_STR.send(ctx, arg)

    @commands.command()
    @commands.guild_only()
    async def spam(self, ctx, *args):
        if len(args) == 1:
            arg = args[0]
        else:
            await disp.WRONG_USAGE.send(ctx, ctx.command.name)
            return
        if arg == "clear":
            spam_checker.clear_spam_list()
            await disp.SPAM_CLEARED.send(ctx)
            return
        if arg == "debug":
            all_spammers = spam_checker.debug()
            giga_string = ""
            for k in all_spammers.keys():
                p = Player.get(k)
                if p:
                    giga_string += f"\nSpammer: {p.mention}, id[{p.id}], name: [{p.name}], " \
                                   f"spam value: [{all_spammers[k]}]"
                else:
                    giga_string += f"\nSpammer: id[{k}], spam value: [{all_spammers[k]}]"
            await disp.SPAM_DEBUG.send(ctx, giga_string)
            return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def lobby(self, ctx, *args):
        if ctx.channel.id != cfg.channels["lobby"]:
            await disp.WRONG_CHANNEL.send(ctx, ctx.command.name, f'<#{cfg.channels["lobby"]}>')
            return
        if len(args) > 0 and args[0] == "restore":
            for mention in ctx.message.mentions:
                try:
                    p_id = mention.id
                    player = Player.get(int(p_id))
                    if player and not lobby.is_lobby_stuck() and player.is_registered and not player.is_lobbied:
                        lobby.add_to_lobby(player)
                except ValueError:
                    pass
            await disp.LB_QUEUE.send(ctx, names_in_lobby=lobby.get_all_names_in_lobby())
            return
        if len(args) > 0 and args[0] == "save":
            lb = lobby.get_all_ids_in_lobby()
            await db.async_db_call(db.set_field, "restart_data", 0, {"last_lobby": lb})
            await disp.LB_SAVE.send(ctx)
            return
        if len(args) > 0 and args[0] == "get":
            lb = lobby.get_all_ids_in_lobby()
            await disp.LB_GET.send(ctx, " ".join([str(p_id) for p_id in lb]))
            return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def timeout(self, ctx, *args):
        if len(args) == 1 and args[0] == "help":
            await disp.RM_TIMEOUT_HELP.send(ctx)
            return
        if len(ctx.message.mentions) != 1:
            await disp.RM_MENTION_ONE.send(ctx)
            return
        player = Player.get(ctx.message.mentions[0].id)
        if not player:
            # player isn't even registered in the system...
            player = Player(ctx.message.mentions[0].id, ctx.message.mentions[0].name)
            await db.async_db_call(db.set_element, "users", player.id, player.get_data())
        if player.is_lobbied:
            lobby.remove_from_lobby(player)
            await disp.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention,
                                     names_in_lobby=lobby.get_all_names_in_lobby())
        if player.match:
            await disp.RM_IN_MATCH.send(ctx)
            return

        if len(args) == 0:
            if player.is_timeout:
                await disp.RM_TIMEOUT_INFO.send(ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
                return
            await roles.role_update(player)
            await roles.perms_muted(False, player.id)
            await disp.RM_TIMEOUT_NO.send(ctx)
            return
        # =timeout @player remove
        if len(args) == 1 and args[0] == 'remove':
            player.timeout = 0
            await player.db_update("timeout")
            await disp.RM_TIMEOUT_FREE.send(ctx, player.mention)
            await roles.role_update(player)
            await roles.perms_muted(False, player.id)
            return
        # Check if command is correct (=timeout @player 12 d)

        time = tools.time_calculator(" ".join(args))
        if time == 0:
            await disp.RM_TIMEOUT_INVALID.send(ctx)
            return

        end_time = tools.timestamp_now() + time
        player.timeout = end_time
        await roles.role_update(player)
        await player.db_update("timeout")
        await roles.perms_muted(True, player.id)
        if ctx.channel.id != cfg.channels['muted']:
            await disp.RM_TIMEOUT.send(ctx, player.mention, dt.utcfromtimestamp(end_time).strftime("%Y-%m-%d %H:%M UTC"))
        await disp.RM_TIMEOUT.send(ContextWrapper.channel(cfg.channels['muted']), player.mention, dt.utcfromtimestamp(end_time).strftime("%Y-%m-%d %H:%M UTC"))

    @commands.command()
    @commands.guild_only()
    async def pog(self, ctx, *args):
        if len(args) == 0:
            await disp.BOT_VERSION.send(ctx, cfg.VERSION, loader.is_all_locked())
            return
        arg = args[0]
        if arg == "version":
            await disp.BOT_VERSION.send(ctx, cfg.VERSION, loader.is_all_locked())
            return
        if arg == "lock":
            if loader.is_all_locked():
                await disp.BOT_ALREADY.send(ctx, "locked")
                return
            loader.lock_all(self.client)
            await disp.BOT_LOCKED.send(ctx)
            return
        if arg == "unlock":
            if not loader.is_all_locked():
                await disp.BOT_ALREADY.send(ctx, "unlocked")
                return
            loader.unlock_all(self.client)
            await disp.BOT_UNLOCKED.send(ctx)
            return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def fstart(self, ctx, *args):
        if ctx.channel.id != cfg.channels["lobby"]: # only allowed in lobby channel
            await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")
            return

        if (lobby.get_lobby_len() == 0): # don't allow starting with 0 players
            await disp.LB_FORCE_START_ZERO_PLAYERS.send(ctx)
            return

        # TODO: is this check needed? can you successfully have a 5v6 lobby?
        if (lobby.get_lobby_len() % 2 != 0):
            await disp.LB_FORCE_START_NOT_EVEN.send(ctx)
            return

        # start the match!
        lobby._start_match_from_full_lobby()
        await disp.LB_FORCE_START.send(ctx, f"<@{ctx.author.id}>")

    @commands.command()
    @commands.guild_only()
    async def accounts(self, ctx, *args):
        if len(args) == 0:
            await disp.ACC_ALL_HANDOUT.send(ctx, "enabled" if lobby.accounts_enabled() else "disabled")
            return
        arg = args[0]
        if arg == "unlock":
            if lobby.accounts_enabled():
                await disp.ACC_ALL_HANDOUT.send(ctx, "already enabled")
                return
            lobby.set_lobby_accounts_enabled(True)
            await disp.ACC_ALL_HANDOUT.send(ctx, "enabled")
            return
        if arg == "lock":
            if not lobby.accounts_enabled():
                await disp.ACC_ALL_HANDOUT.send(ctx, "already disabled")
                return
            lobby.set_lobby_accounts_enabled(False)
            removed = []
            for p in lobby.get_all_in_lobby():
                if not p.has_own_account():
                    lobby.remove_from_lobby(p)
                    removed.append(p.mention)
            await disp.RM_LOBBY_ACC.send(ContextWrapper.channel(cfg.channels["lobby"]),
                                         ' '.join(removed),
                                         names_in_lobby=lobby.get_all_names_in_lobby())
            await disp.ACC_ALL_HANDOUT.send(ctx, "disabled")
            return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def channel(self, ctx, *args):
        if ctx.channel.id not in [cfg.channels["register"], cfg.channels["lobby"], *cfg.channels["matches"]]:
            await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")
            return
        if len(args) == 1:
            arg = args[0]
            if arg == "freeze":
                await roles.channel_freeze(True, ctx.channel.id)
                await disp.BOT_FROZEN.send(ctx)
                return
            if arg == "unfreeze":
                await roles.channel_freeze(False, ctx.channel.id)
                await disp.BOT_UNFROZEN.send(ctx)
                return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def reload(self, ctx, *args):
        if len(args) == 1:
            arg = args[0]
            loop = asyncio.get_event_loop()
            if arg == "accounts":
                await loop.run_in_executor(None, accounts_sheet.init, cfg.GAPI_JSON)
                await disp.BOT_RELOAD.send(ctx, "Accounts")
                return
            if arg == "weapons":
                classes.Weapon.clear_all()
                await loop.run_in_executor(None, db.get_all_elements, classes.Weapon, "static_weapons")
                await disp.BOT_RELOAD.send(ctx, "Weapons")
                return
            if arg == "bases":
                classes.Base.clear_all()
                await loop.run_in_executor(None, db.get_all_elements, classes.Base, "static_bases")
                await disp.BOT_RELOAD.send(ctx, "Bases")
                return
            if arg == "config":
                await loop.run_in_executor(None, cfg.get_config, cfg.LAUNCH_STR)
                await roles.update_rule_msg()
                await loop.run_in_executor(None, db.init, cfg.database)
                await disp.BOT_RELOAD.send(ctx, "Config")
                return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @commands.command(aliases=['rm'])
    @commands.guild_only()
    async def remove(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:
            player = await get_check_player(ctx)
            if not player:
                return
            if player.is_lobbied:
                lobby.remove_from_lobby(player)
                await disp.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention,
                                         names_in_lobby=lobby.get_all_names_in_lobby())
                return
            await disp.RM_NOT_LOBBIED.send(ctx)
            return
        # if ctx.channel.id == cfg.channels["register"]:
        #     player = await get_check_player(ctx)
        #     if not player:
        #         return
        #     #TODO: remove ig names
        else:
            await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")

    @commands.command()
    @commands.guild_only()
    async def captain(self, ctx):
        if not await _check_channels(ctx, cfg.channels["matches"]):
            return
        match = Match.get(ctx.channel.id)
        player = await get_check_player(ctx)
        if not player:
            return
        if match.status is not MatchStatus.IS_CAPTAIN:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return
        if player.match is match and not player.active:
            await match.on_volunteer(player)
        else:
            await disp.CAP_NOT_OK.send(ctx, player.mention)


def setup(client):
    client.add_cog(AdminCog(client))

def _log_command(ctx):
    Loop(coro=_log_admin_command_impl, count=1).start(ctx)

async def _log_admin_command_impl(ctx):
    await disp.ADMIN_MSG_LOG.send(ContextWrapper.channel(cfg.channels["spam"]), ctx.author.name, ctx.author.id, ctx.message.content, ctx.channel.id)

async def _check_channels(ctx, channels):
    if not isinstance(channels, list):
        channels = [channels]
    if ctx.channel.id not in channels:
        await disp.WRONG_CHANNEL.send(ctx, ctx.command.name, ", ".join(f"<#{c_id}>" for c_id in channels))
        return False
    return True

async def get_check_player(ctx):
    if len(ctx.message.mentions) != 1:
        await disp.RM_MENTION_ONE.send(ctx)
        return
    player = Player.get(ctx.message.mentions[0].id)
    if not player:
        # player isn't even registered in the system...
        await disp.RM_NOT_IN_DB.send(ctx)
        return
    return player
