from __future__ import unicode_literals
import datetime
import mock
import requests
import unittest
import scorched.connection


class TestConnection(unittest.TestCase):

    def _make_connection(self, url="http://localhost:8983/solr",
                         http_connection=None, mode="r", retry_timeout=-1,
                         max_length_get_url=2048):

        sc = scorched.connection.SolrConnection(
            url=url,
            http_connection=http_connection,
            mode=mode,
            retry_timeout=retry_timeout,
            max_length_get_url=max_length_get_url)

        return sc

    def test_readable(self):
        sc = self._make_connection()
        self.assertRaises(TypeError, sc.update, {})

    def test_writeable(self):
        sc = self._make_connection(mode="w")
        self.assertRaises(TypeError, sc.mlt, [])
        self.assertRaises(TypeError, sc.select, {})

    def test_mlt(self):
        sc = self._make_connection(mode="")
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [])
            # test content
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [],
                              content="fooo")
        # test post building
        sc = self._make_connection(max_length_get_url=0)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.mlt, [],
                              content="fooo")

    def test_select(self):
        sc = self._make_connection(max_length_get_url=0)
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.select, [])

    def test_no_body_response_error(self):
        sc = self._make_connection(mode="")
        with mock.patch.object(requests.Session, 'request',
                               return_value=mock.Mock(status_code=500)):
            self.assertRaises(scorched.exc.SolrError, sc.update, {"foo": 2})
            self.assertRaises(scorched.exc.SolrError, sc.update, {})

    def test_request(self):
        sc = self._make_connection(url="http://localhost:1234/none", mode="")
        self.assertRaises(Exception, sc.request, (), {})

    def test_url_for_update(self):
        dsn = "http://localhost:1234/none"
        sc = self._make_connection(url=dsn)
        ret = sc.url_for_update()

        def dsn_url(path):
            return "%s%s" % (dsn, path)

        self.assertEqual(ret, dsn_url("/update/json"))
        # commitwithin
        ret = sc.url_for_update(commitWithin=2)
        self.assertEqual(ret, dsn_url("/update/json?commitWithin=2"))
        self.assertRaises(ValueError, sc.url_for_update, commitWithin="a")
        self.assertRaises(ValueError, sc.url_for_update, commitWithin=-1)
        # softCommit
        ret = sc.url_for_update(softCommit=True)
        self.assertEqual(ret, dsn_url("/update/json?softCommit=true"))
        ret = sc.url_for_update(softCommit=False)
        self.assertEqual(ret, dsn_url("/update/json?softCommit=false"))
        # optimize
        ret = sc.url_for_update(optimize=True)
        self.assertEqual(ret, dsn_url("/update/json?optimize=true"))
        ret = sc.url_for_update(optimize=False)
        self.assertEqual(ret, dsn_url("/update/json?optimize=false"))
        # waitSearcher
        ret = sc.url_for_update(waitSearcher=True)
        self.assertEqual(ret, dsn_url("/update/json?waitSearcher=true"))
        ret = sc.url_for_update(waitSearcher=False)
        self.assertEqual(ret, dsn_url("/update/json?waitSearcher=false"))
        # expungeDeletes
        ret = sc.url_for_update(commit=True, expungeDeletes=True)
        self.assertEqual(
            ret, dsn_url("/update/json?commit=true&expungeDeletes=true"))
        ret = sc.url_for_update(commit=True, expungeDeletes=False)
        self.assertEqual(
            ret, dsn_url("/update/json?commit=true&expungeDeletes=false"))
        self.assertRaises(ValueError, sc.url_for_update, expungeDeletes=True)
        # maxSegments
        ret = sc.url_for_update(optimize=True, maxSegments=2)
        self.assertEqual(
            ret, dsn_url("/update/json?maxSegments=2&optimize=true"))
        self.assertRaises(
            ValueError, sc.url_for_update, optimize=True, maxSegments="a")
        self.assertRaises(
            ValueError, sc.url_for_update, optimize=True, maxSegments=-1)
        self.assertRaises(ValueError, sc.url_for_update, maxSegments=2)


class TestSolrInterface(unittest.TestCase):

    def _make_one(self):
        import scorched.connection
        import scorched.tests.schema
        with mock.patch('scorched.connection.SolrInterface.init_schema') as \
                init_schema:
            init_schema.return_value = scorched.tests.schema.schema
            si = scorched.connection.SolrInterface(
                'http://localhost:2222/mysolr')
        return si

    def test__prepare_docs_does_not_alter_given_docs(self):
        sc = self._make_one()
        today = datetime.datetime.utcnow()
        docs = [{'last_modified': today}]
        sc._prepare_docs(docs)
        self.assertEqual(docs, [{'last_modified': today}])

    def test__prepare_docs_converts_datetime(self):
        sc = self._make_one()
        dt = datetime.datetime(2014, 2, 18, 12, 12, 10)
        docs = [{'last_modified': dt}]
        result = sc._prepare_docs(docs)
        self.assertEqual(result[0]['last_modified'], "2014-02-18T12:12:10Z")
