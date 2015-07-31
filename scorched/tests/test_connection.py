from __future__ import unicode_literals
import json
import os
import mock
import requests
import unittest
import scorched.connection

HTTPBIN = os.environ.get('HTTPBIN_URL', 'http://httpbin.org/')
# Issue #1483: Make sure the URL always has a trailing slash
HTTPBIN = HTTPBIN.rstrip('/') + '/'


def httpbin(*suffix):
    """Returns url for HTTPBIN resource."""
    return requests.compat.urljoin(HTTPBIN, '/'.join(suffix))


class TestConnection(unittest.TestCase):

    def test_readable(self):
        dsn = "http://localhost:8983/solr"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="r", retry_timeout=-1,
            max_length_get_url=2048)
        self.assertRaises(TypeError, sc.update, {})

    def test_writeable(self):
        dsn = "http://localhost:8983/solr"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="w", retry_timeout=-1,
            max_length_get_url=2048)
        self.assertRaises(TypeError, sc.mlt, [])
        self.assertRaises(TypeError, sc.select, {})

    def test_mlt(self):
        dsn = "http://localhost:8983/solr"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=2048)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [])
            # test content
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [],
                              content="fooo")
        # test post building
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=0)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [],
                              content="fooo")

    def test_select(self):
        dsn = "http://localhost:8983/solr"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=0)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.select, [])

    def test_no_body_response_error(self):
        dsn = "http://localhost:8983/solr"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=2048)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.update, {"foo": 2})
            self.assertRaises(scorched.exc.SolrError, sc.update, {})

    def test_request(self):
        dsn = "http://localhost:1234/none"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=2048)
        self.assertRaises(Exception, sc.request, (), {})

    def test_url_for_update(self):
        dsn = "http://localhost:1234/none"
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=2048)
        ret = sc.url_for_update()
        self.assertEqual(ret, "http://localhost:1234/none/update/json")
        # commitwithin
        ret = sc.url_for_update(commitWithin=2)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?commitWithin=2")
        self.assertRaises(ValueError, sc.url_for_update, commitWithin="a")
        self.assertRaises(ValueError, sc.url_for_update, commitWithin=-1)
        # softCommit
        ret = sc.url_for_update(softCommit=True)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?softCommit=true")
        ret = sc.url_for_update(softCommit=False)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?softCommit=false")
        # optimize
        ret = sc.url_for_update(optimize=True)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?optimize=true")
        ret = sc.url_for_update(optimize=False)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?optimize=false")
        # waitSearcher
        ret = sc.url_for_update(waitSearcher=True)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?waitSearcher=true")
        ret = sc.url_for_update(waitSearcher=False)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?waitSearcher=false")
        # expungeDeletes
        ret = sc.url_for_update(commit=True, expungeDeletes=True)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?commit=true&expungeDeletes=true")
        ret = sc.url_for_update(commit=True, expungeDeletes=False)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?commit=true&expungeDeletes=false")
        self.assertRaises(ValueError, sc.url_for_update, expungeDeletes=True)
        # maxSegments
        ret = sc.url_for_update(optimize=True, maxSegments=2)
        self.assertEqual(
            ret, "http://localhost:1234/none/update/json?maxSegments=2&optimize=true")
        self.assertRaises(ValueError, sc.url_for_update, optimize=True, maxSegments="a")
        self.assertRaises(ValueError, sc.url_for_update, optimize=True, maxSegments=-1)
        self.assertRaises(ValueError, sc.url_for_update, maxSegments=2)

    def test_select_timeout(self):
        dsn = "http://localhost:1234/none"
        # max_length_get_url=99999: httbin doesn't support POST
        sc = scorched.connection.SolrConnection(
            url=dsn, http_connection=None, mode="", retry_timeout=-1,
            max_length_get_url=99999, search_timeout=3.0)
        sc.select_url = httpbin('delay/2')
        # delay 2.0s < 3.0s timeout, ok
        resp = sc.select([])
        self.assertTrue(json.loads(resp)['url'].startswith(sc.select_url))
        # delay 2.0s > 1.0s timeout, raise ReadTimeout
        sc.search_timeout = 1.0
        self.assertRaises(requests.exceptions.ReadTimeout, sc.select, [])
        sc.search_timeout = (5.0, 1.0)  # (connect, read)
        self.assertRaises(requests.exceptions.ReadTimeout, sc.select, [])
        # delay 2.0s < 3.0s timeout, ok
        sc.search_timeout = (1.0, 3.0)  # (connect, read)
        resp = sc.select([])
        self.assertTrue(json.loads(resp)['url'].startswith(sc.select_url))
        # Connecting to an invalid port should raise a ConnectionError
        sc.select_url = "http://httpbin.org:1/none/select"
        sc.search_timeout = 1.0
        self.assertRaises(requests.exceptions.ConnectTimeout, sc.select, [])
        sc.search_timeout = (1.0, 5.0)
        self.assertRaises(requests.exceptions.ConnectTimeout, sc.select, [])
