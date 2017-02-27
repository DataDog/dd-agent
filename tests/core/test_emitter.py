# -*- coding: utf-8 -*-
# 3p
from mock import Mock
import unittest
import simplejson as json

# project
from emitter import (
    remove_control_chars,
    remove_undecodable_chars,
    sanitize_payload,
    split_payload
)

import os

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'payloads')

class TestEmitter(unittest.TestCase):


    def test_payload_splitter(self):
        with open(FIXTURE_PATH + '/legacy_payload.json') as f:
            legacy_payload = json.load(f)

        legacy_payload_split, metrics_payload = split_payload(dict(legacy_payload))
        series = metrics_payload['series']
        legacy_payload_split['metrics'] = []

        for s in series:
            attributes = {}

            if s.get('type'):
                attributes['type'] = s['type']
            if s.get('host'):
                attributes['hostname'] = s['host']
            if s.get('tags'):
                attributes['tags'] = s['tags']
            if s.get('device'):
                attributes['device_name'] = s['device']

            formatted_sample = [s['metric'], s['points'][0][0], s['points'][0][1], attributes]
            legacy_payload_split['metrics'].append(formatted_sample)

        self.assertEqual(legacy_payload, legacy_payload_split)

    def test_remove_control_chars(self):
        messages = [
            (u'#és9df\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00>\x00\x01\x00\x00\x00\x06@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00´wer0sf®ré', u'#és9dfELF>@@´wer0sf®ré'),
            ('AAAAAA', 'AAAAAA'),
            (u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪', u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪')
        ]

        log = Mock()
        for bad, good in messages:
            self.assertTrue(remove_control_chars(bad, log) == good, (bad,good))

    def test_remove_control_chars_from_payload(self):
        bad_messages = [
            (
                {"processes":[1234,[[u'☢cd≤Ω≈ç√∫˜µ≤\r\n', 0, 2.2,12,34,'compiz\r\n',1]]]},
                {"processes":[1234,[[u'☢cd≤Ω≈ç√∫˜µ≤', 0, 2.2,12,34,'compiz',1]]]}
            ),
            (
                (u'☢cd≤Ω≈ç√∫˜µ≤\r', ),
                (u'☢cd≤Ω≈ç√∫˜µ≤', )
            )
        ]
        good_messages = [
            {"processes":[1234,[[u'db🖫', 0, 2.2,12,34,u'☢compiz☢',1]]]}
        ]

        log = Mock()

        def is_converted_same(msg):
            new_msg = sanitize_payload(msg, log, remove_control_chars)
            if str(new_msg) == str(msg):
                return True
            return False

        for bad, good in bad_messages:
            self.assertFalse(is_converted_same(bad))
            self.assertTrue(sanitize_payload(bad, log, remove_control_chars) == good)

        for msg in good_messages:
            self.assertTrue(is_converted_same(msg))

    def test_remove_undecodable_characters(self):
        messages = [
            ('\xc3\xa9 \xe9 \xc3\xa7', u'é  ç', True),
            (u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪', u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪', False), # left unchanged
        ]

        for bad, good, log_called in messages:
            log = Mock()
            self.assertEqual(good, remove_undecodable_chars(bad, log))
            self.assertEqual(log_called, log.warning.called)
