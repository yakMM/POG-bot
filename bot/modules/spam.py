"""Tiny module used as a slight spam protector
"""

from modules.display import send

__spamList = dict()
__SPAM_MSG_FREQUENCY = 5


async def isSpam(msg):
    id = msg.author.id
    if id not in __spamList:
        __spamList[id] = 1
        return False
    __spamList[id] += 1
    if __spamList[id] == 1:
        return False
    if __spamList[id] % __SPAM_MSG_FREQUENCY == 0:
        await send("STOP_SPAM", msg)
    return True


# This is never called:
def clean():
    tmp = __spamList.copy()
    for id in tmp:
        if __spamList[id] == 0:
            del __spamList[id]


def unlock(id):
    __spamList[id] = 0
