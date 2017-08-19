# -*- coding:utf-8 -*-

import datetime
import json
import logging
import os

from inspect import isfunction
from itertools import chain

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.runtime.apiproxy_errors import OverQuotaError

from naziscore.models import Score

from naziscore.deplorable_constants import (
    ACTUAL_NEWS_WEBSITES,
    FAKE_NEWS_WEBSITES,
    HASHTAGS,
    PEPES,
    TRIGGERS,
    URL_MASKERS,
)

from naziscore.utils import expanded_url

# How much of the tree will be scanned. We stop at depth >= MAX_DEPTH
# +-----+----------------------------------------------+
# |Depth|Meaning                                       |
# +-----+----------------------------------------------+
# |  0  |We are scoring this from a direct API request.|
# +-----+----------------------------------------------+
# |  1  |This user is being scored because it was found|
# |     |in the feed of a directly scanned user.       |
# +-----+----------------------------------------------+
# |  2+ |This user was found on an indirectly scanned  |
# |     |user's feed.                                  |
# +-----+----------------------------------------------+
MAX_DEPTH = 1

# Scoring
POINTS_GABAI = 1

POINTS_PEPE_SCREEN_NAME = 2
POINTS_PEPE_NAME = 2
POINTS_PEPE_DESCRIPTION = 1
POINTS_PEPE_TWEET = 1

POINTS_HASHTAG_SCREEN_NAME = 2
POINTS_HASHTAG_NAME = 2
POINTS_HASHTAG_DESCRIPTION = 1
POINTS_HASHTAG_TWEET = 1

POINTS_TRIGGER_SCREEN_NAME = 2
POINTS_TRIGGER_NAME = 2
POINTS_TRIGGER_DESCRIPTION = 1
POINTS_TRIGGER_TWEET = 1

POINTS_RETWEET_FRACTION = 0.05

POINTS_FAKE_NEWS = 0.25
POINTS_ACTUAL_NEWS = - POINTS_FAKE_NEWS / 2  # Forgiveness is twice as hard.

POINTS_FEW_FOLLOWERS = 1
POINTS_NO_FOLLOWER = 3

POINTS_NEW_ACCOUNT = 1


@ndb.tasklet
def get_score_by_screen_name(screen_name, depth):
    # Gets the most recently updated copy, if duplicated.
    key_name = (
        '.' + screen_name if screen_name.startswith('__') else screen_name)
    try:
        score = yield ndb.Key(Score, key_name).get_async()
    except OverQuotaError:
        logging.critical('We are over quota.')
        raise ndb.Return(None)
    if score is None:
        # If we don't have one, we need to calculate one.
        try:
            yield taskqueue.Task(
                name=('{}_{}'.format(
                    screen_name,
                    os.environ['CURRENT_VERSION_ID'].split('.')[0])),
                params={
                    'screen_name': screen_name,
                    'depth': depth
                }).add_async(
                    'scoring-direct' if depth == 0 else 'scoring-indirect')
            # TODO: If we add it to the scoring-direct queue, we should remove
            # the corresponding task from the scoring-indirect queue at this
            # point.
        except taskqueue.TaskAlreadyExistsError:
            # We already are going to check this person. There is nothing
            # to do here.
            logging.warning(
                'Fetch for {} already scheduled'.format(screen_name))
        except taskqueue.TombstonedTaskError:
            # This task is too recent. We shouldn't try again so
            # soon. Thombstoning won't happen across different deploys, as the
            # task name has the deploy timestamp on it.
            logging.warning('Fetch for {} tombstoned'.format(screen_name))
        raise ndb.Return(None)
    else:
        raise ndb.Return(score)


@ndb.tasklet
def get_score_by_twitter_id(twitter_id, depth):
    try:
        score = yield Score.query(Score.twitter_id == twitter_id).get_async()
    except OverQuotaError:
        logging.critical(
            'Over quota fetching {}'.format(twitter_id))
        raise ndb.Return(None)
    if score is None:
        try:
            yield taskqueue.Task(
                name=('{}_{}'.format(
                    twitter_id,
                    os.environ['CURRENT_VERSION_ID'].split('.')[0])),
                params={
                    'twitter_id': twitter_id,
                    'depth': depth
                }).add_async(
                    'scoring-direct' if depth == 0 else 'scoring-indirect')
            # TODO: If we add it to the scoring-direct queue, we should remove
            # the corresponding task from the scoring-indirect queue at this
            # point.
        except taskqueue.TaskAlreadyExistsError:
            # We already are going to check this person. There is nothing
            # to do here.
            logging.warning(
                'Fetch for {} already scheduled'.format(twitter_id))
        except taskqueue.TombstonedTaskError:
            # This task is too recent. We shouldn't try again so
            # soon. Thombstoning won't happen across different deploys, as the
            # task name has the deploy timestamp on it.
            logging.warning('Fetch for {} tombstoned'.format(twitter_id))
        raise ndb.Return(None)
    else:
        raise ndb.Return(score)


