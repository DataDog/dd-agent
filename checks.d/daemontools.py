# project
from checks import AgentCheck
import re
from utils.subprocess_output import get_subprocess_output

DT_STATUS = re.compile(".*: (down|up) \(pid (\d+)\) (\d+) seconds")

class DaemonToolsCheck(AgentCheck):
    def check(self, instance):
        path = instance.get('path', '/etc/service')
        if path is None:
            raise Exception("Must provide a path where services are installed!")
        service = instance.get('service')
        if service is None:
            raise Exception("Must provide a service to check!")
        tags = instance.get('tags', [])
        tags.append("service:" + service)

        status = get_subprocess_output(['svstat', path + "/" + service], self.log)

        check_status = AgentCheck.CRITICAL
        dt_result = DT_STATUS.match(status[0])

        if status[1] is not None:
            self.log.error(status[1])

        if dt_result:
            if dt_result.group(1) == "up":
                check_status = AgentCheck.OK
                self.gauge('daemontools.service.uptime', float(dt_result.group(3)), tags)
            elif dt_result.group(1) == "down":
                check_status == AgentCheck.CRITICAL
            else:
                check_status == AgentCheck.UNKNOWN

        self.service_check(
            "daemontools.is_running",
            check_status,
            message=status[0],
            tags=tags
        )
