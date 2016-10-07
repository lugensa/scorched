from __future__ import unicode_literals
import collections
import json
import scorched.dates

from scorched.compat import str
from scorched.search import is_iter


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
    def from_json(cls, jsonmsg, unique_key, datefields=()):
        self = cls()
        self.original_json = jsonmsg
        doc = json.loads(jsonmsg)
        details = doc['responseHeader']
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details.get(attr))
        if self.status != 0:
            raise ValueError("Response indicates an error")
        self.result = SolrResult()
        if doc.get('response'):
            self.result = SolrResult.from_json(doc['response'], datefields)
        # TODO mlt/ returns match what should we do with it ?
        # if doc.get('match'):
        #    self.result = SolrResult.from_json(doc['match'], datefields)
        self.facet_counts = SolrFacetCounts.from_json(doc)
        self.spellcheck = doc.get("spellcheck", {})
        if self.params is not None:
            self.group_field = self.params.get('group.field')
        else:
            self.group_field = None
        self.groups = {}
        if self.group_field is not None:
            self.groups = SolrGroupResult.from_json(
                doc['grouped'], self.group_field, datefields)
        self.highlighting = doc.get("highlighting", {})
        if self.highlighting:
            # Add highlighting info to the individual documents.
            if doc.get('response'):
                for d in self.result.docs:
                    k = str(d[unique_key])
                    if k in self.highlighting:
                        d['solr_highlights'] = self.highlighting[k]
            elif doc.get('grouped'):
                for group in getattr(self.groups, self.group_field)['groups']:
                    for d in group['doclist']['docs']:
                        k = str(d[unique_key])
                        if k in self.highlighting:
                            d['solr_highlights'] = self.highlighting[k]

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
        self.groups = {}
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
        if self.groups:
            return len(getattr(self.groups, self.group_field)['groups'])
        else:
            return len(self.result.docs)

    def __getitem__(self, key):
        if self.groups:
            return getattr(self.groups, self.group_field)['groups'][key]
        else:
            return self.result.docs[key]


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

    @staticmethod
    def _prepare_docs(docs, datefields):
        for doc in docs:
            for name, value in list(doc.items()):
                if scorched.dates.is_datetime_field(name, datefields):
                    if is_iter(value):
                        doc[name] = [scorched.dates.solr_date(v)._dt_obj for
                                     v in value]
                    else:
                        doc[name] = scorched.dates.solr_date(value)._dt_obj
        return docs

    def __str__(self):
        return "{numFound} results found, starting at #{start}".format(
            numFound=self.numFound, start=self.start)


class SolrGroupResult(object):

    @classmethod
    def from_json(cls, node, group_field, datefields=()):
        self = cls()
        self.name = 'response'
        self.group_field = group_field
        groups = node[group_field]['groups']
        setattr(self, group_field, {
            'matches': node[group_field]['matches'],
            'ngroups': node[group_field]['ngroups'],
            'groups': self._prepare_groups(groups, datefields),
        })
        return self

    @staticmethod
    def _prepare_groups(groups, datefields):
        """Iterate over the docs and the groups and cast fields appropriately"""
        for group in groups:
            for doc in group['doclist']['docs']:
                for name, value in doc.items():
                    if scorched.dates.is_datetime_field(name, datefields):
                        if is_iter(value):
                            doc[name] = [scorched.dates.solr_date(v)._dt_obj for
                                         v in value]
                        else:
                            doc[name] = scorched.dates.solr_date(value)._dt_obj
        return groups

    def __str__(self):
        return "{ngroups} groups with {matches} matches found".format(
            ngroups=getattr(self, self.group_field)['ngroups'],
            matches=getattr(self, self.group_field)['matches'],
        )
