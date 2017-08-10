# -*- coding:utf-8 -*-

import urlparse

from google.appengine.api import urlfetch
from google.appengine.api.urlfetch_errors import (
    CertificateError,
    DNSLookupFailedError,
)

def expanded_url(url):
    "Expands the URL using the location header protocol. Returns the URL."
    # TODO: Memcache URLs - popular ones will tend to repeat.
    while True:
        try:
            eu = urlfetch.Fetch(
                url, follow_redirects=False).headers.get('location', url)
            purl = urlparse.urlparse(eu)
            if purl.scheme == '':  # It's relative (hopefully root-relative)
                purl = urlparse.urlparse(url)
                return purl.scheme + '://' + purl.netloc + eu
            if url == eu:
                return eu
            else:
                url = eu
        except (CertificateError, DNSLookupFailedError) as e:
            logging.error('fetching {} resulted in {}'.format(url, e))
            return url  # Return the last good one.
