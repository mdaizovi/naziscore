# -*- coding:utf-8 -*-


from google.appengine.api import urlfetch


def fetch(url, payload=None, method=1, headers={}, allow_truncated=False,
          follow_redirects=True, deadline=None, validate_certificate=None):
    """Tries an anonymous fetch first and, if we are over quota, try again with
    our credentials.  """
    pass
