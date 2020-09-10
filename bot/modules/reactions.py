from modules.enumerations import PlayerStatus
from modules.display import edit


async def reactionHandler(reaction, player):
    if player.hasOwnAccount:
        return
    if player.status is not PlayerStatus.IS_PLAYING:
        return
    if player.active.account is None:
        return
    # If we reach this point, we know player has been given an account
    account = player.active.account
    if reaction.message.id != account.message.id:  # check if it's the right message
        return
    if account.isValidated:  # Check if user didn't already react
        return
    if str(reaction.emoji) == "✅":  # If everything is fine, account is validated
        account.validate()
        await edit("ACC_UPDATE", account.message, account=account)
        await account.message.remove_reaction(reaction.emoji, player)
