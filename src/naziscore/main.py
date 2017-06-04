# -*- coding:utf-8 -*-

import os
import webapp2

from google.appengine.ext import ndb

from naziscore.handlers import (
    ScoreByIdHandler,
    ScoreByNameHandler,
)

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication(
    [
        # gives the score of a given profile, or 404 if the score isn't
        # calculated yet. If the score is not calculates, schedule a crawl over
        # the profile.
        webapp2.Route(
            '/v1/screen_name/<screen_name:.{1,15}>/score.json',
            ScoreByNameHandler, name='score_handler_by_screen_name_v1'),
        webapp2.Route(
            '/v1/twitter_id/<twitter_id:\d*>/score.json',
            ScoreByIdHandler, name='score_handler_by_idv1'),
    ],
    debug=DEBUG)

app = ndb.toplevel(app)
