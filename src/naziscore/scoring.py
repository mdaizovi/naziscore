# -*- coding:utf-8 -*-

import datetime
import json
import logging
import os

from inspect import isfunction

from google.appengine.api import taskqueue
from naziscore.models import Score

from naziscore.deplorable_constants import (
    FAKE_NEWS_WEBSITES,
    HASHTAGS,
    PEPES,
    TRIGGERS,
)


def get_score_by_screen_name(screen_name, depth):
    score = Score.query(Score.screen_name == screen_name).get()
    if score is None:
        try:
            taskqueue.Task(
                name=('{}_{}'.format(
                    screen_name,
                    os.environ['CURRENT_VERSION_ID'].split('.')[0])),
                params={
                    'screen_name': screen_name,
                    'depth': depth
                }).add(
                    'scoring')
        except taskqueue.TaskAlreadyExistsError:
            # We already are going to check this person. There is nothing
            # to do here.
            logging.warning(
                'Fetch for {} already scheduled'.format(screen_name))
        except taskqueue.TombstonedTaskError:
            # This task is too recent. We shouldn't try again so soon.
            logging.warning('Fetch for {} tombstoned'.format(screen_name))
        return None
    else:
        return score


def get_score_by_twitter_id(twitter_id, depth):
    score = Score.query(Score.twitter_id == twitter_id).get()
    if score is None:
        try:
            taskqueue.Task(
                name=('{}_{}'.format(
                    twitter_id,
                    os.environ['CURRENT_VERSION_ID'].split('.')[0])),
                params={
                    'twitter_id': twitter_id,
                    'depth': depth
                }).add(
                    'scoring')
        except taskqueue.TaskAlreadyExistsError:
            # We already are going to check this person. There is nothing
            # to do here.
            pass
        except taskqueue.TombstonedTaskError:
            # This task is too recent. We shouldn't try again so soon.
            logging.warning('Fetch for {} tombstoned'.format(twitter_id))
            pass
        return None
    else:
        return score


def calculated_score(profile_json, posts_json, depth):
    """Returns the score for the recent posts JSON"""
    g = globals()
    total = 0
    profile = json.loads(profile_json)
    timeline = json.loads(posts_json)
    if 'error' in timeline and timeline['error'] == 'Not authorized.':
        logging.warning('{} is private'.format(profile['screen_name']))
        timeline = []  # There are no tweets to check, user is private
    for grader in [
            g[f] for f in g
            if isfunction(g[f]) and f.startswith('points_from')]:
        logging.info('Calling ' + grader.__repr__())
        total += grader(profile, timeline, depth)
    return total


def points_from_gabai(profile, timeline, depth):
    "Returns 1 if 'gab.ai' is in the profile name or description."
    result = (1 if 'gab.ai' in profile['description']
              or 'gab.ai' in profile['name']
              else 0)
    if result > 0:
        logging.info(
            '{} scored {} for gab.ai'.format(profile['screen_name'], result))
    return result


def trigger_count(triggers, profile, timeline):
    """Counts the number of times a trigger from triggers appears in the
    profile or timeline."""
    result = 0
    tweets = [t['text'] for t in timeline]  # Could use ['status']['text'].
    for trigger in triggers:
        # Check the profile
        result += 1 if trigger in profile['screen_name'].lower() else 0
        result += 1 if trigger in profile['name'].lower() else 0
        result += 1 if trigger in profile['description'].lower() else 0
        # Check the tweets themselves
        for tweet in tweets:
            result += 1 if trigger in tweet.lower() else 0
    return result


def points_from_pepes(profile, timeline, depth):
    "Returns the number of different racist symbols in the name and tweets."
    result = trigger_count(PEPES, profile, timeline)
    if result > 0:
        logging.info(
            '{} scored {} for pepes'.format(profile['screen_name'], result))
    return result


def points_from_hashtags(profile, timeline, depth):
    "Returns the number of trigger hasthags in the profile and tweets."
    # Hashtags also appear under ['status']['entities']['hashtags']
    result = trigger_count(HASHTAGS, profile, timeline)
    if result > 0:
        logging.info(
            '{} scored {} for hashtags'.format(profile['screen_name'], result))
    return result


def points_from_triggers(profile, timeline, depth):
    "Returns the number of trigger hasthags in the profile and tweets."
    result = trigger_count(TRIGGERS, profile, timeline)
    if result > 0:
        logging.info(
            '{} scored {} for triggers'.format(profile['screen_name'], result))
    return result


def points_from_retweets(profile, timeline, depth):
    "Returns a fraction of the score of each retweeted author."
    if depth > 1:
        logging.warning(  # TODO: This should be info when in production.
            '{} exceeded max depth at {}'.format(
                profile['screen_name'], depth))
        return 0
    else:
        result = 0
        logging.info(
            'Recursively looking into {} at depth {}'.format(
                profile['screen_name'], depth))
        authors = [
            t['retweeted_status']['user']['screen_name']
            for t in timeline if 'retweeted_status' in t]
        for screen_name in authors:
            score = get_score_by_screen_name(screen_name, depth + 1)
            result += score.score * .125 if score is not None else 0
        if result > 0:
            logging.info(
                '{} scored {} for retweets'.format(
                    profile['screen_name'], result))
        return result


def points_from_external_links(profile, timeline, depth):
    "Returns 0.03125 point for each link from the fake news sources."
    result = 0
    lists = [s for s in
             [t['retweeted_status']['entities']['urls']for t in
              timeline if 'retweeted_status' in t] if s] + [
                  t['entities']['urls'] for t in timeline if 'entities' in t]
    for l in lists:
        for u in l:
            for fnw in FAKE_NEWS_WEBSITES:
                result += 0.03125 if fnw in u['expanded_url'] else 0
    if result > 0:
        logging.info(
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
    "Returns 1 if the account has fewer than 11 followes, 3 if it has none."
    if profile['followers_count'] == 0:
        result = 3
    elif profile['followers_count'] < 11:
        result = 1
    else:
        result = 0
    if result > 0:
        logging.info(
            '{} scored {} for low folower count'.format(
                profile['screen_name'], result))
    return result


def points_from_new_account(profile, timeline, depth):
    "Returns 1 if the profile is less than 30 days old."
    age = (datetime.datetime.now() - datetime.datetime.strptime(
        profile['created_at'], '%a %b %d %H:%M:%S +0000 %Y')).days
    if age < 30:
        result = 1
    else:
        result = 0
    if result > 0:
        logging.info(
            '{} scored {} for low folower count'.format(
                profile['screen_name'], result))
    return result
