# stdlib
from cStringIO import StringIO
import logging
import unittest

# project
from checks import LaconicFilter


class TestLaconic(unittest.TestCase):
    """Verify that we only output messages once
    """
    def setUp(self):
        self.l = logging.getLogger("test_laconic")
        self.sio = StringIO()

        # create console handler and set level to debug
        ch = logging.StreamHandler(self.sio)
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.l.addHandler(ch)

        self.laconic = LaconicFilter()
        self.l.addFilter(self.laconic)

    def tearDown(self):
        del self.l
        del self.sio

    def testRepeatingErrors(self):
        for i in range(10):
            self.l.error("Cannot find nagios.log")
        self.assertEquals(self.sio.getvalue().count("Cannot find nagios.log"), 1, self.sio.getvalue())

        for i in range(10):
            self.l.warn("Cannot find ganglia.log")
        self.assertEquals(self.sio.getvalue().count("Cannot find ganglia.log"), 1, self.sio.getvalue())

        for i in range(10):
            try:
                raise Exception("Ka-boom")
            except Exception:
                self.l.exception("Caught!")

        self.assertEquals(self.sio.getvalue().count("Ka-boom"), 2) # once for the traceback, once for the message

    def testNonRepeat(self):
        for i in range(10):
            self.l.error("Cannot find nagios.log %d" % i)
        self.assertEquals(self.sio.getvalue().count(" nagios.log"), 10)
        self.assertEquals(self.sio.getvalue().count(" 7"), 1)


    def testBlowUp(self):
        """Try to use a lot of memory"""
        for i in range(2 * self.laconic.LACONIC_MEM_LIMIT + 7):
            self.l.warn("""%d Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer
 adipiscing urna sed urna sagittis rutrum. Etiam elementum justo quis
 quam pellentesque vel porta eros vestibulum. Nulla nec felis
 lacus. Maecenas sit amet aliquet nunc. Curabitur non tellus eget
 sapien faucibus feugiat. Vivamus tortor nisl, posuere eget
 ullamcorper at, interdum id odio. Sed convallis, nisl quis luctus
 posuere, nulla sapien consequat magna, vitae euismod mauris felis et
 augue. Maecenas eget tortor elit. Cras eu nulla sit amet est
 hendrerit malesuada sit amet eu nibh. Aliquam erat volutpat. Cum
 sociis natoque penatibus et magnis dis parturient montes, nascetur
 ridiculus mus. Proin et erat diam, non venenatis dui. Etiam feugiat
 mattis nunc, tincidunt mollis quam condimentum eu. Donec volutpat
 sodales magna eu fermentum. Integer ultricies odio non metus aliquet
 tristique. Proin ultrices accumsan augue, quis tempor diam rutrum at.""" % i)
        self.assertEquals(len(self.laconic.hashed_messages), 7, self.sio.getvalue())
