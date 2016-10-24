# -*- coding: utf-8 -*-
# 3p
from mock import Mock
import unittest

# project
from emitter import (
    remove_control_chars,
    remove_undecodable_chars,
    sanitize_payload,
)


class TestEmitter(unittest.TestCase):

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
