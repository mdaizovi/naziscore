# -*- coding:utf-8 -*-

import base64
import json
import webapp2
import urllib
import logging

from google.appengine.api import taskqueue
from google.appengine.api import urlfetch

from naziscore.credentials import (
    CUSTOMER_KEY,
    CUSTOMER_SECRET
)
from naziscore.models import Score


def get_access_token():
    """Tries to obtain access token from memcache and, if it fails,
    obtains a new set and stores in memcache.

    See https://dev.twitter.com/oauth/application-only"""
    encoded_key = urllib.quote_plus(CUSTOMER_KEY)
    encoded_secret = urllib.quote_plus(CUSTOMER_SECRET)
    encoded_credentials = base64.b64encode(
        "{}:{}".format(encoded_key, encoded_secret))
    response = urlfetch.fetch(
        "https://api.twitter.com/oauth2/token",
        method=urlfetch.POST,
        headers={"Authorization": "Basic " + encoded_credentials})
    return json.loads(response.content)
    logging.debug(response.status_code)


def authenticated_get(
        url, customer_key=CUSTOMER_KEY, customer_secret=CUSTOMER_SECRET):
    """Performs an authenticated GET to the given URL.

    https://dev.twitter.com/oauth/application-only"""
    pass


def get_profile(profile_id):
    """Returns a dict from the Twitter GET users/show API.

    See https://dev.twitter.com/rest/reference/get/users/show"""
    pass


def get_timeline(profile_id):
    """Returns a dict from the Twitter GET statuses/user_timeline API.

    See https://dev.twitter.com/rest/reference/get/statuses/user_timeline"""
    pass


class ScoreHandler(webapp2.RequestHandler):

    def get(self, profile_id):

        self.response.headers['Content-Type'] = 'application/json'
        # TODO: retrieve the score from the datastore. If not found, schedule a
        # calculation.
        score = Score.query(Score.profile_id == profile_id).get()
        if score is None:
            try:
                taskqueue.add(
                    url='/calculate',
                    name=profile_id,
                    params={'profile_id': profile_id})
            except taskqueue.TaskAlreadyExistsError:
                # We already are going to check this person. There is nothing
                # to do here.
                pass
            obj = {'profile_id': profile_id,
                   'last_updated': None}
        else:
            obj = {'profile_id': score.profile_id,
                   'last_updated': score.last_updated.isoformat(),
                   'score': score.score}
        self.response.out.write(unicode(json.dumps(obj), encoding='utf-8'))


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
            if score is None:
                Score(profile_id=profile_id, score=0).put()
            else:
                score.score = 1
                score.put()
