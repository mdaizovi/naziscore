# -*- coding:utf-8 -*-

import json
import logging

from inspect import isfunction


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
        logging.info(profile['screen_name'] + 'tested positive for gab.ai')
    return result


def points_from_pepes(profile, timeline):
    "Returns the number of different racist symbols in the name."
    result = 0
    for pepe in u"🐸🥛👌":  # Pepe, milk and OK
        result += 1 if pepe in profile['name'] else 0
    if result > 0:
        logging.info(profile['screen_name'] + 'tested positive for pepe')
    return result
