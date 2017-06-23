# -*- coding:utf-8 -*-

import datetime
import itertools
import json
import logging
import urlparse

from google.appengine.ext import ndb


class Score(ndb.Model):
    "Keeps data on Twitter profiles"

    def get_average_interval(self):
        if self.timeline_text is not None:
            timeline = json.loads(self.timeline_text)
            if 'error' not in timeline:
                try:
                    oldest_date = datetime.datetime.strptime(
                        timeline[-1]['created_at'],
                        '%a %b %d %H:%M:%S +0000 %Y')
                    newest_date = datetime.datetime.strptime(
                        timeline[0]['created_at'],
                        '%a %b %d %H:%M:%S +0000 %Y')
                    return (newest_date - oldest_date).seconds
                except IndexError:
                    logging.warning(
                        'get_average_interval for {} could not be '
                        'calculated'.format(self.screen_name))
        return None

    def get_follower_count(self):
        profile = json.loads(self.profile_text)
        return profile['followers_count']

    def get_hashtags(self):
        if self.timeline_text is not None:
            timeline = json.loads(self.timeline_text)
            if 'error' not in timeline:
                return list(
                    itertools.chain(
                        *['#' + hashtag['text'] if 'text' in hashtag
                          else ['#' + ht['text'] for ht in hashtag]
                          for hashtag in [
                                  tweet['entities']['hashtags']
                                  for tweet in timeline
                                  if tweet['entities']['hashtags'] != []]]))
        return None

    def get_websites(self):
        if self.timeline_text is not None:
            timeline = json.loads(self.timeline_text)
            if 'error' not in timeline:
                lists = [s for s in
                         [t['retweeted_status']['entities']['urls']for t in
                          timeline if 'retweeted_status' in t] if s] + [
                              t['entities']['urls']
                              for t in timeline if 'entities' in t]
                return list(set([urlparse.urlparse(u['expanded_url']).netloc
                                 for u in itertools.chain(*lists)]))
        return None

    screen_name = ndb.StringProperty()
    screen_name_lower = ndb.ComputedProperty(
        lambda self: self.screen_name.lower())
    twitter_id = ndb.IntegerProperty()
    last_updated = ndb.DateTimeProperty(auto_now=True)
    score = ndb.ComputedProperty(
        lambda self: float(sum([self.grades[k] for k in self.grades])))
    grades = ndb.JsonProperty()

    # For refreshing scores without hitting the APIs
    profile_text = ndb.TextProperty()
    timeline_text = ndb.TextProperty()

    # For analytics
    follower_count = ndb.ComputedProperty(get_follower_count)
    avg_interval = ndb.ComputedProperty(get_average_interval)
    websites = ndb.ComputedProperty(get_websites, repeated=True)
    hashtags = ndb.ComputedProperty(get_hashtags, repeated=True)
