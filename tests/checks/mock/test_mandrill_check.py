# third party imports
import mock

# dd-agent imports
from tests.checks.common import AgentCheckTest


class TestMandrillCheck(AgentCheckTest):
    CHECK_NAME = 'mandrill_check'

    USER_STATS = {
        'backlog': 5,
        'hourly_quota': 50,
        'reputation': 100,
        'username': 'test_user',
        'public_id': 'public_id',
        'stats': {
            'all_time': {
                'clicks': 10000,
            },
            'last_30_days': {
                'clicks': 5,
            },
            'last_60_days': {
                'clicks': 10,
            },
            'last_90_days': {
                'clicks': 30,
            },
            'last_7_days': {
                'clicks': 2,
            },
            'today': {
                'clicks': 0,
            },
        }
    }

    URL_STATS = [
        {
            'url': 'http://app.datadoghq.com/some-url/here',
            'click': 30,
            'sent': 1,
            'unique_clicks': 5,
        }
    ]

    TAGS = [
        {
            'tag': 'tag1',
        },
    ]
    TAG_STATS = {
        'tag1': {
            'stats': {
                'last_30_days': {
                    'clicks': 5,
                },
                'last_60_days': {
                    'clicks': 10,
                },
                'last_90_days': {
                    'clicks': 30,
                },
                'last_7_days': {
                    'clicks': 2,
                },
                'today': {
                    'clicks': 0,
                },
            },
        },
    }

    def _get_mock_client(self):
        """
        Helper method used to get mocked `mandrill.Mandrill` client
        """

        # `mandrill.Mandrill.tags.info` helper
        def tags_info(tag):
            return self.TAG_STATS.get(tag, {})

        client = mock.MagicMock()
        # these are the api calls that the check makes
        client.users.info.return_value = self.USER_STATS
        client.urls.list.return_value = self.URL_STATS
        client.tags.list.return_value = self.TAGS
        client.tags.info.side_effect = tags_info
        return client

    def _assert_user_stats(self):
        """
        Helper method to assert that the user metrics were properly sent
        """
        self.assertMetric('mandrill.users.backlog', 5, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.hourly_quota', 50, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.reputation', 100, tags=('username:test_user', 'public_id:public_id'))

        self.assertMetric('mandrill.users.clicks.last_30_days', 5, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.clicks.last_60_days', 10, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.clicks.last_90_days', 30, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.clicks.last_7_days', 2, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.clicks.today', 0, tags=('username:test_user', 'public_id:public_id'))
        self.assertMetric('mandrill.users.clicks.all_time', 10000, tags=('username:test_user', 'public_id:public_id'))

    def _assert_url_stats(self):
        """
        Helper method to assert that the url metrics were properly sent
        """
        self.assertMetric('mandrill.urls.click.max', 30, tags=('domain:app.datadoghq.com', ))
        self.assertMetric('mandrill.urls.sent.max', 1, tags=('domain:app.datadoghq.com', ))
        self.assertMetric('mandrill.urls.unique_clicks.max', 5, tags=('domain:app.datadoghq.com', ))

    def _assert_tag_stats(self):
        """
        Helper method to assert that the tag metrics were properly sent
        """
        self.assertMetric('mandrill.tags.clicks.last_30_days', 5, tags=('tag_name:tag1', ))
        self.assertMetric('mandrill.tags.clicks.last_60_days', 10, tags=('tag_name:tag1', ))
        self.assertMetric('mandrill.tags.clicks.last_90_days', 30, tags=('tag_name:tag1', ))
        self.assertMetric('mandrill.tags.clicks.last_7_days', 2, tags=('tag_name:tag1', ))
        self.assertMetric('mandrill.tags.clicks.today', 0, tags=('tag_name:tag1', ))

    def test_check(self):
        """
        Test that a normal api call emits the correct metrics
        """
        config = {
            'instances': [{
                'api_key': 'EXAMPLE_KEY',
            }]
        }

        with mock.patch('mandrill.Mandrill') as mandrill:
            mandrill.return_value = self._get_mock_client()

            self.run_check(config)
            self._assert_user_stats()
            self._assert_url_stats()
            self._assert_tag_stats()
