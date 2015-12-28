from checks import Check

# 3rd party
import uptime

class System(Check):
    def check(self, agentConfig):
        return {"system.uptime": uptime.uptime()}
