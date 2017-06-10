# -*- coding:utf-8 -*-

from google.appengine.ext import ndb


class Score(ndb.Model):
    """Our sample class"""
    screen_name = ndb.StringProperty()
    screen_name_lower = ndb.ComputedProperty(
        lambda self: self.screen_name.lower())
    twitter_id = ndb.IntegerProperty()
    last_updated = ndb.DateTimeProperty(auto_now=True)
    score = ndb.FloatProperty()
    grade = ndb.ComputedProperty(
        lambda self: float(sum([self.grades[k] for k in self.grades])))
    grades = ndb.JsonProperty()

    profile_text = ndb.TextProperty()
    timeline_text = ndb.TextProperty()
