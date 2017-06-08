# stdlib
import subprocess

# project
from checks import AgentCheck


class Fail2Ban(AgentCheck):
    """ Fail2Ban agent check

    This check is used to run the `fail2ban-client` command to get the status
    of active fail2ban jails. The following is an example of the metrics retrieved
    for a single jail:

    fail2ban.filter.currently_failed = 2       {'type': 'gauge', 'tags': ['jail:ssh']}
    fail2ban.action.total_banned     = 4955    {'type': 'gauge', 'tags': ['jail:ssh']}
    fail2ban.action.currently_banned = 1       {'type': 'gauge', 'tags': ['jail:ssh']}
    fail2ban.filter.total_failed     = 61645   {'type': 'gauge', 'tags': ['jail:ssh']}
    """

    STATS = dict(
        filter=["currently_failed", "total_failed"],
        action=["currently_banned", "total_banned"],
    )
    SERVICE_CHECK_NAME = "fail2ban.can_connect"

    def check(self, instance):
        """ Run the check

        Each instance accepts the following paramaters:

        sudo                Optional: Boolean - whether or not to prepend "sudo" to the fail2ban-client calls
        jail_blacklist      Optional: List - any fail2ban jails to omit, e.g. "ssh-ddos"
        tags                Optional: List - any additional tags to send with each metric for the instance
        """
        sudo = instance.get("sudo", False)
        jail_blacklist = instance.get("jail_blacklist", [])
        instance_tags = instance.get('tags', [])

        if self.can_ping_fail2ban(sudo=sudo):
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=instance_tags)
            stats = self.get_jail_stats(sudo=sudo, jail_blacklist=jail_blacklist)
            for jail_name, metric, value in stats:
                tags = instance_tags + ["jail:%s" % (jail_name, )]
                self.gauge(metric, value, tags=tags)
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance_tags)

    def execute_command(self, args, sudo=False):
        """ Helper method used to execute the given command

        :param args: Command arguments to execute, e.g. ["fail2ban-client", "status"]
        :type args: list
        :param sudo: Whether or not to prepend "sudo" to the argument list [default: False]
        :type sudo: bool
        :rtype: generator
        :returns: a generator which will yield for every line in the commands stdout
        """
        if sudo:
            args.insert(0, "sudo")
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = process.communicate()
        if output and not err and process.returncode == 0:
            for line in output.split("\n"):
                yield line

    def get_jails(self, sudo=False, jail_blacklist=None):
        """ Get a list of enabled jails

        :param sudo: Whether or not sudo is needed [default: False]
        :type sudo: bool
        :param jail_blacklist: A list of jails to omit [default: None]
        :type jail_blacklist: None|list
        :rtype: generator
        :returns: a generator which will yield for every jail name found (minus those
            provided in ``jail_blacklist``)
        """
        for line in self.execute_command(["fail2ban-client", "status"], sudo=sudo):
            if "list" in line:
                _, _, jails = line.rpartition(":")
                for jail in jails.split(","):
                    jail = jail.strip(" \t\r\n")
                    if not jail_blacklist or jail not in jail_blacklist:
                        yield jail

    def get_jail_status(self, jail, sudo=False):
        """ Parse the status output for a given jail

        The output will look like

        .. code:: python

            {
              "filter": {
                "total_failed": 456,
                "currently_failed": 0
              },
              "action": {
                "currently_banned": 2,
                "total_banned": 345
              }
            }


        Parsing these metrics is a little messy since the output of fail2ban-client looks like:

        .. code:: none

            Status for the jail: ssh
            |- filter
            |  |- File list:/var/log/auth.log
            |  |- Currently failed:0
            |  `- Total failed:62170
            `- action
               |- Currently banned:1
               |  `- IP list:222.186.56.43
               `- Total banned:4978


        The main idea of this method is that we want to parse "filter" and "action" as
        top level "buckets" and parse everything under them as metrics, so we end
        up with the above example output

        :param jail: The name of the jail to get the status of
        :type jail: str
        :param sudo: Whether or not sudo is needed to execute [default: False]
        :type sudo: bool
        :rtype: dict
        :returns: A dictionary mapping jail filter or action metrics
        """
        contents = self.execute_command(["fail2ban-client", "status", jail], sudo=sudo)

        # these two generator expresstions are used to "peel back" one level of the output,
        # so that anything starting with "-" is our top level "bucket"
        #
        # [
        #   "- filter",
        #   "  |- File list:/var/log/auth.log",
        #   "  |- Currently failed:0",
        #   "  `- Total failed:62170",
        #   "- action",
        #   "  |- Currently banned:1",
        #   "  |  `- IP list:222.186.56.43",
        #   "  `- Total banned:4978"
        # ]
        contents = (l.strip("\r\n") for l in contents
                    if len(l) and l[0] in (" ", "|", "-", "`"))
        contents = (l.strip("|`") for l in contents)

        last = None
        tree = dict()
        for line in contents:
            # "- filter" or "- action"
            if line.startswith("-"):
                last = line.strip("- ")
                tree[last] = dict()
            elif last in tree:
                # this is a metric under "filter" or "action", do some serious
                # cleanup of excess characters, partition on ":", then do some more cleanup
                part = line[2:].strip(" |`-")
                key, _, value = part.partition(":")
                key = key.strip(" \t").replace(" ", "_").lower()
                value = value.strip(" \t")
                if value != '':
                    tree[last][key] = value

        return tree

    def get_jail_stats(self, sudo=False, jail_blacklist=None):
        """ Parse out all the available stats from fail2ban-client

        The output will be a generator which emits tuples used for emitting
        metrics, the tuples will look like the following

        .. code:: python

            [('ssh', 'fail2ban.action.currently_banned', '1'),
             ('ssh', 'fail2ban.action.total_banned', '4979'),
             ('ssh', 'fail2ban.filter.currently_failed', '1'),
             ('ssh', 'fail2ban.filter.total_failed', '62177'),
             ('ssh_ddos', 'fail2ban.action.currently_banned', '0'),
             ('ssh_ddos', 'fail2ban.action.total_banned', '19'),
             ('ssh_ddos', 'fail2ban.filter.currently_failed', '0'),
             ('ssh_ddos', 'fail2ban.filter.total_failed', '1425')]


        :param sudo: Whether or not sudo is needed to execute [default: False]
        :type sudo: bool
        :param jail_blacklist: A list of jails to omit [default: None]
        :type jail_blacklist: None|list
        :rtype: generator
        :returns: A generator which emits tuples ``(<jail_name>, <metric_name>, <metric_value>)``
        """
        for jail in self.get_jails(sudo=sudo, jail_blacklist=jail_blacklist):
            jail_status = self.get_jail_status(jail, sudo=sudo)
            jail_name = jail.replace("-", "_")
            for stat, substats in self.STATS.iteritems():
                for substat in substats:
                    value = jail_status.get(stat, {}).get(substat, 0)
                    yield (jail_name, "fail2ban.%s.%s" % (stat, substat), value)

    def can_ping_fail2ban(self, sudo=False):
        """ Check if we can ping fail2ban server

        Simply executes ``fail2ban-client ping``, expects the response "pong"

        :param sudo: Whether or not sudo is needed to execute [default: False]
        :type sudo: bool
        :rtype: bool
        :returns: Whether or not we got a "pong" response back
        """
        output = self.execute_command(["fail2ban-client", "ping"], sudo=sudo)
        for line in output:
            if "pong" in line:
                return True
        return False
