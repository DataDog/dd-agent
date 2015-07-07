# stdlib
import os.path
import unittest

# 3p
import mock
from nose.plugins.attrib import attr

# project
from utils.flare import Flare


def get_mocked_config():
    return {
        'api_key': 'APIKEY',
        'dd_url': 'https://app.datadoghq.com',
    }


def get_mocked_version():
    return '6.6.6'


def get_mocked_temp():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'flare'
    )


def mocked_strftime(t):
    return '1'


class FakeResponse(object):
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = '{"case_id":1337}'

    def json(self):
        return {'case_id': 1337}

    def raise_for_status(self):
        return None


class FlareTest(unittest.TestCase):

    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('config.get_version', side_effect=get_mocked_version)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_init(self, mock_config, mock_version, mock_tempdir, mock_strftime):
        f = Flare(case_id=1337)
        conf = mock_config()
        self.assertEqual(f._case_id, 1337)
        self.assertEqual(f._api_key, conf['api_key'])
        self.assertEqual(f._url, 'https://6-6-6-flare.agent.datadoghq.com/support/flare')
        self.assertEqual(f._tar_path, os.path.join(get_mocked_temp(), "datadog-agent-1.tar.bz2"))

    @mock.patch('utils.flare.requests.post', return_value=FakeResponse())
    @mock.patch('config.get_version', side_effect=get_mocked_version)
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_upload_with_case(self, mock_config, mock_tempdir, mock_stfrtime, mock_version, mock_requests):
        f = Flare(case_id=1337)
        f._ask_for_email = lambda: 'test@example.com'

        assert not mock_requests.called
        f.upload()
        assert mock_requests.called
        args, kwargs = mock_requests.call_args_list[0]
        self.assertEqual(
            args,
            ('https://6-6-6-flare.agent.datadoghq.com/support/flare/1337?api_key=APIKEY',)
        )
        self.assertEqual(
            kwargs['files']['flare_file'].name,
            os.path.join(get_mocked_temp(), "datadog-agent-1.tar.bz2")
        )
        self.assertEqual(kwargs['data']['case_id'], 1337)
        self.assertEqual(kwargs['data']['email'], 'test@example.com')
        assert kwargs['data']['hostname']

    @mock.patch('utils.flare.requests.post', return_value=FakeResponse())
    @mock.patch('config.get_version', side_effect=get_mocked_version)
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_upload_no_case(self, mock_config, mock_tempdir, mock_stfrtime, mock_version, mock_requests):
        f = Flare()
        f._ask_for_email = lambda: 'test@example.com'

        assert not mock_requests.called
        f.upload()
        assert mock_requests.called
        args, kwargs = mock_requests.call_args_list[0]
        self.assertEqual(
            args,
            ('https://6-6-6-flare.agent.datadoghq.com/support/flare?api_key=APIKEY',)
        )
        self.assertEqual(
            kwargs['files']['flare_file'].name,
            os.path.join(get_mocked_temp(), "datadog-agent-1.tar.bz2")
        )
        self.assertEqual(kwargs['data']['case_id'], None)
        self.assertEqual(kwargs['data']['email'], 'test@example.com')
        assert kwargs['data']['hostname']

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_endpoint(self, mock_config, mock_temp, mock_stfrtime):
        f = Flare()
        f._ask_for_email = lambda: None
        try:
            f.upload()
            raise Exception('Should fail before')
        except Exception, e:
            self.assertEqual(str(e), "Your request is incorrect: Invalid inputs: 'API key unknown'")
