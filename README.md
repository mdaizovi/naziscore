# Naziscore
A tool for assessing the naziness of a Twitter profile. Runs on Google
App Engine.

# Basic idea
When a request arrives, we check if the score was already calculated. If
it was, we return the score and the date/time it was calculated. If it's
not found or was calculated more than a month ago, we recalculate and
store in the datastore (as a queued task).

# Endpoints
- GET /{name} returns a rendered HTML page with that person's score or a
  404 if there is no data (yet). It triggers a calculation.
- GET /{name}/score.json returns the score as a JSON. If there is no
  data, it triggers a calculation.

# Criteria
The application gives a score based on the Twitter profile of the
user and their most recent tweets. See `scoring.py` for details.
