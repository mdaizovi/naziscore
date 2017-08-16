# -*- coding:utf-8 -*-

import logging
import urlparse

from ssl import CertificateError

from google.appengine.api import urlfetch
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
        except InvalidURLError as e:
            logging.info('fetching {} resulted in {}'.format(url, e))
            url = purl.scheme + '://' + purl.netloc + eu
        except (CertificateError,
                DeadlineExceededError,
                DownloadError,
                DNSLookupFailedError,
                ResponseTooLargeError,
                SSLCertificateError) as e:
            # This is as far as we'll go expanding this URL
            logging.error('fetching {} resulted in {}'.format(url, e))
            return url  # Return the last good one.
