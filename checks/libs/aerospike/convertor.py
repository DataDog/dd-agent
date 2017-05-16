# stdlib
import datetime as dt

# convert string to list


def text_to_list(text, delimiter=';'):

    if text.strip() == "":
        return []
    return text.split(delimiter)

# convert list to dict


def list_to_dict(lst, delimiter="="):

    result = dict(node_status="on")
    for row in lst:
        split = row.split(delimiter, 1)
        if split == ['']:
            pass
        else:
            key, value = split
            if key not in result:
                result[key] = value
            else:
                result[key] = "%s, %s" % (result[key], value)
    return result

# get time difference in seconds


def time_diffrence_in_sec(time1, time2):

    FMT = '%H:%M:%S'
    tdelta = dt.datetime.strptime(
        time1, FMT) - dt.datetime.strptime(time2, FMT)
    return tdelta.seconds

# get time average


def time_average(time1, time2):

    diff = time_diffrence_in_sec(time1, time2)
    FMT = '%H:%M:%S'
    avg_time = dt.datetime.strptime(time2, FMT) + dt.timedelta(0, diff / 2)
    return avg_time.strftime("%H:%M:%S")

# get alert status


def get_alert_status(error_condition, warning_condition=None):

    if error_condition:
        return 'error'
    elif warning_condition:
        return 'warning'
    else:
        return 'success'
