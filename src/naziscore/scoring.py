# -*- coding:utf-8 -*-

import json
import logging

from inspect import isfunction

from naziscore.deplorable_constants import (
    PEPES,
    HASHTAGS
)


def calculated_score(profile_json, posts_json):
    """Returns the score for the recent posts JSON"""
    g = globals()
    total = 0
    profile = json.loads(profile_json)
    timeline = json.loads(posts_json)
    for grader in [
            g[f] for f in g
            if isfunction(g[f]) and f.startswith('points_from')]:
        logging.info('Calling ' + grader.__repr__())
        total += grader(profile, timeline)
    return total


def points_from_gabai(profile, timeline):
    "Returns 1 if 'gab.ai' is in the profile name or description."
    result = (1 if 'gab.ai' in profile['description']
              or 'gab.ai' in profile['name']
              else 0)
    if result > 0:
        logging.info(
            '{} scored {} for gab.ai'.format(profile['screen_name'], result))
    return result


def points_from_pepes(profile, timeline):
    "Returns the number of different racist symbols in the name and tweets."
    result = 0
    # Check the profile
    tweets = [t['text'] for t in timeline]
    for pepe in PEPES:  # Pepe, milk and OK
        result += 1 if pepe in profile['name'] else 0
        result += 1 if pepe in profile['description'] else 0
        # Check the tweets themselves
        for tweet in tweets:
            result += 1 if pepe in tweet else 0

    if result > 0:
        logging.info(
            '{} scored {} for gab.ai'.format(profile['screen_name'], result))
    return result


def points_from_magas(profile, timeline):
    "Returns the number of trigger hasthags in the profile and tweets."
    result = 0
    tweets = [t['text'] for t in timeline]
    for hashtag in HASHTAGS:
        # Check the profile
        result += 1 if hashtag in profile['name'] else 0
        result += 1 if hashtag in profile['description'] else 0
        # Check the tweets themselves
        for tweet in tweets:
            result += 1 if hashtag in tweet else 0

    if result > 0:
        logging.info(
            '{} scored {} for hashtags'.format(profile['screen_name'], result))
    return result
