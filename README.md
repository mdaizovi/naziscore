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
  404 if there is no data (yet).
- GET /{name}.json returns the score as a JSON.

# Criteria
The application gives a score based on the Twitter profile of the
user. Points are given according to the criteria listed below:

- #MAGA hashtag in the profile
- #MAGA hashtag in recent tweets
- Less than 10 followers
- Profile less than two months old
- Has a frog emoji in the name
- Has a gab.ai URL
- Used terms like "libtard" in recent tweets
- The #WhiteGenocide hashtag in the profile
- The #WhiteGenocide hashtag in recent tweets
