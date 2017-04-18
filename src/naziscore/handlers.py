# -*- coding:utf-8 -*-

import json
import webapp2

from google.appengine.api import taskqueue

class ScoreHandler(webapp2.RequestHandler):

    def get(self, profileid):

        self.response.headers['Content-Type'] = 'application/json'
        # TODO: retrieve the score from the datastore. If not found, schedule a
        # calculation.
        obj = {'profileid': profileid,
               'score': 0}
        try:
            taskqueue.add(
                url='/calculate',
                name=profileid,
                params={'profileid': profileid})
        except TaskAlreadyExistsError:
            # We already are going to check this person. There is nothing to do
            # here.
            pass
        self.response.out.write(unicode(json.dumps(obj), encoding='utf-8'))

class CalculationHandler(webapp2.RequestHandler):
    def get(self, profileid=None):
        # TODO: Here we get the user's stream, profile and calculate their nazi
        # score aplying the criteria functions on the data and adding the
        # results.
        pass
