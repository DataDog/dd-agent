import calendar
from datetime import datetime

MAX_TITLE_LEN = 100


class ParseError(Exception):
    pass


def parse_date(date_val, date_format=None):
    if date_format:
        dt = datetime.strptime(date_val, date_format)
    else:
        to_try = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S,%f']

        for fmt in to_try:
            try:
                dt = datetime.strptime(date_val, fmt)
                break
            except Exception:
                pass
        else:
            raise ParseError(date_val)

    return calendar.timegm(dt.timetuple())
