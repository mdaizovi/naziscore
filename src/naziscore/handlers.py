# -*- coding:utf-8 -*-

import base64
import datetime
import json
import logging
import urllib
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch

from naziscore.credentials import (
    CUSTOMER_KEY,
    CUSTOMER_SECRET
)
from naziscore.models import Score
from naziscore.scoring import (
    calculated_score,
    get_score_by_screen_name,
    get_score_by_twitter_id,
)


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
    elif response.status_code == urlfetch.httplib.UNAUTHORIZED:
        return response.content  # User is probably suspended
    else:
        message = 'Url ' + url + ' returned ' + response.content
        logging.warning(message)
        raise urlfetch.httplib.HTTPException(message)


def get_profile(screen_name='', twitter_id=''):
    if screen_name != '':
        profile = get_profile_by_screen_name(screen_name)
    elif twitter_id != '':
        profile = get_profile_by_twitter_id(twitter_id)
    return profile


def get_profile_by_screen_name(screen_name):
    """Returns a dict from the Twitter GET users/show API.

    See https://dev.twitter.com/rest/reference/get/users/show"""
    return authenticated_get(
        'https://api.twitter.com/1.1/users/show.json?screen_name={}'.format(
            screen_name))


def get_profile_by_twitter_id(twitter_id):
    """Returns a dict from the Twitter GET users/show API.

    See https://dev.twitter.com/rest/reference/get/users/show"""
    return authenticated_get(
        'https://api.twitter.com/1.1/users/show.json?id={}'.format(
            twitter_id))


def get_timeline(screen_name='', twitter_id=''):
    if screen_name != '':
        timeline = get_timeline_by_screen_name(screen_name)
    elif twitter_id != '':
        timeline = get_timeline_by_twitter_id(twitter_id)
    return timeline


def get_timeline_by_screen_name(screen_name):
    """Returns a dict from the Twitter GET statuses/user_timeline API.

    See https://dev.twitter.com/rest/reference/get/statuses/user_timeline"""
    return authenticated_get(
        'https://api.twitter.com/1.1/statuses/user_timeline.json?'
        'screen_name={}'.format(
            screen_name))


def get_timeline_by_twitter_id(twitter_id):
    """Returns a dict from the Twitter GET statuses/user_timeline API.

    See https://dev.twitter.com/rest/reference/get/statuses/user_timeline"""
    return authenticated_get(
        'https://api.twitter.com/1.1/statuses/user_timeline.json?'
        'id={}'.format(
            twitter_id))


class ScoreByNameHandler(webapp2.RequestHandler):

    def get(self, screen_name):
        self.response.headers['Content-Type'] = 'application/json'
        screen_name = screen_name.lower()
        result = memcache.get('screen_name:' + screen_name)
        if result is None:
            # We don't have a cached result.
            score = get_score_by_screen_name(screen_name, depth=0)
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
                   'score': score.score}, encoding='utf-8')
                memcache.set('screen_name:' + screen_name, result, 3600)
        self.response.out.write(result)


class ScoreByIdHandler(webapp2.RequestHandler):

    def get(self, twitter_id):
        self.response.headers['Content-Type'] = 'application/json'
        twitter_id = int(twitter_id)
        result = memcache.get('twitter_id:{}'.format(twitter_id))
        if result is None:
            # We don't have a cached result.
            score = get_score_by_twitter_id(twitter_id, depth=0)
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
                     'score': score.score}, encoding='utf-8')
                memcache.set('twitter_id:{}'.format(twitter_id), result, 3600)
        self.response.out.write(result)


class CalculationHandler(webapp2.RequestHandler):
    """
    Makes requests to the Twitter API to retrieve the score.
    """
    def post(self):
        # TODO: Here we get the user's stream, profile and calculate their nazi
        # score aplying the criteria functions on the data and adding the
        # results.
        screen_name = self.request.get('screen_name')
        twitter_id = self.request.get('twitter_id')
        depth = int(self.request.get('depth'))
        if screen_name != '':
            screen_name = screen_name.lower()
            score = get_score_by_screen_name(screen_name, depth)
        elif twitter_id != '':
            twitter_id = int(twitter_id)
            score = get_score_by_twitter_id(twitter_id, depth)

        if score is None or score.last_updated < (
                datetime.datetime.now() - datetime.timedelta(days=7)):
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
                # We need to add a new one, but only if we got something back.
                if screen_name == '':
                    screen_name = json.loads(profile)['screen_name']
                elif twitter_id == '':
                    twitter_id = json.loads(profile)['id']

                Score(screen_name=screen_name,
                      twitter_id=twitter_id,
                      score=calculated_score(profile, timeline, depth),
                      profile_text=profile,
                      timeline_text=timeline).put()

            elif score is not None and score.last_updated < (
                    datetime.datetime.now() - datetime.timedelta(days=7)):
                # We need to either update or create a new one.
                    if timeline is not None:
                        score.score = calculated_score(
                            profile, timeline, depth)
                        score.put()
        else:
            # We have an up-to-date score. Nothing to do.
            pass
