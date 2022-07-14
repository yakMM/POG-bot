# @CHECK 2.0 features OK
from datetime import datetime as dt
import pytz
from dateutil import parser
from dateutil import tz
from logging import getLogger
import re

log = getLogger("pog_bot")

TZ_OFFSETS = {
    "CEST": +7200,
    "BST": +3600,
    "EDT": -14400,
    "CDT": -18000,
    "MDT": -21600,
    "PDT": -25200,
    "MSK": +10800,
    "AEST": +36000,
    "CST": +28800
}

MONTH_KW = ["months", "month"]
WEEK_KW = ["weeks", "week", "w"]
DAY_KW = ["days", "day", "d"]
HOUR_KW = ["hours", "hour", "h"]
MIN_KW = ["minutes", "minute", "mins", "min", "m"]
SEC_KW = ["seconds", "second", "secs", "sec", "s"]
ALL_KW = [keywords for keywords in (*MONTH_KW, *WEEK_KW, *DAY_KW, *HOUR_KW, *MIN_KW, *SEC_KW)]
ALL_KW.sort(key=len, reverse=True)
RE_DURATION = re.compile(rf"([0-9]+)\s*({'|'.join(ALL_KW)})\s*([0-9]*)")


class UnexpectedError(Exception):
    def __init__(self, msg):
        self.reason = msg
        message = "Encountered unexpected error: " + msg
        log.error(message)
        super().__init__(message)


def is_al_num(string):
    """
    Little utility to check if a string contains only letters and numbers (a-z,A-Z,0-9)

    :param string: The string to be processed
    :return: Result
    """
    for i in string.lower():
        cond = ord('a') <= ord(i) <= ord('z')
        cond = cond or (ord('0') <= ord(i) <= ord('9'))
        if not cond:
            return False
    return True


def date_parser(string):
    try:
        dtx = parser.parse(string, dayfirst=False, tzinfos=TZ_OFFSETS)
    except parser.ParserError:
        return
    try:
        dtx = pytz.utc.localize(dtx)
        dtx = dtx.replace(tzinfo=tz.UTC)
    except ValueError:
        pass
    dtx = dtx.astimezone(pytz.timezone("UTC"))
    return dtx


def timestamp_now():
    return int(dt.timestamp(dt.now()))


def time_diff(timestamp, now=timestamp_now()):
    lead = now - timestamp
    if lead < 60:
        lead_str = f"{lead} second"
    elif lead < 3600:
        lead //= 60
        lead_str = f"{lead} minute"
    elif lead < 86400:
        lead //= 3600
        lead_str = f"{lead} hour"
    elif lead < 604800:
        lead //= 86400
        lead_str = f"{lead} day"
    elif lead < 2419200:
        lead //= 604800
        lead_str = f"{lead} week"
    else:
        lead //= 2419200
        lead_str = f"{lead} month"
    if lead > 1:
        return lead_str + "s"
    else:
        return lead_str


def time_calculator(arg: str):
    lookup = RE_DURATION.match(arg)
    time = 0
    if not lookup:
        return time
    leading = int(lookup.group(1))
    keyword = lookup.group(2)
    try:
        trailing = int(lookup.group(3))
    except ValueError:
        trailing = 0
    if keyword in MONTH_KW:
        time = 2419200 * leading
        time += 604800 * trailing
    elif keyword in WEEK_KW:
        time = 604800 * leading
        time += 86400 * trailing
    elif keyword in DAY_KW:
        time = 86400 * leading
        time += 3600 * trailing
    elif keyword in HOUR_KW:
        time = 3600 * leading
        time += 60 * trailing
    elif keyword in MIN_KW:
        time = 60 * leading
        time += trailing
    return time


class AutoDict(dict):
    def auto_add(self, key, value):
        if key in self:
            self[key] += value
        else:
            self[key] = value