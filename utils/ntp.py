import random

def get_ntp_datadog_host(subpool=None):
    """
    Returns randomly a NTP hostname of our vendor pool. Or
    a given subpool if given in input.
    """
    subpool = subpool or random.randint(0, 3)
    return "{0}.datadog.pool.ntp.org".format(subpool)
