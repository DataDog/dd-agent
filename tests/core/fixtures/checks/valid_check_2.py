from checks import AgentCheck

OUTPUT = 'valid_check_2'

class ValidCheck(AgentCheck):

    def check(self, instance):
        return OUTPUT
