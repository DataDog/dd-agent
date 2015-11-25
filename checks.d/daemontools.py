# project
from checks import AgentCheck
import re
import subprocess

dt_status = re.compile(".*: (down|up) \(pid (\d+)\) (\d+) seconds")

class DaemonToolsCheck(AgentCheck):
    def check(self, instance):
        path = self.init_config.get('path', '/etc/service')
        service = instance.get('service')
        tags = instance.get('tags', [])
        tags.append("service:" + service)

        try:
            status = subprocess.Popen(['svstat', path + "/" + service], stdout=subprocess.PIPE, close_fds=True).communicate()[0]

            check_message = status
            check_status = AgentCheck.CRITICAL
            dt_result = dt_status.match(status)
            if dt_result:
                if dt_result.group(1) == "up":
                    check_status = AgentCheck.OK
                    self.gauge('daemontools.service.uptime', float(dt_result.group(3)), tags)
                elif dt_result.group(1) == "down":
                    check_status == AgentCheck.CRITICAL
                else:
                    check_status == AgentCheck.UNKNOWN

            self.service_check(
                "daemontools.{0}.is_running".format(service),
                check_status,
                message=check_message,
                tags=tags
            )

        except Exception:
            self.log.exception('Cannot get status of service from daemontools')
            return False
