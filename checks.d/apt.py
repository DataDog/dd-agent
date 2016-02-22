# stdlib
import re

# project
from checks import AgentCheck

# The name of the service check we'll use to report when there are package
# updates available. Normal non-security related packages will generate a
# warning, security related package updates will generate a critical alert.
SECURITY_CHECK = 'apt.updates'

# Regular expressions to match the /var/lib/update-notifier/updates-available format.
PACKAGES_REGEX = re.compile(r"^(\d+) packages? can be updated.*", re.MULTILINE)
SECURITY_REGEX = re.compile(r"^(\d+) updates? (is a|are) security updates?.*$", re.MULTILINE)


class APT(AgentCheck):
    """Generates metrics and service alerts when package updates are available
    """

    def check(self, instance):
        updates = self.updates(instance)

        self.gauge('apt.updates.packages', updates['packages'])
        self.gauge('apt.updates.security', updates['security'])

        if updates['security'] > 0:
            self.service_check(SECURITY_CHECK, AgentCheck.CRITICAL)
        elif updates['packages'] > 0:
            self.service_check(SECURITY_CHECK, AgentCheck.WARNING)
        else:
            self.service_check(SECURITY_CHECK, AgentCheck.OK)

    def updates(self, instance):
        updates = {'packages': 0, 'security': 0}

        with open(instance['updates_file'], 'r') as fd:
            content = fd.read()

            for m in PACKAGES_REGEX.finditer(content):
                updates['packages'] = int(m.groups()[0])
            for m in SECURITY_REGEX.finditer(content):
                updates['security'] = int(m.groups()[0])

        return updates
