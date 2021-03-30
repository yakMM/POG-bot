# This file is an example of test script for an easier development

from modules.lobby import add_to_lobby
from classes import Player
import asyncio
from discord.ext import commands
from logging import getLogger
import modules.config as cfg

from display import ContextWrapper

log = getLogger("pog_bot")


def get_ids():
    # Enter here a list of discord IDS of accounts you wish to use for the testing
    # For example:
    # return [0000, 0000, 0000, 0000]
    from test2 import id3s
    return id3s


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
        await launch(ctx, [20, 21, 22, 23], 0)
        await launch(ctx, ids, 1)



async def launch(ctx, id_list, tier):

    players = [Player.get(id) for id in id_list]

    for p in players:
        add_to_lobby(p)

    if tier == 1:
        return

    await asyncio.sleep(3)

    match = players[0].match

    await match.on_volunteer(players[0])
    await match.on_volunteer(players[1])

    cap1, cap2 = players[0].active, players[1].active

    if tier == 2:
        return

    await asyncio.sleep(1)

    context = ContextWrapper.wrap(match.channel)
    context.author = ctx.author
    context.message = ctx.message

    ctx.message.mentions.append(context.author)

    await match.pick(context, cap1, [""])

    if tier == 3:
        return

    ctx.message.mentions.clear()

    await asyncio.sleep(2)
    await match.pick(context, cap2, ["VS"])
    await asyncio.sleep(1)
    await match.pick(context, cap1, ["TR"])

    if tier == 4:
        return

    await asyncio.sleep(3)

    await match.base_selector.select_by_index(context, cap1, 0)

    if tier == 5:
        return

    await asyncio.sleep(2)

    match.change_check("online")
    match.change_check("account")

    await match.team_ready(context, cap1)
    await match.team_ready(context, cap2)

