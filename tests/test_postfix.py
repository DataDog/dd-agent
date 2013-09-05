from common import get_check
from random import shuffle, sample

# run/execute unittest for dd-agent (for example, a test as defined in https://github.com/DataDog/dd-agent/tree/master/tests) ??
# @conorb: Using nosetests, you can runs something like nosetests -v —tests=path/to/test_file.py
# @conorb: you'll have to easy_install/pip install nosetests first

import unittest
import os
import binascii
import re
import logging
import subprocess
import shutil

log = logging.getLogger()

class TestPostfix(unittest.TestCase):
    def setUp(self):
        self.queue_root = '/tmp/dd-postfix-test/var/spool/postfix'

        self.queues = [
            'active',
            'maildrop',
            'bounce',
            'incoming',
            'deferred'
        ]

        self.tally = {}

        # create test queues
        for queue in self.queues:
          try:
              os.makedirs(queue)
              # init tally dictionary
              self.tally[queue] = [0, 0]
          except Exception:
              pass

    def tearDown(self):
        # clean up test queues
        shutil.rmtree('/tmp/dd-postfix-test')

    def strip_heredoc(text):
        indent = len(min(re.findall('\n[ \t]*(?=\S)', text) or ['']))
        pattern = r'\n[ \t]{%d}' % (indent - 1)
        return re.sub(pattern, '\n', text)

    def testChecks(self):
        self.config = strip_heredoc("""init_config:

        instances:
            - directory: %s
              queues:
                  - bounce
                  - maildrop
                  - incoming
                  - active
                  - deferred
        """ % (self.queue_root) )

        # stuff 10K files in random queues
        for _ in xrange(1, 10000):
            shuffle(self.queues)
            rand_queue = sample(self.queues, 1)[0]
            queue_file = binascii.b2a_hex(os.urandom(7))

            open(os.path.join(self.queue_root, rand_queue, queue_file), 'w')

            # keep track of generated counts
            self.tally[rand_queue][0] += 1

        # set self.tally[rand_queue][1] to out_count (need to parse this into an integer for each queue)
        # compare self.tally[rand_queue][0] and self.tally[rand_queue][1] - if not equal, report failure

        check, instances = get_check('postfix', self.config)

        check.check(instances[0])
        out_count = check.get_metrics()

        print out_count

    if __name__ == '__main__':
        unittest.main()

