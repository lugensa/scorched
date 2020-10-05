from __future__ import unicode_literals
import datetime
import pytz
import unittest
import os.path
import scorched.response


class ResultsTestCase(unittest.TestCase):

    def setUp(self):
        file_path = os.path.join(os.path.dirname(__file__), "dumps",
                                 "request_w_facets.json")
        with open(file_path) as f:
            self.data = f.read()
        # termVector data
        file_path = os.path.join(os.path.dirname(__file__), "dumps",
                                 "request_w_termvector.json")
        with open(file_path) as f:
            self.data_tv = f.read()
        # error data
        file_path = os.path.join(os.path.dirname(__file__), "dumps",
                                 "request_error.json")
        with open(file_path) as f:
            self.data_error = f.read()

        file_path = os.path.join(os.path.dirname(__file__), "dumps",
                                 "request_hl.json")
        with open(file_path) as f:
            self.data_hl = f.read()

        file_path = os.path.join(os.path.dirname(__file__), "dumps",
                                 "request_hl_grouped.json")
        with open(file_path) as f:
            self.data_hl_grouped = f.read()

    def test_response(self):
        res = scorched.response.SolrResponse.from_json(
            self.data, 'id', datefields=('*_dt', 'modified'))
        self.assertEqual(res.status, 0)
        self.assertEqual(res.QTime, 1)
        self.assertEqual(res.result.numFound, 3)
        # iterable
        self.assertEqual([x['name'] for x in res],
                         [u'The Lightning Thief',
                          u'The Sea of Monsters',
                          u"Sophie's World : The Greek Philosophers"])
        self.assertEqual([x['name'] for x in res.result.docs],
                         [u'The Lightning Thief',
                          u'The Sea of Monsters',
                          u"Sophie's World : The Greek Philosophers"])
        self.assertEqual([x['created_dt'] for x in res.result.docs if 'created_dt' in x],
                         [datetime.datetime(2009, 7, 23, 3, 24, 34, 376,
                                            tzinfo=pytz.utc)])
        self.assertEqual([x['modified'] for x in res.result.docs if 'modified' in x],
                         [datetime.datetime(2009, 7, 23, 3, 24, 34, 376,
                                            tzinfo=pytz.utc)])
        self.assertEqual(res.facet_counts.__dict__,
                         {'facet_fields': {u'cat': [(u'book', 3),
                                                    (u'paperback', 2),
                                                    (u'hardcover', 1)]},
                          'facet_dates': {},
                          'facet_queries': {},
                          'facet_ranges': {
                            u'created_dt': {
                              u'gap': u'+1YEARS',
                              u'start': u'2009-01-01T00:00:00Z',
                              u'end': u'2012-01-01T00:00:00Z',
                              u'counts': [
                                (u'2009-01-01T00:00:00Z',1),
                                (u'2010-01-01T00:00:00Z',0),
                                (u'2011-01-01T00:00:00Z',0),
                              ]
                            },
                          },
                          'facet_pivot': ()})

        self.assertRaises(ValueError, res.from_json, self.data_error, 'id')
        self.assertEqual(res.__str__(), u'3 results found, starting at #0')
        self.assertEqual(len(res), 3)

    def test_term_vectors(self):
        res_tv = scorched.response.SolrResponse.from_json(
            self.data_tv, 'id', datefields=('date',))
        self.assertEqual(res_tv.term_vectors["uniqueKeyFieldName"], "uid")
        self.assertEqual(res_tv.term_vectors["warnings"],
                         {"noTermVectors": ["title"]})
        self.assertEqual(res_tv.term_vectors["ffaa9370-5182-5810-b8a9-54b751ef0606"]["uniqueKey"],
                         "ffaa9370-5182-5810-b8a9-54b751ef0606")
        self.assertEqual(res_tv.term_vectors["ffaa9370-5182-5810-b8a9-54b751ef0606"]["weighted_words"]["wirken"],
                         {"tf": 1, "df": 106})
        self.assertEqual(res_tv.term_vectors["9ce8ef2d-6e0f-5647-ae4c-2aaaca37b28f"]["weighted_words"]["anlagen"],
                         {"tf": 3, "df": 21484})

    def test_highlighting(self):
        res_hl = scorched.response.SolrResponse.from_json(
            self.data_hl, 'id')
        highlights = {u'author': [u'<em>John</em> Muir']}
        self.assertEqual(res_hl.highlighting['978'], highlights)
        self.assertEqual(res_hl.result.docs[0]['solr_highlights'], highlights)

    def test_highlighting_with_grouping(self):
        res_hl_group = scorched.response.SolrResponse.from_json(
            self.data_hl_grouped, 'id', datefields=('important_dts',))
        self.assertEqual(res_hl_group.group_field, 'inStock')
        self.assertEqual(getattr(res_hl_group.groups, res_hl_group.group_field)['matches'], 2)
        ngroups = getattr(res_hl_group.groups, res_hl_group.group_field)['ngroups']
        self.assertEqual(ngroups, 1)

        groups = getattr(res_hl_group.groups, res_hl_group.group_field)['groups']
        self.assertEqual(len(groups), ngroups)

        highlights = {u'author': [u'John <em>Muir</em>']}
        self.assertEqual(groups[0]['doclist']['docs'][0]['solr_highlights'],
                         highlights)
        self.assertEqual(type(groups[0]['doclist']['docs'][0]['important_dts'][0]),
                         datetime.datetime)



