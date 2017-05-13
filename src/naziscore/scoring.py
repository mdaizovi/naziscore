# -*- coding:utf-8 -*-

import logging

from inspect import isfunction


def calculated_score(profile_json, posts_json):
    """Returns the score for the recent posts JSON"""
    g = globals()
    total = 0
    for grader in [
            g[f] for f in g
            if isfunction(g[f]) and f.startswith('points_from')]:
        logging.info('Calling ' + grader.__repr__())
        total += grader(profile_json, posts_json)
    return total


def points_from_gabai(profile_json, timeline_json):
    return 1


def points_from_pepes(profile_json, timeline_json):
    return 1
