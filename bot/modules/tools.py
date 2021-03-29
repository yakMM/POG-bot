# @CHECK 2.0 features OK
from datetime import datetime as dt
import pytz
from dateutil import parser
from dateutil import tz
from logging import getLogger

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


class UnexpectedError(Exception):
    def __init__(self, msg):
        self.reason = msg
        message = "Encountered unexpected error: " + msg
        log.error(message)
        super().__init__(message)


def is_al_num(string):
    """ Little utility to check if a string contains only letters and numbers (a-z,A-Z,0-9)
        Parameters
        ----------
        string : str
            The string to be processed

        Returns
        -------
        is_alpha_num : boolean
            Result
    """
    for i in string.lower():
        cond = ord('a') <= ord(i) <= ord('z')
        cond = cond or (ord('0') <= ord(i) <= ord('9'))
        if not cond:
            return False
    return True


def date_parser(string):
    dtx = parser.parse(string, dayfirst=False, tzinfos=TZ_OFFSETS)
    try:
        dtx = pytz.utc.localize(dtx)
        dtx = dtx.replace(tzinfo=tz.UTC)
    except ValueError:
        pass
    dtx = dtx.astimezone(pytz.timezone("UTC"))
    return dtx
