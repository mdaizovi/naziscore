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


class AsyncURLExpander():
    def __init__(self, url):
        try:
            self.key = urllib.quote_plus(urlparse.urlparse(url).geturl())
        except KeyError:
            logging.error(u"Couldn't parse {}".format(url))
            raise
        self.expanded = memcache.get(self.key)
        rpc = urlfetch.create_rpc()
        if self.expanded is None:
            self.rpc = urlfetch.create_rpc()
            urlfetch.make_fetch_call(rpc, url)

    def get_result(self):
        if self.expanded is None:
            self.expanded = self.rpc.get_result().final_url
            memcache.set(self.key, self.expanded)
        return self.expanded


def expanded_url(url):
    "Expands the URL using the location header protocol. Returns the URL."
    try:
        key = urllib.quote_plus(
            urlparse.urlparse(url.encode('utf-8')).geturl())
    except KeyError:
        logging.error(u'Unable to parse {}'.format(url))
        raise
    expanded = memcache.get(key)
    if expanded is not None:
        logging.debug(
            u'URL expansion cache hit: {}'.format(url.encode('utf-8')))
    else:
        logging.debug(
            u'URL expansion cache miss: {}'.format(url.decode('utf-8')))
        try:
            result = urlfetch.fetch(
                url,
                follow_redirects=True,
                deadline=60  # Give it one minute until timeout.
            )
            if result.status_code == 200:
                expanded = result.final_url
                memcache.set(key, expanded)
            else:
                expanded = ''
        except InvalidURLError as e:
            logging.error(
                u'fetching {} resulted in {}'.format(url.encode('utf-8'), e))
            url = purl.scheme + '://' + purl.netloc + eu
        except (CertificateError,
                DeadlineExceededError,
                DownloadError,
                DNSLookupFailedError,
                ResponseTooLargeError,
                SSLCertificateError,
                UnicodeDecodeError) as e:
            logging.error(
                u'fetching {} resulted in {}'.format(url.encode('utf-8'), e))
            raise
    return expanded
