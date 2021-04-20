

import modules.database as db
from datetime import datetime as dt, timezone as tz, date as dt_date, time as dt_time, timedelta as dt_delta
import modules.tools as tools

_match_stamps = dict()

oldest = 0


def init():
    # Create timestamp dict
    def add_match(match):
        global oldest
        _match_stamps[match["_id"]] = match["round_stamps"][0]
        oldest = match["round_stamps"][0] if oldest ==0 else min(match["round_stamps"][0], oldest)
    db.get_all_elements(add_match, "matches")


def get_num_matches(player, time):
    num = 0
    for m_id in player.matches[::-1]:
        try:
            if _match_stamps[m_id] >= time:
                num += 1
            else:
                break
        except KeyError:
            pass
    return num


def get_previous_week(date):
    iso_date = date.isocalendar()
    end = dt.combine(dt_date.fromisocalendar(iso_date[0], iso_date[1], 1), dt_time(tzinfo=tz.utc))
    start = end - dt_delta(weeks=1)
    return start, end


class PsbWeekUsage:
    def __init__(self, player, week_num, start, end):
        self.week_num = week_num
        self.start = start
        self.end = end
        self.start_stamp = dt.timestamp(start)
        self.end_stamp = dt.timestamp(end)
        self.num = self.get_num_matches(player)

    def get_num_matches(self, player):
        num = 0
        for m_id in player.matches[::-1]:
            try:
                if _match_stamps[m_id] > self.end_stamp:
                    pass
                elif self.start_stamp <= _match_stamps[m_id] <= self.end_stamp:
                    num += 1
                else:
                    break
            except KeyError:
                pass
        return num

    @property
    def start_str(self):
        return self.start.strftime("%B %d")

    @property
    def end_str(self):
        return self.end.strftime("%B %d")


def format_for_psb(player, args):
    all_weeks = list()
    date = None
    if args:
        date = tools.date_parser(" ".join(args))
    if not date:
        date = dt.now(tz.utc)
    req_date = date.strftime("%Y-%m-%d")

    for i in range(8):
        start, end = get_previous_week(date)
        all_weeks.append(PsbWeekUsage(player, 8-i, start, end))
        date = start

    return req_date, all_weeks



