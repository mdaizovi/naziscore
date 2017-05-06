# -*- coding:utf-8 -*-

"""
Validates the score calculation.
"""

import datetime
import os
import unittest
import webtest

# The test will error out if we can't import these items
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from naziscore.scoring import (
    score_from_profile,
    score_from_posts
)


class ProfileTest(unittest.TestCase):
    """Verifies the profile JSON is being scored properly."""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_neonazi(self):
        "Score a neonazi JSON"
        self.assertEqual(0, score_from_profile(""))


class PostsTest(unittest.TestCase):
    """Verifies the posts JSON is being scored properly."""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_neonazi(self):
        "Score a neonazi JSON"
        self.assertEqual(0, score_from_posts(""))


if __name__ == '__main__':
    unittest.main()
