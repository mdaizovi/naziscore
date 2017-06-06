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
user. Points are given according to the criteria listed below:

- #MAGA, #WhiteGenocide and similar hashtags in the profile
- #MAGA, #WhiteGenocide and similar hashtags in recent tweets
- Less than 10 followers
- Profile less than two months old
- Has a frog emoji in the name
- Has a gab.ai URL
- Used terms like "libtard" in recent tweets/retweets, description, name or screen-name.
- Retweets other scored accounts
- Likes offensive tweets
