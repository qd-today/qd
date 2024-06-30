import datetime
import time


def timestamp(type="int"):
    if type == "float":
        return time.time()
    return int(time.time())


def get_date_time(date=True, time=True, time_difference=0):
    if isinstance(date, str):
        date = int(date)
    if isinstance(time, str):
        time = int(time)
    if isinstance(time_difference, str):
        time_difference = int(time_difference)
    now_date = datetime.datetime.today() + datetime.timedelta(hours=time_difference)
    if date:
        if time:
            return str(now_date).split(".", maxsplit=1)[0]
        else:
            return str(now_date.date())
    elif time:
        return str(now_date.time()).split(".", maxsplit=1)[0]
    else:
        return ""


def strftime(string_format, second=None):
    """return a date string using string. See https://docs.python.org/3/library/time.html#time.strftime for format"""
    if second is not None:
        try:
            second = float(second)
        except Exception as e:
            raise Exception(f"Invalid value for epoch value ({second})") from e
    return time.strftime(string_format, time.localtime(second))


def format_date(date, gmt_offset=time.timezone / 60, relative=True, shorter=False, full_format=True):
    """Formats the given date (which should be GMT).

    By default, we return a relative time (e.g., "2 minutes ago"). You
    can return an absolute date string with ``relative=False``.

    You can force a full format date ("July 10, 1980") with
    ``full_format=True``.

    This method is primarily intended for dates in the past.
    For dates in the future, we fall back to full format.
    """
    if not date:
        return "-"
    if isinstance(date, float) or isinstance(date, int):
        date = datetime.datetime.utcfromtimestamp(date)
    now = datetime.datetime.utcnow()
    local_date = date - datetime.timedelta(minutes=gmt_offset)
    local_now = now - datetime.timedelta(minutes=gmt_offset)
    local_yesterday = local_now - datetime.timedelta(hours=24)
    local_tomorrow = local_now + datetime.timedelta(hours=24)
    if date > now:
        later = "后"
        date, now = now, date
    else:
        later = "前"
    difference = now - date
    seconds = difference.seconds
    days = difference.days

    format = None
    if not full_format:
        if relative and days == 0:
            if seconds < 50:
                return f"{seconds} 秒" + later

            if seconds < 50 * 60:
                minutes = round(seconds / 60.0)
                return f"{minutes} 分钟" + later

            hours = round(seconds / (60.0 * 60))
            return f"{hours} 小时" + later

        if days == 0:
            format = "%(time)s"
        elif days == 1 and local_date.day == local_yesterday.day and relative and later == "前":
            format = "昨天" if shorter else "昨天 %(time)s"
        elif days == 1 and local_date.day == local_tomorrow.day and relative and later == "后":
            format = "明天" if shorter else "明天 %(time)s"
        # elif days < 5:
        # format = "%(weekday)s" if shorter else "%(weekday)s %(time)s"
        elif days < 334:  # 11mo, since confusing for same month last year
            format = "%(month_name)s-%(day)s" if shorter else "%(month_name)s-%(day)s %(time)s"

    if format is None:
        format = "%(year)s-%(month_name)s-%(day)s" if shorter else "%(year)s-%(month_name)s-%(day)s %(time)s"

    str_time = f"{local_date.hour:02d}:{local_date.minute:02d}:{local_date.second:02d}"

    return format % {
        "month_name": local_date.month,
        "weekday": local_date.weekday(),
        "day": str(local_date.day),
        "year": str(local_date.year),
        "time": str_time,
    }