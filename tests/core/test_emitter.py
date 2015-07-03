# -*- coding: utf-8 -*-
# 3p
import unittest

# project
from emitter import remove_control_chars


class TestEmitter(unittest.TestCase):

    def test_remove_control_chars(self):
        messages = [
            (u'#és9df\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00>\x00\x01\x00\x00\x00\x06@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00´wer0sf®ré', u'#és9dfELF>@@´wer0sf®ré'),
            ('AAAAAA', 'AAAAAA'),
            (u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪', u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪')
        ]

        for bad, good in messages:
            self.assertTrue(remove_control_chars(bad) == good, (bad,good))
