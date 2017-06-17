# -*- coding:utf-8 -*-

import base64
import json
import logging
import urllib


from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from naziscore.credentials import (
    CUSTOMER_KEY,
    CUSTOMER_SECRET
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


@ndb.tasklet
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
        'https://api.twitter.com/1.1/statuses/user_timeline.json?count=90&'
        'screen_name={}'.format(
            screen_name))


def get_timeline_by_twitter_id(twitter_id):
    """Returns a dict from the Twitter GET statuses/user_timeline API.

    See https://dev.twitter.com/rest/reference/get/statuses/user_timeline"""
    return authenticated_get(
        'https://api.twitter.com/1.1/statuses/user_timeline.json?count=100&'
        'id={}'.format(
            twitter_id))
