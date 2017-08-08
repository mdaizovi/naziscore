# -*- coding:utf-8 -*-

from google.appengine.api import urlfetch


def expanded_url(url):
    "Expands the URL using the location header protocol. Returns the URL."
    # TODO: Memcache URLs - popular ones will tend to repeat.
    while True:
        eu = urlfetch.Fetch(
            url, follow_redirects=False).headers.get('location', url)
        if url == eu:
            return eu
        else:
            url = eu
