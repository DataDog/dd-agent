# stdlib
import os.path
import unittest
import re

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


def get_mocked_config_with_proxy():
    return {
        'api_key': 'APIKEY',
        'dd_url': 'https://app.datadoghq.com',
        'skip_ssl_validation': True,
        'proxy_settings': {
            'host': 'proxy.host.com',
            'port': 3128,
            'user': 'proxy_user',
            'password': 'proxy_pass',
        }
    }


def get_mocked_version():
    return '6.6.6'


def get_mocked_temp():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'fixtures',
        'flare'
    )

mock_cfgs = {
    'uri_password' : 'password_uri.yaml',
}

password_tests = {
    'uri_password' : '      -   server: mongodb://datadog:V3pZC7ghx1ne82XkyqLnOW36@localhost:27017/admin',
    'uri_password_2' : '      -   server: mongodb://datadog:V3!pZC7ghx1ne8#-2XkyqLnOW36!?@localhost:27017/admin',
    'uri_password_expected' : '      -   server: mongodb://datadog:********@localhost:27017/admin',
}


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
        self.assertEqual(f.tar_path, os.path.join(get_mocked_temp(), "datadog-agent-1.tar.bz2"))

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

    @mock.patch('utils.flare.requests.post', return_value=FakeResponse())
    @mock.patch('config.get_version', side_effect=get_mocked_version)
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config_with_proxy)
    def test_upload_with_case_proxy(self, mock_config, mock_tempdir, mock_stfrtime, mock_version, mock_requests):
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
        assert kwargs['proxies']['https'] == 'http://proxy_user:proxy_pass@proxy.host.com:3128'
        assert not kwargs['verify']

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

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_uri_password(self, mock_config, mock_tempdir, mock_strftime):
        f = Flare()
        _, credentials_log = f._strip_credentials(
            os.path.join(get_mocked_temp(), mock_cfgs['uri_password']),
            f.CHECK_CREDENTIALS
        )
        self.assertEqual(
            credentials_log,
            " - this file contains a credential (password in a uri) which has been removed in the collected version"
        )

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_uri_password_regex(self, mock_config, mock_tempdir, mock_strftime):
        f = Flare()
        password_uri_pattern = filter(
            lambda cred_pattern: cred_pattern.label == 'password in a uri',
            f.CHECK_CREDENTIALS
        ).pop()

        line = re.sub(password_uri_pattern.pattern, password_uri_pattern.replacement, password_tests['uri_password'])
        self.assertEqual(
            line,
            password_tests['uri_password_expected']
        )

        line = re.sub(password_uri_pattern.pattern, password_uri_pattern.replacement, password_tests['uri_password_2'])
        self.assertEqual(
            line,
            password_tests['uri_password_expected']
        )

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config_with_proxy)
    def test_uri_set_proxy(self, mock_config, mock_tempdir, mock_strftime):
        f = Flare()
        request_options = {}
        f.set_proxy(request_options)
        expected = 'http://proxy_user:proxy_pass@proxy.host.com:3128'
        self.assertEqual(expected, request_options['proxies']['https'])

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config_with_proxy)
    def test_uri_no_verify_ssl(self, mock_config, mock_tempdir, mock_strftime):
        f = Flare()
        request_options = {}
        f.set_ssl_validation(request_options)
        self.assertFalse(request_options['verify'])

    @attr(requires='core_integration')
    @mock.patch('utils.flare.strftime', side_effect=mocked_strftime)
    @mock.patch('tempfile.gettempdir', side_effect=get_mocked_temp)
    @mock.patch('utils.flare.get_config', side_effect=get_mocked_config)
    def test_uri_verify_ssl_default(self, mock_config, mock_tempdir, mock_strftime):
        f = Flare()
        request_options = {}
        f.set_ssl_validation(request_options)
        self.assertEquals(request_options.get('verify'), None)
