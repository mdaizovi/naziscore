# -*- coding:utf-8 -*-

from google.appengine.ext import ndb


class Score(ndb.Model):
    """Our sample class"""
    profile_id = ndb.StringProperty()
    last_updated = ndb.DateTimeProperty(auto_now=True)
    score = ndb.FloatProperty()

    profile_text = ndb.TextProperty()
    timeline_text = ndb.TextProperty()
