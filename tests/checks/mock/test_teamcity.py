# stdlib
import unittest

# 3p
from mock import MagicMock, patch

# project
from tests.checks.common import load_check

CONFIG = {
    'init_config': {},
    'instances': [
        {
            'name': 'One test build',
            'server': 'localhost:8111',
            'build_configuration': 'TestProject_TestBuild',
            'host_affected': 'buildhost42.dtdg.co',
            'is_deployment': False,
            'tags': ['one:tag', 'one:test']
        }
    ]
}

def get_mock_first_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    if 'sinceBuild' in url:
        # looking for new builds
        json = {"count":0,"href":"/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"}
    else:
        json = {"count":1,"href":"/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1","nextHref":"/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1,start:1","build":[{"id":1,"buildTypeId":"TestProject_TestBuild","number":"1","status":"SUCCESS","state":"finished","href":"/guestAuth/app/rest/builds/id:1","webUrl":"http://localhost:8111/viewLog.html?buildId=1&buildTypeId=TestProject_TestBuild"}]}

    mock_resp.json.return_value = json
    return mock_resp

def get_mock_one_more_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    json = {}

    if 'sinceBuild:id:1' in url:
        json = {"count":1,"href":"/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS","build":[{"id":2,"buildTypeId":"TestProject_TestBuild","number":"2","status":"SUCCESS","state":"finished","href":"/guestAuth/app/rest/builds/id:2","webUrl":"http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild"}]}
    elif 'sinceBuild:id:2' in url:
        json = {"count":0,"href":"/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:2,status:SUCCESS"}

    mock_resp.json.return_value = json
    return mock_resp



class TeamCityCheckTest(unittest.TestCase):
    """
    If you delete the cassettes at fixtures/teamcity*.
    You can run the tests with a real TC server providing you
    create a build configuration with the ID above in CONFIG
    """

    def test_build_event(self):
        agent_config = {
            'version': '0.1',
            'api_key': 'toto'
        }
        check = load_check('teamcity', CONFIG, agent_config)

        with patch('requests.get', get_mock_first_build):
            check.check(check.instances[0])

        metrics = check.get_metrics()
        self.assertEquals(len(metrics), 0)

        events = check.get_events()
        # Nothing should have happened because we only create events
        # for newer builds
        self.assertEquals(len(events), 0)

        with patch('requests.get', get_mock_one_more_build):
            check.check(check.instances[0])

        events = check.get_events()
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0]['msg_title'], "Build for One test build successful")
        self.assertEquals(events[0]['msg_text'], "Build Number: 2\nDeployed To: buildhost42.dtdg.co\n\nMore Info: http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild")
        self.assertEquals(events[0]['tags'], ['build', 'one:tag', 'one:test'])
        self.assertEquals(events[0]['host'], "buildhost42.dtdg.co")


        # One more check should not create any more events
        with patch('requests.get', get_mock_one_more_build):
            check.check(check.instances[0])

        events = check.get_events()
        self.assertEquals(len(events), 0)
