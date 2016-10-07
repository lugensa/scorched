from __future__ import unicode_literals
import collections
import json
import scorched.dates

from scorched.compat import str


class SolrFacetCounts(object):
    members = (
        "facet_dates",
        "facet_fields",
        "facet_queries",
        "facet_ranges",
        "facet_pivot"
    )

    def __init__(self, **kwargs):
        for member in self.members:
            setattr(self, member, kwargs.get(member, ()))
        self.facet_fields = dict(self.facet_fields)

    @classmethod
    def from_json(cls, response):
        try:
            facet_counts = response['facet_counts']
        except KeyError:
            return SolrFacetCounts()
        facet_fields = {}
        for facet_field, facet_values in list(facet_counts[
                'facet_fields'].items()):
            facets = []
            # Change each facet list from [a, 1, b, 2, c, 3 ...] to
            # [(a, 1), (b, 2), (c, 3) ...]
            for n, value in enumerate(facet_values):
                if n & 1 == 0:
                    name = value
                else:
                    facets.append((name, value))
            facet_fields[facet_field] = facets
        facet_counts['facet_fields'] = facet_fields
        for facet_field in list(facet_counts['facet_ranges'].keys()):
            counts = []
            count_list = facet_counts['facet_ranges'][facet_field]['counts']
            # Change each facet list from [a, 1, b, 2, c, 3 ...] to
            # [(a, 1), (b, 2), (c, 3) ...]
            for n, value in enumerate(count_list):
                if n & 1 == 0:
                    name = value
                else:
                    counts.append((name, value))
            facet_counts['facet_ranges'][facet_field]['counts'] = counts
        return SolrFacetCounts(**facet_counts)


class SolrStats(object):
    members = (
        "stats_fields",
        "facet",
    )

    def __init__(self, **kwargs):
        for member in self.members:
            setattr(self, member, kwargs.get(member, ()))
        self.stats_fields = dict(self.stats_fields)

    @classmethod
    def from_json(cls, response):
        try:
            stats_response = response['stats']
        except KeyError:
            return SolrStats()
        stats = {'stats_fields': {}}
        # faceted stats, if present, are included within the field
        for field, values in list(stats_response['stats_fields'].items()):
            stats['stats_fields'][field] = values

        return SolrStats(**stats)


class SolrUpdateResponse(object):
    @classmethod
    def from_json(cls, jsonmsg):
        self = cls()
        self.original_json = jsonmsg
        doc = json.loads(jsonmsg)
        details = doc['responseHeader']
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details.get(attr))
        if self.status != 0:
            raise ValueError("Response indicates an error")
        return self


class SolrResponse(collections.Sequence):

    @classmethod
    def from_json(cls, jsonmsg, datefields=()):
        self = cls()
        self.original_json = jsonmsg
        doc = json.loads(jsonmsg)
        details = doc['responseHeader']
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details.get(attr))
        # should this be a SolrResult attr ??
        if doc.get('nextCursorMark'):
            self.nextcursormark = doc.get('nextCursorMark')
        if self.status != 0:
            raise ValueError("Response indicates an error")
        self.result = SolrResult()
        if doc.get('response'):
            self.result = SolrResult.from_json(doc['response'], datefields)
        # TODO mlt/ returns match what should we do with it ?
        # if doc.get('match'):
        #    self.result = SolrResult.from_json(doc['match'], datefields)
        self.facet_counts = SolrFacetCounts.from_json(doc)
        self.highlighting = doc.get("highlighting", {})
        self.spellcheck = doc.get("spellcheck", {})
        self.groups = doc.get('grouped', {})
        self.debug = doc.get('debug', {})
        self.next_cursor_mark = doc.get('nextCursorMark')
        self.more_like_these = dict(
            (k, SolrResult.from_json(v, datefields))
            for (k, v) in list(doc.get('moreLikeThis', {}).items()))
        self.term_vectors = self.parse_term_vectors(doc.get('termVectors', []))
        # can be computed by MoreLikeThisHandler
        self.interesting_terms = doc.get('interestingTerms', None)
        self.stats = SolrStats.from_json(doc)
        return self

    @classmethod
    def from_get_json(cls, jsonmsg, datefields=()):
        """Generate instance from the response of a RealTime Get"""
        self = cls()
        self.original_json = jsonmsg
        doc = json.loads(jsonmsg)
        self.result = SolrResult.from_json(doc['response'], datefields)
        return self

    @classmethod
    def parse_term_vectors(cls, lst, path=""):
        """Transform a solr list to dict

        Turns [a, x, b, y, c, z ...] into {a: x, b: y, c: z ...}
        If the values are lists themselves, this is done recursively
        """
        dct = dict()
        for i in range(0, len(lst), 2):
            k = lst[i]
            v = lst[i+1]
            # Do not recurse too deep into warnings list
            if path != ".warnings" and isinstance(v, list):
                v = cls.parse_term_vectors(v, path + "." + k)
            dct[k] = v
        return dct

    def __str__(self):
        return str(self.result)

    def __len__(self):
        return len(self.result.docs)

    def __getitem__(self, key):
        return self.result.docs[key]
    
    def __iter__(self):
#        print("in Solrresponse#iter")
        nret = 0
        srch = self.origsearch
        
        while True:
            i = 0
            l = len(self)
        
            while i < l and nret  < srch.paginator.userrows:
                v = self[i]
                yield v
                i += 1
                nret += 1
                if nret >= srch.paginator.userrows:
                    return
            
        # end buffer, see if we need to get more
        
            if hasattr(self, "nextcursormark"):
#                print("endbuf: nextcursor:"+ self.nextcursormark + " prev curs:" +
#                      self.params['cursorMark'])
                if(self.nextcursormark == self.params['cursorMark']):
#                    print("completed iteration")
                    return
                else:
#                    print("go pull next buffer")
                    srch.paginator.update(None,None, True, None, self.nextcursormark)
                    newres = srch.execute()
                    self = newres
                    continue
            #else:
#                print("no cursormark")
            return
    

class SolrResult(object):

    @classmethod
    def from_json(cls, node, datefields=()):
        self = cls()
        self.name = 'response'
        self.numFound = int(node['numFound'])
        self.start = int(node['start'])
        docs = node['docs']
        self.docs = self._prepare_docs(docs, datefields)
        return self

    def _prepare_docs(self, docs, datefields):
        for doc in docs:
            for name, value in list(doc.items()):
                if scorched.dates.is_datetime_field(name, datefields):
                    doc[name] = scorched.dates.solr_date(value)._dt_obj
        return docs

    def __str__(self):
        return "{numFound} results found, starting at #{start}".format(
            numFound=self.numFound, start=self.start)