def refresh_score_by_screen_name(screen_name):
    try:
        task = taskqueue.Task(
            name=('{}_{}'.format(
                screen_name,
                os.environ['CURRENT_VERSION_ID'].split('.')[0])),
            params={
                'screen_name': screen_name,
                'depth': MAX_DEPTH  # Prevent cascades
            })
        task.add('refresh')
    except taskqueue.TaskAlreadyExistsError:
        # We already are going to check this person. There is nothing
        # to do here.
        logging.warning('Refresh for {} already scheduled'.format(screen_name))
    except taskqueue.TombstonedTaskError:
        # This task is too recent. We shouldn't try again so soon.
        logging.warning('Refresh for {} tombstoned'.format(screen_name))


def calculated_score(profile_json, timeline_json, depth):
    """Returns the score for the recent posts JSON"""
    g = globals()
    grades = {}
    profile = json.loads(profile_json)
    timeline = json.loads(timeline_json)
    logging.info('Scoring {}'.format(profile['screen_name']))
    if 'error' in timeline and timeline['error'] == 'Not authorized.':
        logging.info('{} is private'.format(profile['screen_name']))
        timeline = []  # There are no tweets to check, user is private
    for grader in [
            g[f] for f in g
            if isfunction(g[f]) and f.startswith('points_from')]:
        logging.debug(
            'Calling {} for {}'.format(
                grader.func_name, profile['screen_name']))
        grade = grader(profile, timeline, depth)
        grades[grader.func_name] = grade
    return grades


def points_from_gabai(profile, timeline, depth):
    "Returns POINTS_GABAI if 'gab.ai' is in the profile name or description."
    result = (POINTS_GABAI if 'gab.ai' in profile['description'].lower()
              or 'gab.ai' in profile['name'].lower()
              else 0)
    if result > 0:
        logging.debug(
            '{} scored {} for gab.ai'.format(profile['screen_name'], result))
    return result


def trigger_count(triggers, profile, timeline, points_screen_name, points_name,
                  points_description, points_tweet):
    "Returns the score according to the trigger count in various elements."
    result = 0
    tweets = [
        (t['text'],
         [u['url'] for u in t['entities']['urls']])
        for t in timeline]  # Could use ['status']['text'].
    retweets = [
        (t['retweeted_statu']['text'],
         [u['url'] for u in t['retweeted_statu']['entities']['urls']])
        for t in timeline
        if 'retweeted_statu' in t]
    for trigger in triggers:
        # Check the profile
        result += (points_screen_name
                   if trigger in profile['screen_name'].lower() else 0)
        result += points_name if trigger in profile['name'].lower() else 0
        result += (points_description
                   if trigger in profile['description'].lower() else 0)
        # Check the tweets themselves
        for tweet, urls in chain(tweets, retweets):
            for url in urls:
                tweet = tweet.replace(url, '')  # Remove the URLs
            result += points_tweet if trigger in tweet.lower() else 0
    return result


def points_from_pepes(profile, timeline, depth):
    "Returns the number of different racist symbols in the name and tweets."
    result = trigger_count(
        PEPES, profile, timeline, POINTS_PEPE_SCREEN_NAME, POINTS_PEPE_NAME,
        POINTS_PEPE_DESCRIPTION, POINTS_PEPE_TWEET)
    if result > 0:
        logging.debug(
            '{} scored {} for pepes'.format(profile['screen_name'], result))
    return result


def points_from_hashtags(profile, timeline, depth):
    "Returns the number of trigger hasthags in the profile and tweets."
    # Hashtags also appear under ['status']['entities']['hashtags']
    result = trigger_count(
        HASHTAGS, profile, timeline, POINTS_HASHTAG_SCREEN_NAME,
        POINTS_HASHTAG_NAME, POINTS_HASHTAG_DESCRIPTION, POINTS_HASHTAG_TWEET)
    if result > 0:
        logging.debug(
            '{} scored {} for hashtags'.format(profile['screen_name'], result))
    return result


def points_from_triggers(profile, timeline, depth):
    "Returns the number of trigger hasthags in the profile and tweets."
    result = trigger_count(
        TRIGGERS, profile, timeline, POINTS_TRIGGER_SCREEN_NAME,
        POINTS_TRIGGER_NAME, POINTS_TRIGGER_DESCRIPTION, POINTS_TRIGGER_TWEET)
    if result > 0:
        logging.debug(
            '{} scored {} for triggers'.format(profile['screen_name'], result))
    return result


