# -*- coding:utf-8 -*-

from google.appengine.ext import ndb


class Score(ndb.Model):
    """Our sample class"""
    screen_name = ndb.StringProperty()
    twitter_id = ndb.IntegerProperty()
    last_updated = ndb.DateTimeProperty(auto_now=True)
    score = ndb.FloatProperty()

    profile_text = ndb.TextProperty()
    timeline_text = ndb.TextProperty()
