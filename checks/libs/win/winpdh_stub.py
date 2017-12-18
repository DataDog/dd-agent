# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class WinPDHCounter(object):

    def is_single_instance(self):
        return False

    def get_single_value(self):
        return None

    def get_all_values(self):
        return {}

    def _get_counter_dictionary(self):
        return
