from gspread import service_account
from datetime import datetime as dt, timezone as tz, timedelta as td
from numpy import array as np_array
from re import compile as reg_compile, sub as reg_sub

from modules.tools import date_parser

import modules.config as cfg

from logging import getLogger

log = getLogger("pog_bot")

_secret_file = ""


def init(secret_file):
    global _secret_file
    _secret_file = secret_file


def get_booked_bases(base_class, booked_bases_list):  # runs on class init, saves a list of booked bases at the time of init to self.booked
    index_start = index_end = None
    gc = service_account(filename=_secret_file)

    if cfg.database["jaeger_cal"] is None or cfg.database["jaeger_cal"] == "":
        log.info("config value 'jaeger_cal' is not set, skipping booked bases check")
        return

    sh = gc.open_by_key(cfg.database["jaeger_cal"])
    ws = sh.worksheet("Current")
    cal_export = np_array(ws.get_all_values())
    date_col = cal_export[:,0]
    for index, value in enumerate(date_col):
        if not index_start and value == dt.now(tz.utc).strftime('%b-%d'):
            # gets us the header for the current date section in the google sheet
            index_start = index + 1
            continue
        if value == (dt.now(tz.utc) + td(days=1)).strftime('%b-%d'):
            # gets us the header for tomorrow's date in the sheet
            index_end = index  # now we know the range on the google sheet to look for base availability
            break
    if index_start is None or index_end is None:
        log.warning(f"Unable to find date range in Jaeger calendar for today's date. Returned: '{index_start}' "
                    f"to '{index_end}'")
        return


    today_bookings = cal_export[index_start:index_end]

    for booking in today_bookings:
        try:
            start_time = date_parser(booking[10])  # 45 mins before start of reservation
            if booking[11] != "":
                end_time = date_parser(booking[11])
            else:
                end_time = date_parser(booking[9])
            if start_time <= dt.now(tz.utc) <= end_time:
                splitting_chars = ['/', ',', '&', '(', ')']
                booked_bases = booking[3]
                for sc in splitting_chars:
                    booked_bases = booked_bases.replace(sc, ';')
                booked_bases = [_identify_base_from_name(base, base_class) for base in booked_bases.split(";")]
                for booked in booked_bases:
                    if booked is not None and booked not in booked_bases_list:
                        booked_bases_list.append(booked)
        except (ValueError, TypeError) as e:
            log.warning(f"Skipping invalid line in Jaeger Calendar:\n{booking}\nError: {e}")


def _identify_base_from_name(name, base_class):
    # Check if string is empty
    if len(name) == 0:
        return

    # Use regex to clean the string from unwanted characters
    pattern = reg_compile("[^a-zA-Z0-9 ]")
    name = reg_sub(" {2,}", " ", pattern.sub('', name)).strip()

    # Add all matching bases to list
    results = base_class.get_bases_from_name(name)

    # If only one matching base
    if len(results) == 1:
        return results[0]

    # If not, we take only the bases which are in pool
    if len(results) > 1:
        results_2 = list()
        for base in results:
            if base.pool:
                results_2.append(base)
        # If only one matching base
        if len(results_2) == 1:
            return results_2[0]
