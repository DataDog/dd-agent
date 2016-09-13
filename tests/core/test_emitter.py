# -*- coding: utf-8 -*-
# 3p
import unittest

# project
from emitter import remove_control_chars
from emitter import remove_control_chars_from


class TestEmitter(unittest.TestCase):

    def test_remove_control_chars(self):
        messages = [
            (u'#és9df\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00>\x00\x01\x00\x00\x00\x06@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00´wer0sf®ré', u'#és9dfELF>@@´wer0sf®ré'),
            ('AAAAAA', 'AAAAAA'),
            (u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪', u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪')
        ]

        for bad, good in messages:
            self.assertTrue(remove_control_chars(bad) == good, (bad,good))

    def test_remove_control_chars_from(self):
        bad_messages = [
            {"processes":[1234,[["d≤Ω≈ç√∫˜µ≤", 0, 2.2,12,34,"compiz",1]]]}
        ]
        good_messages = [
            {"processes":[1234,[["db", 0, 2.2,12,34,"compiz",1]]]}
        ]

        def is_converted_same(msg):
            new_msg = remove_control_chars_from(msg, None)
            if str(new_msg) == str(msg):
                return True
            return False

        for msg in bad_messages:
            self.assertFalse(is_converted_same(msg))

        for msg in good_messages:
            self.assertTrue(is_converted_same(msg))
