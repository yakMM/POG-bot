# @CHECK 2.0 features OK

"""Tiny module used as a slight spam protector
"""

from display import send

__spam_list = dict()
__SPAM_MSG_FREQUENCY = 5


async def is_spam(msg):
    id = msg.author.id
    if id not in __spam_list:
        __spam_list[id] = 1
        return False
    __spam_list[id] += 1
    if __spam_list[id] == 1:
        return False
    if __spam_list[id] % __SPAM_MSG_FREQUENCY == 0:
        await send("STOP_SPAM", msg)
    return True


# This is never called:
def clean():
    tmp = __spam_list.copy()
    for id in tmp:
        if __spam_list[id] == 0:
            del __spam_list[id]


def unlock(id):
    __spam_list[id] = 0
