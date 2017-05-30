# -*- coding:utf-8 -*-

import datetime
import base64
import json
import logging
import urllib
import webapp2

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch

from naziscore.credentials import (
    CUSTOMER_KEY,
    CUSTOMER_SECRET
)
from naziscore.models import Score
from naziscore.scoring import calculated_score


def get_access_token(force=False):
    """Tries to obtain access token from memcache and, if it fails,
    obtains a new set and stores in memcache.

    See https://dev.twitter.com/oauth/application-only"""
    token = memcache.get('access_token')
    if force or token is None:
        logging.warning('Needed to fetch access_token')
        encoded_key = urllib.quote_plus(CUSTOMER_KEY)
        encoded_secret = urllib.quote_plus(CUSTOMER_SECRET)
        encoded_credentials = base64.b64encode(
            "{}:{}".format(encoded_key, encoded_secret))
        response = urlfetch.fetch(
            'https://api.twitter.com/oauth2/token',
            payload='grant_type=client_credentials',
            method=urlfetch.POST,
            headers={'Authorization': 'Basic ' + encoded_credentials})
        if response.status_code == urlfetch.httplib.OK:
            response_data = json.loads(response.content)
            token = response_data['access_token']
            memcache.set('access_token', token, 2592000)  # 30 days
    return token


def authenticated_get(
        url, customer_key=CUSTOMER_KEY, customer_secret=CUSTOMER_SECRET):
    """Performs an authenticated GET to the given URL.

    https://dev.twitter.com/oauth/application-only"""
    token = get_access_token()
    response = urlfetch.fetch(
        url,
        method=urlfetch.GET,
        headers={'Authorization': 'Bearer ' + token})
    if response.status_code == urlfetch.httplib.OK:
        return response.content
    else:
        message = 'Url ' + url + ' returned ' + response.content
        logging.warning(message)
        raise urlfetch.httplib.HTTPException(message)


def get_profile(profile_id):
    """Returns a dict from the Twitter GET users/show API.

    See https://dev.twitter.com/rest/reference/get/users/show"""
    return authenticated_get(
        'https://api.twitter.com/1.1/users/show.json?screen_name={}'.format(
            profile_id))


def get_timeline(profile_id):
    """Returns a dict from the Twitter GET statuses/user_timeline API.

    See https://dev.twitter.com/rest/reference/get/statuses/user_timeline"""
    return authenticated_get(
        'https://api.twitter.com/1.1/statuses/user_timeline.json?'
        'screen_name={}'.format(
            profile_id))


class ScoreHandler(webapp2.RequestHandler):

    def get(self, profile_id):

        self.response.headers['Content-Type'] = 'application/json'
        # TODO: retrieve the score from memcache before trying the
        # datastore. If not found, schedule a calculation.
        score = Score.query(Score.profile_id == profile_id).get()
        if score is None:
            try:
                taskqueue.Task(
                    name=profile_id,
                    params={'profile_id': profile_id}).add(
                        'scoring')
            except taskqueue.TaskAlreadyExistsError:
                # We already are going to check this person. There is nothing
                # to do here.
                pass
            except taskqueue.TombstonedTaskError:
                # This task is too recent. We shouldn't try again so soon.
                pass

            obj = {'profile_id': profile_id,
                   'last_updated': None}
        else:
            obj = {'profile_id': score.profile_id,
                   'last_updated': score.last_updated.isoformat(),
                   'score': score.score}
        self.response.out.write(json.dumps(obj, encoding='utf-8'))


class CalculationHandler(webapp2.RequestHandler):
    """
    Makes requests to the Twitter API to retrieve the score.
    """
    def post(self):
        # TODO: Here we get the user's stream, profile and calculate their nazi
        # score aplying the criteria functions on the data and adding the
        # results.
        profile_id = self.request.get('profile_id')
        if profile_id is not None:
            score = Score.query(Score.profile_id == profile_id).get()
            if score is None or score.last_updated < (
                    datetime.datetime.now() - datetime.timedelta(days=7)):
                try:
                    profile = get_profile(profile_id)
                except urlfetch.httplib.HTTPException as e:
                    if 'User has been suspended' in e.message:
                        profile = None
                    else:
                        raise
                if profile is not None:
                    timeline = get_timeline(profile_id)
                    if timeline is not None:
                        Score(profile_id=profile_id,
                              score=calculated_score(profile, timeline),
                              profile_text=profile,
                              timeline_text=timeline).put()
            else:
                # We have a score. Nothing to do.
                pass
