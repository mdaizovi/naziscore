# -*- coding:utf-8 -*-

import logging

from google.appengine.api import urlfetch
from google.appengine.api.urlfetch_errors import DNSLookupFailedError

def expanded_url(url):
    "Expands the URL using the location header protocol. Returns the URL."
    # TODO: Memcache URLs - popular ones will tend to repeat.
    while True:
        try:
            eu = urlfetch.Fetch(
                url, follow_redirects=False).headers.get('location', url)
            if url == eu:
                return eu
            else:
                url = eu
        except DNSLookupFailedError:
            return url  # Return the last good one.
