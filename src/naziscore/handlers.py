# -*- coding:utf-8 -*-

import csv
import datetime
import json
import logging
import webapp2

from collections import Counter

from google.appengine.api import (
    memcache,
    urlfetch
)
from google.appengine.api.datastore_errors import Timeout
from google.appengine.ext import ndb
from google.appengine.runtime.apiproxy_errors import (
    CancelledError,
    OverQuotaError
)

from naziscore.deplorable_constants import KNOWN_SITES
from naziscore.models import Score
from naziscore.scoring import (
    calculated_score,
    get_score_by_screen_name,
    get_score_by_twitter_id,
    refresh_score_by_screen_name,
    MAX_DEPTH,
)
from naziscore.twitter import (
    get_profile,
    get_timeline,
)

MAX_AGE_DAYS = 10


class ScoreByNameHandler(webapp2.RequestHandler):
    "Returns the score JSON for a given screen_name."

    @ndb.toplevel
    def get(self, screen_name):
        self.response.headers['Content-Type'] = 'application/json'
        screen_name = screen_name.lower()
        result = memcache.get('screen_name:' + screen_name)
        if result is None:
            # We don't have a cached result.
            score = get_score_by_screen_name(screen_name, depth=0).get_result()
            if score is None:
                # We don't have a precalculated score.
                result = json.dumps(
                    {'screen_name': screen_name,
                     'last_updated': None}, encoding='utf-8')
                memcache.set(
                    'screen_name:' + screen_name, result, 5)  # 5 seconds
                expires_date = (datetime.datetime.utcnow()
                                + datetime.timedelta(seconds=2))
            else:
                # We have a score in the datastore.
                result = json.dumps(
                    {'screen_name': score.screen_name,
                     'twitter_id': score.twitter_id,
                     'last_updated': score.last_updated.isoformat(),
                     'score': score.score,
                     'grades': score.grades},
                    encoding='utf-8')
                memcache.set(
                    'screen_name:' + screen_name, result, 86400)  # 1 day
                expires_date = (datetime.datetime.utcnow()
                                + datetime.timedelta(1))
            expires_str = expires_date.strftime("%d %b %Y %H:%M:%S GMT")
            self.response.headers.add_header("Expires", expires_str)
        self.response.out.write(result)


class ScoreByIdHandler(webapp2.RequestHandler):
    "Returns the score JSON object for a given twitter id."

    @ndb.toplevel
    def get(self, twitter_id):
        self.response.headers['Content-Type'] = 'application/json'
        twitter_id = int(twitter_id)
        result = memcache.get('twitter_id:{}'.format(twitter_id))
        if result is None:
            # We don't have a cached result.
            score = get_score_by_twitter_id(twitter_id, depth=0).get_result()
            if score is None:
                # We don't have a precalculated score.
                result = json.dumps(
                    {'twitter_id': twitter_id,
                     'last_updated': None}, encoding='utf-8')
                memcache.set(
                    'twitter_id:{}'.format(twitter_id), result, 5)  # 5 seconds
                expires_date = (datetime.datetime.utcnow()
                                + datetime.timedelta(seconds=60))
            else:
                # We have a score in the datastore.
                result = json.dumps(
                    {'screen_name': score.screen_name,
                     'twitter_id': score.twitter_id,
                     'last_updated': score.last_updated.isoformat(),
                     'score': score.score,
                     'grades': score.grades}, encoding='utf-8')
                memcache.set('twitter_id:{}'.format(twitter_id), result, 86400)
                expires_date = (datetime.datetime.utcnow()
                                + datetime.timedelta(1))
            expires_str = expires_date.strftime("%d %b %Y %H:%M:%S GMT")
            self.response.headers.add_header("Expires", expires_str)
        self.response.out.write(result)


