from __future__ import unicode_literals
import itertools
import json
import requests
import scorched.dates
import scorched.response
import scorched.search
import scorched.exc
import scorched.compat
import time
import warnings

from scorched.compat import str

MAX_LENGTH_GET_URL = 2048
# Jetty default is 4096; Tomcat default is 8192; picking 2048 to be
# conservative.


def is_iter(val):
    return isinstance(val, (tuple, list))


class SolrConnection(object):
    readable = True
    writeable = True

    def __init__(self, url, http_connection, mode, retry_timeout,
                 max_length_get_url, search_timeout=()):
        """
        :param url: url to Solr
        :type url: str
        :param http_connection: already existing connection TODO
        :type http_connection: requests connection
        :param mode: mode (readable, writable) Solr
        :type mode: str
        :param retry_timeout: timeout until retry
        :type retry_timeout: int
        :param max_length_get_url: max length until switch to post
        :type max_length_get_url: int
        :param search_timeout: (optional) How long to wait for the server to
                               send data before giving up, as a float, or a
                               (connect timeout, read timeout) tuple.
        :type search_timeout: float or tuple
        """
        self.http_connection = requests.Session()
        if mode == 'r':
            self.writeable = False
        elif mode == 'w':
            self.readable = False
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/json"
        self.select_url = self.url + "select/"
        self.mlt_url = self.url + "mlt/"
        self.get_url = self.url + "get/"
        self.retry_timeout = retry_timeout
        self.max_length_get_url = max_length_get_url
        self.search_timeout = search_timeout

    def request(self, *args, **kwargs):
        """
        :param args: arguments
        :type args: tuple
        :param kwargs: key word arguments
        :type kwargs: dict

        .. todo::
            Make this api more explicit!
        """
        try:
            return self.http_connection.request(*args, **kwargs)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            if self.retry_timeout < 0:
                raise
            time.sleep(self.retry_timeout)
            return self.http_connection.request(*args, **kwargs)

    def get(self, ids, fl=None):
        """
        Perform a RealTime Get
        """
        # We always send the ids parameter to force the standart output format,
        # but use the id parameter for our actual data as `ids` can no handle
        # ids with commas
        params = [
            ("ids", ""),
            ("wt", "json"),
        ]
        if is_iter(ids):
            for id in ids:
                params.append(("id", id))
        else:
            params.append(("id", ids))
        if fl:
            params.append(("fl", ",".join(fl)))

        qs = scorched.compat.urlencode(params)
        url = "%s?%s" % (self.get_url, qs)

        response = self.request("GET", url)
        if response.status_code != 200:
            raise scorched.exc.SolrError(response)
        return response.text

    def update(self, update_doc, **kwargs):
        """
        :param update_doc: data send to Solr
        :type update_doc: json data
        :returns: json -- json string

        Send json to Solr
        """
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        body = update_doc
        if body:
            headers = {"Content-Type": "application/json; charset=utf-8"}
        else:
            headers = {}
        url = self.url_for_update(**kwargs)
        response = self.request('POST', url, data=body, headers=headers)
        if response.status_code != 200:
            raise scorched.exc.SolrError(response)
        return response.text

    def url_for_update(self, commit=None, commitWithin=None, softCommit=None,
                       optimize=None, waitSearcher=None, expungeDeletes=None,
                       maxSegments=None):
        """
        :param commit: optional -- commit actions
        :type commit: bool
        :param commitWithin: optional -- document will be added within that
                             time
        :type commitWithin: int
        :param softCommit: optional -- performant commit without "on-disk"
                           guarantee
        :type softCommit: bool
        :param optimize: optional -- optimize forces all of the index segments
                         to be merged into a single segment first.
        :type optimze: bool
        :param waitSearcher: optional -- block until a new searcher is opened
                             and registered as the main query searcher,
        :type waitSearcher: bool
        :param expungeDeletes: optional -- merge segments with deletes away
        :type expungeDeletes: bool
        :param maxSegments: optional -- optimizes down to at most this number
                            of segments
        :type maxSegments: int
        :returns: str -- url with all extra paramters set

        This functions sets all extra parameters for the ``optimize`` and
        ``commit`` function.
        """
        extra_params = {}
        if commit is not None:
            extra_params['commit'] = "true" if commit else "false"
        if commitWithin is not None:
            try:
                extra_params['commitWithin'] = int(commitWithin)
            except (TypeError, ValueError):
                raise ValueError(
                    "commitWithin should be a number in milliseconds")
            if extra_params['commitWithin'] < 0:
                raise ValueError(
                    "commitWithin should be a number in milliseconds")
            extra_params['commitWithin'] = str(extra_params['commitWithin'])
        if softCommit is not None:
            extra_params['softCommit'] = "true" if softCommit else "false"
        if optimize is not None:
            extra_params['optimize'] = "true" if optimize else "false"
        if waitSearcher is not None:
            extra_params['waitSearcher'] = "true" if waitSearcher else "false"
        if expungeDeletes is not None:
            extra_params[
                'expungeDeletes'] = "true" if expungeDeletes else "false"
        if maxSegments is not None:
            try:
                extra_params['maxSegments'] = int(maxSegments)
            except (TypeError, ValueError):
                raise ValueError("maxSegments")
            if extra_params['maxSegments'] <= 0:
                raise ValueError("maxSegments should be a positive number")
            extra_params['maxSegments'] = str(extra_params['maxSegments'])
        if 'expungeDeletes' in extra_params and 'commit' not in extra_params:
            raise ValueError("Can't do expungeDeletes without commit")
        if 'maxSegments' in extra_params and 'optimize' not in extra_params:
            raise ValueError("Can't do maxSegments without optimize")
        if extra_params:
            return "%s?%s" % (self.update_url, scorched.compat.urlencode(
                sorted(extra_params.items())))
        else:
            return self.update_url

    def select(self, params):
        """
        :param params: LuceneQuery converted to a dictionary with search
                       queries
        :type params: dict
        :returns: json -- json string

        We perform here a search on the `select` handler of Solr.
        """
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        params.append(('wt', 'json'))
        qs = scorched.compat.urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        if len(url) > self.max_length_get_url:
            warnings.warn(
                "Long query URL encountered - POSTing instead of "
                "GETting. This query will not be cached at the HTTP layer")
            url = self.select_url
            method = 'POST'
            kwargs = {
                'data': qs,
                'headers': {
                    "Content-Type": "application/x-www-form-urlencoded"}}
        else:
            method = 'GET'
            kwargs = {}
        if self.search_timeout != ():
            kwargs['timeout'] = self.search_timeout
        response = self.request(method, url, **kwargs)
        if response.status_code != 200:
            raise scorched.exc.SolrError(response)
        return response.text

    def mlt(self, params, content=None):
        """
        :param params: LuceneQuery converted to a dictionary with search
                       queries
        :type params: dict
        :returns: json -- json string

        Perform a MoreLikeThis query using the content specified
        There may be no content if stream.url is specified in the params.
        """
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        params.append(('wt', 'json'))
        qs = scorched.compat.urlencode(params)
        base_url = "%s?%s" % (self.mlt_url, qs)
        method = 'GET'
        kwargs = {}
        if content is None:
            url = base_url
        else:
            get_url = "%s&stream.body=%s" % (
                base_url, scorched.compat.quote_plus(content))
            if len(get_url) <= self.max_length_get_url:
                url = get_url
            else:
                url = base_url
                method = 'POST'
                kwargs = {
                    'data': content,
                    'headers': {"Content-Type": "text/plain; charset=utf-8"}}
        response = self.request(method, url, **kwargs)
        if response.status_code != 200:
            raise scorched.exc.SolrError(response.content)
        return response.text


