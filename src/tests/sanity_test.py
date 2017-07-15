"""
Ensure the environment is sane
"""

# Do not add your own tests to this file. This file is intended for the sole
# purpose of confirming your environment was properly set-up

import datetime
import os
import unittest
import webtest

# The test will error out if we can't import these items
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed


# If your project has a src/main.py file, it'll check if it imports
try:
    from src import main
    TEST_HANDLER = True
except ImportError:
    TEST_HANDLER = False


class SanityTest(unittest.TestCase):
    """A simple sanity test. Everything here should past if the environment was
    properly set up."""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_urlfetch_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_sanity(self):
        """
        Tests the sanity of the unit testing framework and if we can import all
        we need to work
        """
        self.assertTrue(True)


class MemcacheTest(unittest.TestCase):
    """Tests if we can use the memcache from the testbed"""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_memcache(self):
        """Tests memcache"""
        memcache.set('test_key', 'contents')
        self.assertEqual(memcache.get('test_key'), 'contents')


if __name__ == '__main__':
    unittest.main()
