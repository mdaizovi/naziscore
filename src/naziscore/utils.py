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
    DNSLookupFailedError,
    DeadlineExceededError,
    DownloadError,
    InvalidURLError,
    ResponseTooLargeError,
    SSLCertificateError,
    TooManyRedirectsError,
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
    logging.info('Expanding ' + url)
    try:
        key = urllib.quote_plus(
            urlparse.urlparse(url.encode('utf-8')).geturl())
    except KeyError:
        logging.error(u'Unable to parse {}'.format(url))
        raise
    expanded = memcache.get(key)
    if expanded is not None:
        # logging.debug(
        #     u'URL expansion cache hit: {}'.format(url.encode('utf-8')))
        return expanded
    # logging.debug(u'URL expansion cache miss: {}'.format(url.encode('utf-8')))
    while True:
        try:
            eu = urlfetch.fetch(
                url.decode('utf-8'),  # Location came as a raw string
                follow_redirects=False,
                deadline = 60  # Give it one minute until timeout.
            ).headers.get('location', url.encode('utf-8'))
            purl = urlparse.urlparse(eu)
            if purl.scheme == '':  # It's relative (hopefully root-relative)
                logging.info(u'URL {} is relative'.format(url.encode('utf-8')))
                purl = urlparse.urlparse(url)
                expanded = purl.scheme + '://' + purl.netloc + eu
                memcache.set(key, expanded)
                return expanded
            if url == eu:
                memcache.set(key, url)  # We are stuck here
                return url
            else:
                url = eu  # Go for the next iteration
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
            # This is as far as we'll go expanding this URL, but since errors
            # can be transient, we won't cache this.
            memcache.set(key, url)
            logging.error(
                u'fetching {} resulted in {}'.format(url.encode('utf-8'), e))
            return url  # Return the last good one.