class SolrInterface(object):
    remote_schema_file = "schema?wt=json"

    def __init__(self, url, http_connection=None, mode='',
                 retry_timeout=-1, max_length_get_url=MAX_LENGTH_GET_URL,
                 search_timeout=()):
        """
        :param url: url to Solr
        :type url: str
        :param http_connection: optional -- already existing connection TODO
        :type http_connection: requests connection
        :param mode: optional -- mode (readable, writable) Solr
        :type mode: str
        :param retry_timeout: optional -- timeout until retry
        :type retry_timeout: int
        :param max_length_get_url: optional -- max length until switch to post
        :type max_length_get_url: int
        :param search_timeout: (optional) How long to wait for the server to
                               send data before giving up, as a float, or a
                               (connect timeout, read timeout) tuple.
        :type search_timeout: float or tuple
        """

        self.conn = SolrConnection(
            url, http_connection, mode, retry_timeout, max_length_get_url)
        self.schema = self.init_schema()
        self._datefields = self._extract_datefields(self.schema)

    def init_schema(self):
        response = self.conn.request(
            'GET', scorched.compat.urljoin(self.conn.url,
                                           self.remote_schema_file))
        if response.status_code != 200:
            raise EnvironmentError(
                "Couldn't retrieve schema document - status code %s\n%s" % (
                    response.status_code, response.content)
            )
        return response.json()['schema']

    def _extract_datefields(self, schema):
        ret = [x['name'] for x in
               schema['fields'] if x['type'] == 'date']
        ret.extend([x['name'] for x in schema['dynamicFields']
                    if x['type'] == 'date'])
        return ret

    def _prepare_docs(self, docs):
        prepared_docs = []
        for doc in docs:
            new_doc = {}
            for name, value in list(doc.items()):
                # XXX remove all None fields this is needed for adding date
                # fields
                if value is None:
                    continue
                if scorched.dates.is_datetime_field(name, self._datefields):
                    if is_iter(value):
                        value = [str(scorched.dates.solr_date(v)) for v in
                                 value]
                    else:
                        value = str(scorched.dates.solr_date(value))
                new_doc[name] = value
            prepared_docs.append(new_doc)
        return prepared_docs

    def add(self, docs, chunk=100, **kwargs):
        """
        :param docs: documents to be added
        :type docs: dict
        :param chunk: optional -- size of chunks in which the add command
        should be split
        :type chunk: int
        :param kwargs: optinal -- additional arguments
        :type kwargs: dict
        :returns: list of SolrUpdateResponse  -- A Solr response object.

        Add a document or a list of document to Solr.
        """
        if hasattr(docs, "items") or not is_iter(docs):
            docs = [docs]
        # to avoid making messages too large, we break the message every
        # chunk docs.
        ret = []
        for doc_chunk in grouper(docs, chunk):
            update_message = json.dumps(self._prepare_docs(doc_chunk))
            ret.append(scorched.response.SolrUpdateResponse.from_json(
                self.conn.update(update_message, **kwargs)))
        return ret

    def delete_by_query(self, query, **kwargs):
        """
        :param query: criteria how witch entries should be deleted
        :type query: LuceneQuery
        :returns: SolrUpdateResponse  -- A Solr response object.

        Delete entries by a given query
        """
        delete_message = json.dumps({"delete": {"query": str(query)}})
        ret = scorched.response.SolrUpdateResponse.from_json(
            self.conn.update(delete_message, **kwargs))
        return ret

    def delete_by_ids(self, ids, **kwargs):
        """
        :param ids: ids of entries that should be deleted
        :type ids: list
        :returns: SolrUpdateResponse  -- A Solr response object.

        Delete entries by a given id
        """
        delete_message = json.dumps({"delete": ids})
        ret = scorched.response.SolrUpdateResponse.from_json(
            self.conn.update(delete_message, **kwargs))
        return ret

    def commit(self, waitSearcher=None, expungeDeletes=None, softCommit=None):
        """
        :param waitSearcher: optional -- block until a new searcher is opened
                             and registered as the main query searcher, making
                             the changes visible
        :type waitSearcher: bool
        :param expungeDeletes: optional -- merge segments with deletes away
        :type expungeDeletes: bool
        :param softCommit: optional -- perform a soft commit - this will
                           refresh the 'view' of the index in a more performant
                           manner, but without "on-disk" guarantees.
        :type softCommit: bool
        :returns: SolrUpdateResponse  -- A Solr response object.

        A commit operation makes index changes visible to new search requests.
        """
        ret = scorched.response.SolrUpdateResponse.from_json(
            self.conn.update('{"commit": {}}', commit=True,
                             waitSearcher=waitSearcher,
                             expungeDeletes=expungeDeletes,
                             softCommit=softCommit))
        return ret

    def optimize(self, waitSearcher=None, maxSegments=None):
        """
        :param waitSearcher: optional -- block until a new searcher is opened
                             and registered as the main query searcher, making
                             the changes visible
        :type waitSearcher: bool
        :param maxSegments: optional -- optimizes down to at most this number
                            of segments
        :type maxSegments: int
        :returns: SolrUpdateResponse  -- A Solr response object.

        An optimize is like a hard commit except that it forces all of the
        index segments to be merged into a single segment first.
        """
        ret = scorched.response.SolrUpdateResponse.from_json(
            self.conn.update('{"optimize": {}}', optimize=True,
                             waitSearcher=waitSearcher,
                             maxSegments=maxSegments))
        return ret

    def rollback(self):
        """
        :returns: SolrUpdateResponse  -- A Solr response object.

        The rollback command rollbacks all add/deletes made to the index since
        the last commit
        """
        ret = scorched.response.SolrUpdateResponse.from_json(
            self.conn.update('{"rollback": {}}'))
        return ret

    def delete_all(self):
        """
        :returns: SolrUpdateResponse  -- A Solr response object.

        Delete everything
        """
        return self.delete_by_query(self.Q(**{"*": "*"}))

    def get(self, ids, fields=None):
        """
        RealTime Get document(s) by id(s)

        :param ids: id(s) of the document(s)
        :type ids: list, string or int
        :param fields: optional -- list of fields to return
        :type fileds: list of strings
        """
        ret = scorched.response.SolrResponse.from_get_json(
            self.conn.get(ids, fields), self._datefields)
        return ret

    def search(self, **kwargs):
        """
        :returns: SolrResponse  -- A Solr response object.

        Search solr
        """
        params = scorched.search.params_from_dict(**kwargs)
        ret = scorched.response.SolrResponse.from_json(
            self.conn.select(params),
            self.schema['uniqueKey'],
            self._datefields,
        )
        return ret

    def query(self, *args, **kwargs):
        """
        :returns: SolrSearch -- A solrsearch.

        Build a Solr query
        """
        q = scorched.search.SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q

    def mlt_search(self, content=None, **kwargs):
        """
        :returns: SolrResponse  -- A Solr response object.

        More like this search Solr
        """
        params = scorched.search.params_from_dict(**kwargs)
        ret = scorched.response.SolrResponse.from_json(
            self.conn.mlt(params, content=content),
            self.schema['uniqueKey'],
            self._datefields,
        )
        return ret

    def mlt_query(self, fields, content=None, content_charset=None,
                  url=None, query_fields=None, **kwargs):
        """
        :param fields: field names to compute similarity upon
        :type fields: list
        :param content: optional -- string on witch to find similar documents
        :type content: str
        :param content_charset: optional -- charset e.g. (iso-8859-1)
        :type content_charset: str
        :param url: optional -- like content but retrive directly from url
        :type url: str
        :param query_fields: optional -- adjust boosting values for ``fields``
        :type query_fields: dict  e.g. ({"a": 0.25, "b": 0.75})
        :returns: MltSolrSearch

        Perform a similarity query on MoreLikeThisHandler

        The MoreLikeThisHandler is expected to be registered at the '/mlt'
        endpoint in the solrconfig.xml file of the server.

        Other MoreLikeThis specific parameters can be passed as kwargs without
        the 'mlt.' prefix.
        """
        q = scorched.search.MltSolrSearch(
            self, content=content, content_charset=content_charset, url=url)
        return q.mlt(fields=fields, query_fields=query_fields, **kwargs)

    def Q(self, *args, **kwargs):
        q = scorched.search.LuceneQuery()
        q.add(args, kwargs)
        return q


def grouper(iterable, n):
    """
    grouper('ABCDEFG', 3) --> [['ABC'], ['DEF'], ['G']]
    """
    i = iter(iterable)
    g = list(itertools.islice(i, 0, n))
    while g:
        yield g
        g = list(itertools.islice(i, 0, n))
