from logging import getLogger
from display import AllStrings as disp, ContextWrapper
import modules.tools as tools

__spam_list = dict()
__SPAM_MSG_FREQUENCY = 5
__last_requests = dict()

log = getLogger("pog_bot")


async def is_spam(author, channel, ctx=None):
    a_id = author.id
    if a_id in __spam_list and __spam_list[a_id] > 0:
        if a_id in __last_requests and __last_requests[a_id] < tools.timestamp_now() - 30:
            log.info(f"Automatically unlocked id[{a_id}], name[{author.name}] from spam filter")
            unlock(a_id)
    __last_requests[a_id] = tools.timestamp_now()
    if a_id not in __spam_list:
        __spam_list[a_id] = 1
        return False
    __spam_list[a_id] += 1
    if __spam_list[a_id] == 1:
        return False
    if __spam_list[a_id] % __SPAM_MSG_FREQUENCY == 0:
        if not ctx:
            ctx = ContextWrapper.wrap(channel, author=author)
        await disp.STOP_SPAM.send(ctx)
    return True


# This is never called:
def clean():
    tmp = __spam_list.copy()
    for a_id in tmp:
        if __spam_list[a_id] == 0:
            del __spam_list[a_id]


def debug():
    result = dict()
    for k in list(__spam_list.keys()):
        if __spam_list[k] > 0:
            result[k] = __spam_list[k]
    return result


def clear_spam_list():
    __spam_list.clear()


def unlock(a_id):
    __spam_list[a_id] = 0

