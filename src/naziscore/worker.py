# -*- coding:utf-8 -*-

import os
import webapp2

from google.appengine.ext import ndb

from naziscore.handlers import CalculationHandler

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
        webapp2.Route(
            '/_ah/queue/scoring', CalculationHandler,
            name='calculation_handler_legacy_v1'),
        webapp2.Route(
            '/_ah/queue/scoring-direct', CalculationHandler,
            name='calculation_handler_direct_v1'),
        webapp2.Route(
            '/_ah/queue/scoring-indirect', CalculationHandler,
            name='calculation_handler_indirect_v1'),
        webapp2.Route(
            '/_ah/queue/refresh', CalculationHandler,
            name='calculation_refresh_v1'),
    ],
    debug=DEBUG)

app = ndb.toplevel(app)
