import unittest

import json
import unittest

# The test will error out if we can't import these items
from google.appengine.ext import (
    ndb,
    testbed
)

from naziscore.models import Score


class ScoreModelTest(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        self.timeline = json.loads(open('tests/good_timeline.json').read())
        self.profile = json.loads(open('tests/good_profile.json').read())

    def tearDown(self):
        self.testbed.deactivate()

    def test_average_interval(self):
        "Make sure it returns None - we can't calculate it."
        score = Score(
            screen_name='TestUser',
            twitter_id=1234,
            timeline_text=self.timeline,
            profile_text=self.profile)
        self.assertEqual(score.get_average_interval(), 1)

    def test_follower_count(self):
        assert True

    def test_hashtags(self):
        assert True

    def test_websites(self):
        assert True

    def test_times(self):
        assert True

if __name__ == '__main__':
    unittest.main()
