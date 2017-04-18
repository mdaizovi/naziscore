# -*- coding:utf-8 -*-

import os
import webapp2

from google.appengine.ext import ndb

from naziscore.handlers import (
    CalculationHandler,
    ScoreHandler
)

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication(
    [
        # gives the score of a given profile, or 404 if the score isn't
        # calculated yet. If the score is not calculates, schedule a crawl over
        # the profile.
        webapp2.Route(
            '/<profileid>/score.json', ScoreHandler, name='score_handler'),
        webapp2.Route(
            '/calculate', CalculationHandler, name='calculation_handler')
    ],
    debug=DEBUG)

app = ndb.toplevel(app)