def points_from_retweets(profile, timeline, depth):
    "Returns a fraction of the score of each retweeted author."
    if depth >= MAX_DEPTH:
        logging.warning(  # TODO: This should be info when in production.
            '{} exceeded max depth at {}'.format(
                profile['screen_name'], depth))
        return 0
    else:
        result = 0
        logging.debug(
            'Recursively looking into {} at depth {}'.format(
                profile['screen_name'], depth))
        authors = [
            t['retweeted_status']['user']['screen_name']
            for t in timeline if 'retweeted_status' in t]
        for screen_name in authors:
            score = get_score_by_screen_name(
                screen_name, depth + 1).get_result()
            result += (score.score * POINTS_RETWEET_FRACTION
                       if score is not None else 0)
        if result > 0:
            logging.debug(
                '{} scored {} for retweets'.format(
                    profile['screen_name'], result))
        return result


def points_from_external_links(profile, timeline, depth):
    "Returns POINTS_FAKE_NEWS points for each link from fake news sources."
    result = 0
    lists = [s for s in
             [t['retweeted_status']['entities']['urls'] for t in
              timeline if 'retweeted_status' in t] if s] + [
                  t['entities']['urls'] for t in timeline if 'entities' in t]
    for l in lists:
        for u in l:
            url = u['expanded_url'] or u['url']
            for um in URL_MASKERS:
                if url.startswith('http://' + um) or url.startswith(
                            'https://' + um):
                    u['expanded_url'] = expanded_url(url)
                    break
            for nw in FAKE_NEWS_WEBSITES:
                if url.startswith('http://' + nw) or url.startswith(
                        'https://' + nw):
                    result += POINTS_FAKE_NEWS
                    break
    if result > 0:
        logging.debug(
            '{} scored {} for fake news'.format(
                profile['screen_name'], result))
    return result


def points_from_actual_news_sites(profile, timeline, depth):
    "Returns POINTS_ACTUAL_NEWS points for each link from actual news sources."
    result = 0
    lists = [s for s in
             [t['retweeted_status']['entities']['urls']for t in
              timeline if 'retweeted_status' in t] if s] + [
                  t['entities']['urls'] for t in timeline if 'entities' in t]
    for l in lists:
        for u in l:
            url = u['expanded_url'] or u['url']
            for um in URL_MASKERS:
                if url.startswith('http://' + um) or url.startswith(
                            'https://' + um):
                    u['expanded_url'] = expanded_url(url)
                    break
            for nw in ACTUAL_NEWS_WEBSITES:
                if url.startswith('http://' + nw) or url.startswith(
                        'https://' + nw):
                    result += POINTS_ACTUAL_NEWS
                    break
    if result > 0:
        logging.debug(
            '{} scored {} for fake news'.format(
                profile['screen_name'], result))
    return result


def points_from_people_followed(profile, timeline, depth):
    "Returns the average score from accounts followed whose score is >2."
    # TODO: this will require subsampling a friends list.
    # See https://dev.twitter.com/rest/reference/get/friends/list
    return 0


def points_from_favorites(profile, timeline, depth):
    "Returns trigger counts for the user's favorited posts"
    # TODO: will need to subsample favorites list
    # See https://dev.twitter.com/rest/reference/get/favorites/list
    return 0


def points_from_low_follower(profile, timeline, depth):
    """
    Returns POINTS_FOLLOW_LT_11 if the account has fewer than 11 followes,
    POINTS_NO_FOLLOWER if it has none.
    """
    if profile['followers_count'] == 0:
        result = POINTS_NO_FOLLOWER
    elif profile['followers_count'] < 11:
        result = POINTS_FEW_FOLLOWERS
    else:
        result = 0
    if result > 0:
        logging.debug(
            '{} scored {} for low folower count'.format(
                profile['screen_name'], result))
    return result


def points_from_new_account(profile, timeline, depth):
    "Returns POINTS_NEW_ACCOUNT if the profile is less than 30 days old."
    age = (datetime.datetime.now() - datetime.datetime.strptime(
        profile['created_at'], '%a %b %d %H:%M:%S +0000 %Y')).days
    if age < 30:
        result = POINTS_NEW_ACCOUNT
    else:
        result = 0
    if result > 0:
        logging.debug(
            '{} scored {} for low folower count'.format(
                profile['screen_name'], result))
    return result


@ndb.tasklet
def apply_adjustment_for_followers(followed_profile, follower_screen_names):
    """
    Apply a fraction of the score of followed_profile to all its followers.
    Updates the grades property of each user in follower_screen_names.
    """
    # TODO: This needs a push queue at 1/minute, a cron job to trigger it, a
    # triggering endpoint and a service endpoint.
    pass
