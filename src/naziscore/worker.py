# -*- coding:utf-8 -*-

import os
import webapp2

from google.appengine.ext import ndb

from naziscore.handlers import CalculationHandler

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
        webapp2.Route(
            '/v1/worker/calculate', CalculationHandler,
            name='calculation_handler_v1')
    ],
    debug=DEBUG)

app = ndb.toplevel(app)
