# -*- coding:utf-8 -*-

"""
Validates the score calculation.
"""

import json
import unittest

# The test will error out if we can't import these items
from google.appengine.ext import testbed

from naziscore.scoring import (
    calculated_score,
    points_from_triggers,
    MAX_DEPTH
)


class ScoringTest(unittest.TestCase):
    """Verifies the profile JSON is being scored properly."""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        self.timeline = json.loads(open('tests/timeline.json').read())
        self.profile = json.loads(open('tests/profile.json').read())

    def tearDown(self):
        self.testbed.deactivate()

    def test_trigger_word_doesnt_misfire_for_URL(self):
        self.assertEqual(
            0, points_from_triggers(self.profile, self.timeline, MAX_DEPTH))



if __name__ == '__main__':
    unittest.main()
