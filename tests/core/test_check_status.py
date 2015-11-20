# stdlib
import nose.tools as nt

# project
from checks import AgentCheck
from checks.check_status import (
    CheckStatus,
    CollectorStatus,
    InstanceStatus,
    STATUS_ERROR,
    STATUS_OK,
)


class DummyAgentCheck(AgentCheck):

    def check(self, instance):
        if not instance['pass']:
            raise Exception("failure")


def test_check_status_fail():
    instances = [
        {'pass': True},
        {'pass': False},
        {'pass': True}
    ]

    check = DummyAgentCheck('dummy_agent_check', {}, {}, instances)
    instance_statuses = check.run()
    assert len(instance_statuses) == 3
    assert instance_statuses[0].status == STATUS_OK
    assert instance_statuses[1].status == STATUS_ERROR
    assert instance_statuses[2].status == STATUS_OK


def test_check_status_pass():
    instances = [
        {'pass': True},
        {'pass': True},
    ]

    check = DummyAgentCheck('dummy_agent_check', {}, {}, instances)
    instances_status = check.run()
    assert len(instances_status) == 2
    for i in instances_status:
        assert i.status == STATUS_OK


def test_persistence():
    i1 = InstanceStatus(1, STATUS_OK)
    chk1 = CheckStatus("dummy", [i1], 1, 2)
    c1 = CollectorStatus([chk1])
    c1.persist()

    c2 = CollectorStatus.load_latest_status()
    nt.assert_equal(1, len(c2.check_statuses))
    chk2 = c2.check_statuses[0]
    assert chk2.name == chk1.name
    assert chk2.status == chk2.status
    assert chk2.metric_count == 1
    assert chk2.event_count == 2


def test_persistence_fail():

    # Assert remove doesn't crap out if a file doesn't exist.
    CollectorStatus.remove_latest_status()
    CollectorStatus.remove_latest_status()

    status = CollectorStatus.load_latest_status()
    assert not status