class CalculationHandler(webapp2.RequestHandler):
    """Main scoring entry point, tries to get JSON from memcache and, if that
    fails, tries to get it from the datastore. If that fails or the result is
    too old, schedule a recalculation through the queues while returning
    present data if found or a no-data JSON response if not. Called from the
    task queues.

    """
    @ndb.toplevel
    def post(self):
        screen_name = self.request.get('screen_name')
        twitter_id = self.request.get('twitter_id')
        depth = int(self.request.get('depth'))
        # Select the appropriate method based on what information we got. Try
        # to get a valid score instance.
        if screen_name != '':
            score = get_score_by_screen_name(screen_name, depth).get_result()
        elif twitter_id != '':
            twitter_id = int(twitter_id)
            score = get_score_by_twitter_id(twitter_id, depth).get_result()

        # Skip if the score already exists and is less than MAX_AGE_DAYS days
        # old.
        if score is None or score.last_updated < (
                datetime.datetime.now()
                - datetime.timedelta(days=MAX_AGE_DAYS)):
            # We'll need the profile and timeline data.
            try:
                profile = get_profile(screen_name, twitter_id)
            except urlfetch.httplib.HTTPException as e:
                profile = None
                if 'User has been suspended.' in e.message:
                    logging.warning('{} has been suspended'.format(
                        screen_name if screen_name else twitter_id))
                elif 'User not found.' in e.message:
                    logging.warning('{} does not exist'.format(
                        screen_name if screen_name else twitter_id))
                    # Delete previous scores, if they exist.
                    if screen_name is not None:
                        ndb.delete_multi(
                            Score.query(
                                Score.screen_name == screen_name).fetch(
                                    keys_only=True))
                    elif twitter_id is not None:
                        ndb.delete_multi(
                            Score.query(
                                Score.twitter_id == twitter_id).fetch(
                                    keys_only=True))
                    logging.info('Deleted old score for {}'.format(
                         screen_name or twitter_id))
                else:
                    raise  # Will retry later.
            if profile is not None:
                timeline = get_timeline(screen_name, twitter_id)
            else:
                timeline = None

            if score is None and profile is not None:
                # We need to add a new one, but only if we got something back
                # from the Twitter API.
                screen_name = json.loads(profile)['screen_name']
                key_name = (
                    '.' + screen_name.lower() if screen_name.startswith('__')
                    else screen_name.lower())
                twitter_id = json.loads(profile)['id']
                grades = calculated_score(profile, timeline, depth)
                Score(key=ndb.Key(Score, key_name),
                      screen_name=screen_name,
                      twitter_id=twitter_id,
                      grades=grades,
                      profile_text=profile,
                      timeline_text=timeline).put()
                logging.info(
                    'Created new score entry for {}'.format(screen_name))

            elif score is not None and score.last_updated < (
                    datetime.datetime.now()
                    - datetime.timedelta(days=MAX_AGE_DAYS)):

                if timeline is not None:
                    grades = calculated_score(profile, timeline, MAX_DEPTH)
                    score.grades = grades
                score.put()
                logging.info(
                    'Updated score entry for {}'.format(screen_name))

        else:
            # We have an up-to-date score. Nothing to do.
            pass


class UpdateOffenderFollowersHandler(webapp2.RequestHandler):

    @ndb.toplevel
    def post(self):
        """
        Iterate over the most offensive profiles and start analyses of their
        followers.
        """
        for score in Score.query().order(-Score.score).iter():
            pass


# TODO: Cleanup should no longer be about duplicates, but about removing
# records that were not updated in the past 15 days (or so). We should also
# consider getting rid of zero scores older than 10 days (because queues hold
# names for about 9 days). Since they are automatically refreshed after 10
# days, anything older than that has not been needed in at least 5 days.
class CleanupRepeatedProfileHandler(webapp2.RequestHandler):
    "Removes scores with repeated twitter_id. Keep the first."

    @ndb.toplevel
    def get(self):
        pass


class WorstHandler(webapp2.RequestHandler):
    "Retrieves the n worst scores and returns it as a CSV."

    def get(self):
        "Naïve implementation."
        response_writer = csv.writer(
            self.response, delimiter=',', quoting=csv.QUOTE_ALL)
        # Using GQL as a test - will create new index
        for line in ndb.gql(
                'select distinct screen_name, twitter_id, score '
                'from Score order by score desc limit 20000'):
            response_writer.writerow(
                [line.screen_name, line.twitter_id, line.score])


class WorstHashtagsHandler(webapp2.RequestHandler):
    "Gets the hashtags most used by the worst offenders as a CSV."

    def get(self):
        "Naïve implementation."
        response_writer = csv.writer(
            self.response, delimiter=',', quoting=csv.QUOTE_ALL)
        c = Counter()
        for s in Score.query().order(-Score.score).iter(
                    limit=5000, projection=(Score.hashtags)):
            if s.hashtags is not None:
                c.update((h.lower() for h in s.hashtags))
        for tag, tag_count in c.most_common(100):
            response_writer.writerow(
                [tag, tag_count])


class WorstWebsitesHandler(webapp2.RequestHandler):
    "Gets the websites most used by the worst offenders as a CSV."

    def get(self):
        "Naïve implementation."
        response_writer = csv.writer(
            self.response, delimiter=',', quoting=csv.QUOTE_ALL)
        c = Counter()
        for s in Score.query().order(-Score.score).iter(
                    limit=5000, projection=(Score.websites)):
            if s.websites is not None:
                c.update((h.lower() for h in s.websites))
        for site, site_count in c.most_common(200):
            response_writer.writerow(
                [site, site_count])


class WorstUnknownWebsitesHandler(webapp2.RequestHandler):
    "Gets the uncatalogued websites most used by the worst offenders as a CSV."

    def get(self):
        "Naïve implementation."
        response_writer = csv.writer(
            self.response, delimiter=',', quoting=csv.QUOTE_ALL)
        c = Counter()
        for s in Score.query().order(-Score.score).iter(
                    limit=5000, projection=(Score.websites)):
            if s.websites is not None:
                c.update((h.lower() for h in s.websites
                          if h.lower() not in KNOWN_SITES))
        for site, site_count in c.most_common(200):
            response_writer.writerow(
                [site, site_count])
