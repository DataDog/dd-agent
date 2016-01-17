# stdlib
import binascii
import logging
import os
from random import sample, shuffle
import re
import shutil
import unittest

# 3p
from nose.plugins.skip import SkipTest

# project
from tests.checks.common import get_check

log = logging.getLogger()


class TestPostfix(unittest.TestCase):
    #
    # you can execute this dd-agent unit test via python's nose tool
    #
    # example:
    #
    #     nosetests --nocapture --tests=dd-agent/tests/test_postfix.py
    #
    def setUp(self):
        self.queue_root = '/tmp/dd-postfix-test/var/spool/postfix'

        self.queues = [
            'active',
            'maildrop',
            'bounce',
            'incoming',
            'deferred'
        ]

        self.in_count = {}

        # create test queues
        for queue in self.queues:
            try:
                os.makedirs(os.path.join(self.queue_root, queue))
                self.in_count[queue] = [0, 0]
            except Exception:
                pass

    def tearDown(self):
        # clean up test queues
        shutil.rmtree('/tmp/dd-postfix-test')

    def stripHeredoc(self, text):
        indent = len(min(re.findall('\n[ \t]*(?=\S)', text) or ['']))
        pattern = r'\n[ \t]{%d}' % (indent - 1)
        return re.sub(pattern, '\n', text)

    def test_checks(self):
        raise SkipTest("Skipped for now as it needs sudo")
        self.config = self.stripHeredoc("""init_config:

        instances:
            - directory: %s
              queues:
                  - bounce
                  - maildrop
                  - incoming
                  - active
                  - deferred
        """ % (self.queue_root))

        # stuff 10K msgs in random queues
        for _ in xrange(1, 10000):
            shuffle(self.queues)
            rand_queue = sample(self.queues, 1)[0]
            queue_file = binascii.b2a_hex(os.urandom(7))

            open(os.path.join(self.queue_root, rand_queue, queue_file), 'w')

            # keep track of what we put in
            self.in_count[rand_queue][0] += 1

        check, instances = get_check('postfix', self.config)

        check.check(instances[0])
        out_count = check.get_metrics()

        # output what went in... per queue
        print
        for queue, count in self.in_count.iteritems():
            print 'Test messges put into', queue, '= ', self.in_count[queue][0]

        # output postfix.py dd-agent plugin counts... per queue
        print
        for tuple in out_count:
            queue = tuple[3]['tags'][0].split(':')[1]
            self.assertEquals(int(tuple[2]), int(self.in_count[queue][0]))
            print 'Test messages counted by dd-agent for', queue, '= ', tuple[2]

        #
        # uncomment this to see the raw dd-agent metric output
        #
        # print out_count
