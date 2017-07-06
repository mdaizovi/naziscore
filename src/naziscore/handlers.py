# -*- coding:utf-8 -*-

import csv
import datetime
import json
import logging
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api.datastore_errors import Timeout
from google.appengine.ext import ndb
from google.appengine.runtime.apiproxy_errors import CancelledError

from naziscore.models import Score
from naziscore.scoring import (
    calculated_score,
    get_score_by_screen_name,
    get_score_by_twitter_id,
    refresh_score_by_screen_name,
)
from naziscore.twitter import (
    get_profile,
    get_timeline,
)

MAX_AGE_DAYS = 7


class ScoreByNameHandler(webapp2.RequestHandler):

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
                    'screen_name:' + screen_name, result, 3600)  # 1 hour
        self.response.out.write(result)


class ScoreByIdHandler(webapp2.RequestHandler):

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
            else:
                # We have a score in the datastore.
                result = json.dumps(
                    {'screen_name': score.screen_name,
                     'twitter_id': score.twitter_id,
                     'last_updated': score.last_updated.isoformat(),
                     'score': score.score,
                     'grades': score.grades}, encoding='utf-8')
                memcache.set('twitter_id:{}'.format(twitter_id), result, 3600)
        self.response.out.write(result)


class CalculationHandler(webapp2.RequestHandler):
    """
    Makes requests to the Twitter API to retrieve the score. Called from the
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
                twitter_id = json.loads(profile)['id']
                grades = calculated_score(profile, timeline, depth)
                # TODO: Find a way to prevent duplication. Having a dedup cron
                # task is... embarrassing.
                Score(screen_name=screen_name,
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
                    grades = calculated_score(profile, timeline, depth)
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


class RefreshOutdatedProfileHandler(webapp2.RequestHandler):
    "Updates the oldest 5000 score entries. Called by the refresh cron job."

    def get(self):
        """
        Selects 5000 oldest entries and refreshes them.
        """
        for score in ndb.gql(
                'select distinct screen_name, last_updated from Score '
                'order by last_updated limit 5000'):
            refresh_score_by_screen_name(score.screen_name)


class CleanupRepeatedProfileHandler(webapp2.RequestHandler):
    "Removes scores with repeated twitter_id. Keep the first."

    def get(self):
        "Naïve implementation."
        scanned = 0
        deleted = 0
        previous = None
        before = datetime.datetime.now()
        gql = 'select twitter_id from Score '
        if memcache.get('cleanup_maxdupe') is not None:
            gql += 'where twitter_id > {} '.format(
                memcache.get('cleanup_maxdupe'))
            logging.warn(
                'starting cleanup from {}'.format(
                    memcache.get('cleanup_maxdupe')))
        gql += ' order by twitter_id'
        try:
            for line in ndb.gql(gql):
                scanned += 1
                memcache.set('cleanup_maxdupe', line.twitter_id)
                if previous == line.twitter_id:
                    line.key.delete()
                    deleted += 1
                    logging.info(
                        'Removing duplicate score for {} after scanning {}'
                        ', deleting {}'.format(
                            line.twitter_id, scanned, deleted))
                if (datetime.datetime.now() - before).seconds > 590:
                    # Bail out before we are kicked out
                    logging.warn('Bailing out before timing out')
                    return None
                else:
                    previous = line.twitter_id
        except Timeout:
            # We'll catch this one the next time.
            logging.warn('Recovered from a timeout')
        except CancelledError:
            # We should bail out now to avoid an error.
            logging.warn('Bailing out after a CancelledError')
            return None
        # If we got to this point, we are exiting normally after finishing
        # going over all scores. We can delete the bookmark from the cache.
        memcache.delete('cleanup_maxdups')
        logging.warn(
            'Cleanup completed, {} dupes deleted of {} scanned'.format(
                deleted, scanned))


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
