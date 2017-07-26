# -*- coding:utf-8 -*-

import os
import webapp2

from google.appengine.ext import ndb

from naziscore.handlers import CleanupRepeatedProfileHandler

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
        webapp2.Route(
            '/_ah/cron/cleanup', CleanupRepeatedProfileHandler,
            name='cleanup_handler_v1'),
    ],
    debug=DEBUG)

app = ndb.toplevel(app)
