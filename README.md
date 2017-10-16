# Naziscore
A tool for assessing the naziness of a Twitter profile. Runs on Google
App Engine (https://cloud.google.com/appengine/) and is used by the 
Unpepefy browser extension (https://github.com/rbanffy/unpepefy).

# Basic idea
When a request arrives, we check if the score was already calculated. If
it was, we return the score and the date/time it was calculated. If it's
not found or was calculated more than 10 days ago, we queue a
recalculation.

# Endpoints
- GET /v1/screen_name/{name}/score.json returns the score as a JSON. If
  there is no data, it triggers a calculation.

- GET /v1/twitter_id/{id}/score.json returns the score as a JSON. If
  there is no data, it triggers a calculation.

# Criteria
The application gives a score based on the Twitter profile of the
user and their most recent tweets. See `scoring.py` for details.
