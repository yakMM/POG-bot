import modules.database as db
from datetime import datetime as dt, timezone as tz, date as dt_date, time as dt_time, timedelta as dt_delta
import modules.tools as tools
from classes import PlayerStat
from logging import getLogger

log = getLogger("pog_bot")

_match_stamps = dict()

oldest = 0


def init():
    # Create timestamp dict
    def db_match(match):
        global oldest
        _match_stamps[match["_id"]] = match["round_stamps"][0]
        oldest = match["round_stamps"][0] if oldest == 0 else min(match["round_stamps"][0], oldest)
    db.get_all_elements(db_match, "matches")


def add_match(match_data):
    _match_stamps[match_data.id] = match_data.round_stamps[0]


def get_matches_in_time(player, time):
    matches_to_query = list()
    for m_id in player.matches[::-1]:
        try:
            if _match_stamps[m_id] >= time:
                matches_to_query.append(m_id)
            else:
                break
        except KeyError:
            pass
    return matches_to_query


def get_previous_week(date):
    iso_date = date.isocalendar()
    end = dt.combine(dt_date.fromisocalendar(iso_date[0], iso_date[1], 1), dt_time(tzinfo=tz.utc))
    start = end - dt_delta(weeks=1)
    return start, end


async def get_new_stats(match_cls, player, time=tools.timestamp_now()-1209600):
    m_list = get_matches_in_time(player, time)
    new_p_stats = PlayerStat(player.id, player.name)
    for m_id in m_list:
        match = await match_cls.get_from_database(m_id)
        if not match:
            log.error(f"get_new_stats: Couldn't find match {m_id} in database!")
            continue
        found = False
        for tm in match.data.teams:
            for p_score in tm.players:
                if int(p_score.id) == player.id:
                    p_score.stats = new_p_stats
                    p_score.update_stats()
                    found = True
                    break
            if found:
                break
    return new_p_stats


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
        return self.start.strftime("%b %d")

    @property
    def end_str(self):
        return self.end.strftime("%b %d")


def format_for_psb(player, args):
    all_weeks = list()
    date = None
    if args:
        date = tools.date_parser(" ".join(args))
    if not date:
        date = dt.now(tz.utc)
    req_date = date.strftime("%Y-%m-%d")

    date = date + dt_delta(weeks=1)
    start, end = get_previous_week(date)
    all_weeks.append(PsbWeekUsage(player, 0, start, end))
    date = start

    for i in range(8):
        start, end = get_previous_week(date)
        all_weeks.append(PsbWeekUsage(player, i+1, start, end))
        date = start

    return req_date, all_weeks



