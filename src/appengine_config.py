# -*- coding:utf-8 -*-

import os

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')


def webapp_add_wsgi_middleware(app):
    if DEBUG:
        from google.appengine.ext.appstats import recording
        app = recording.appstats_wsgi_middleware(app)
    return app
