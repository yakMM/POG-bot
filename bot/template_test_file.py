# This file is an example of test script for an easier development

from classes import Player
import asyncio
from discord.ext import commands
from logging import getLogger
import modules.config as cfg
import modules.lobby as lobby
import modules.database as db

from match import MatchStatus

from display import ContextWrapper
import modules.tools as tools

log = getLogger("pog_bot")

bot = None


def get_ids():
    # Enter here a list of discord IDS of accounts you wish to use for the testing
    # For example:
    # return [0000, 0000, 0000, 0000]
    from test import ids
    return ids


def test_hand(client):
    ids = get_ids()

    @client.command()
    @commands.guild_only()
    async def x(ctx, *args):
        if len(args) == 0:
            await launch(ctx, ids, 0)
        else:
            await launch(ctx, ids, int(args[0]))

    @client.command()
    @commands.guild_only()
    async def y(ctx):
        await launch(ctx, [20, 21, 22, 23], 2)
        await launch(ctx, ids, 1)

    @client.command()
    @commands.guild_only()
    async def w(ctx, *args):
        time = tools.time_calculator("".join(args))
        ts = tools.timestamp_now() - time
        t_str = tools.time_diff(ts)
        print(t_str)

    global bot
    bot = client


async def launch(ctx, id_list, tier):
    print("TIER 1")
    players = list()
    for p_id in id_list:
        player = Player.get(p_id)
        if not player:
            print(f"user {p_id}")
            user = await bot.fetch_user(p_id)
            player = Player(user.id, user.name)
            await db.async_db_call(db.set_element, "users", player.id, player.get_data())
            await player.register(None)
        players.append(player)

    for p in players:
        lobby.add_to_lobby(p)

    if tier == 1:
        return

    print("TIER 2")
    await asyncio.sleep(1)

    match = players[0].match

    while match.status is not MatchStatus.IS_CAPTAIN:
        await asyncio.sleep(1)

    cap_1_ctx = ContextWrapper.wrap(ctx.channel)
    cap_1_ctx.message = ctx.message
    cap_1_ctx.author = ctx.guild.get_member(players[0].id)
    await match.on_volunteer(players[0])

    cap_2_ctx = ContextWrapper.wrap(ctx.channel)
    cap_2_ctx.message = ctx.message
    cap_2_ctx.author = ctx.guild.get_member(players[1].id)
    await match.on_volunteer(players[1])

    if tier == 2:
        return

    print("TIER 3")
    while match.status is not MatchStatus.IS_PICKING:
        await asyncio.sleep(1)

    picked = await ContextWrapper.user(players[2].id)
    cap_1_ctx.message.mentions.clear()
    cap_1_ctx.message.mentions.append(picked.author)

    await match.command.pick(cap_1_ctx, [""])

    if tier == 3:
        return

    print("TIER 4")

    while match.status is not MatchStatus.IS_FACTION:
        await asyncio.sleep(1)

    cap_2_ctx.message.mentions.clear()
    cap_1_ctx.message.mentions.clear()
    await match.command.pick(cap_2_ctx, ["VS"])
    await match.command.pick(cap_1_ctx, ["TR"])

    if tier == 4:
        return

    print("TIER 5")

    while match.status is not MatchStatus.IS_BASING:
        await asyncio.sleep(1)

    # We assume tester is an admin
    await match.command.base(ctx, ["ceres"])

    if tier == 5:
        return

    print("TIER 6")

    while match.status is not MatchStatus.IS_WAITING:
        await asyncio.sleep(1)

    match.change_check("online")
    match.change_check("account")

    await match.command.ready(cap_1_ctx)
    await match.command.ready(cap_2_ctx)

