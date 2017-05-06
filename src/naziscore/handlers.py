# -*- coding:utf-8 -*-

import json
import webapp2

from google.appengine.api import taskqueue

from naziscore.credentials import (
    CUSTOMER_KEY,
    CUSTOMER_SECRET
)
from naziscore.models import Score


class ScoreHandler(webapp2.RequestHandler):

    def get(self, profile_id):

        self.response.headers['Content-Type'] = 'application/json'
        # TODO: retrieve the score from the datastore. If not found, schedule a
        # calculation.
        score = Score.query(Score.profile_id == profile_id).get()
        if score is None:
            try:
                taskqueue.add(
                    url='/calculate',
                    name=profile_id,
                    params={'profile_id': profile_id})
            except taskqueue.TaskAlreadyExistsError:
                # We already are going to check this person. There is nothing
                # to do here.
                pass
            obj = {'profile_id': profile_id,
                   'last_updated': None}
        else:
            obj = {'profile_id': score.profile_id,
                   'last_updated': score.last_updated.isoformat(),
                   'score': score.score}
        self.response.out.write(unicode(json.dumps(obj), encoding='utf-8'))


class CalculationHandler(webapp2.RequestHandler):
    """
    Makes requests to the Twitter API to retrieve the score.
    """
    def post(self):
        # TODO: Here we get the user's stream, profile and calculate their nazi
        # score aplying the criteria functions on the data and adding the
        # results.
        profile_id = self.request.get('profile_id')
        if profile_id is not None:
            score = Score.query(Score.profile_id == profile_id).get()
            if score is None:
                Score(profile_id=profile_id, score=0).put()
            else:
                score.score = 1
                score.put()
