# -*- coding:utf-8 -*-

import logging
import urllib
import urlparse

from ssl import CertificateError

from google.appengine.api import (
    memcache,
    urlfetch
)
from google.appengine.api.urlfetch_errors import (
    DeadlineExceededError,
    DownloadError,
    DNSLookupFailedError,
    InvalidURLError,
    ResponseTooLargeError,
    SSLCertificateError
)


def expanded_url(url):
    "Expands the URL using the location header protocol. Returns the URL."
    # TODO: Memcache URLs - popular ones will tend to repeat.
    key = urllib.quote_plus(urlparse.urlparse(url).geturl())
    expanded = memcache.get(key)
    if expanded is not None:
        logging.info('URL expansion cache hit.')
        return expanded
    logging.info('URL expansion cache miss.')
    while True:
        try:
            eu = urlfetch.Fetch(
                url, follow_redirects=False).headers.get('location', url)
            purl = urlparse.urlparse(eu)
            if purl.scheme == '':  # It's relative (hopefully root-relative)
                purl = urlparse.urlparse(url)
                expanded = purl.scheme + '://' + purl.netloc + eu
                memcache.set(key, expanded)
                return expanded
            if url == eu:
                memcache.set(key, eu)
                return eu
            else:
                url = eu
        except InvalidURLError as e:
            logging.info('fetching {} resulted in {}'.format(url, e))
            url = purl.scheme + '://' + purl.netloc + eu
        except (CertificateError,
                DeadlineExceededError,
                DownloadError,
                DNSLookupFailedError,
                ResponseTooLargeError,
                SSLCertificateError) as e:
            # This is as far as we'll go expanding this URL, but since errors
            # can be transient, we won't cache this.
            logging.error('fetching {} resulted in {}'.format(url, e))
            return url  # Return the last good one.
