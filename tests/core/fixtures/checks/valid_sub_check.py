from tests.core.fixtures.checks.valid_check_2 import ValidCheck

OUTPUT = 'valid_check_1'

class InheritedCheck(ValidCheck):

    def check(self, instance):
        return OUTPUT
