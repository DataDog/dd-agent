# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import requests


DEFAULT_TIMEOUT = 10


def retrieve_json(url, timeout=DEFAULT_TIMEOUT, verify=True):
    r = requests.get(url, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.json()

# Get expvar stats
def get_expvar_stats(key, port):
    try:
        json = retrieve_json("http://127.0.0.1:{port}/debug/vars".format(port=port))
    except requests.exceptions.RequestException as e:
        raise e

    if key:
        return json.get(key)

    return json
