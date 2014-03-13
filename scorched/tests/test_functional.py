import unittest
import os
import json
import scorched.testing
from scorched import SolrInterface


class TestUtils(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), "dumps",
                            "books.json")
        with open(file) as f:
            self.datajson = f.read()
            self.docs = json.loads(self.datajson)

    @scorched.testing.skip_unless_solr
    def test_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(genre_s="fantasy").execute()
        self.assertEqual(res.result.numFound, 3)
        si.delete_all()

    @scorched.testing.skip_unless_solr
    def test_facet_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(genre_s="fantasy").facet_by("cat").execute()
        self.assertEqual(res.result.numFound, 3)
        self.assertEqual([x['name'] for x in res.result.docs],
                         [u'The Lightning Thief',
                          u'The Sea of Monsters',
                          u"Sophie's World : The Greek Philosophers"])
        self.assertEqual(res.facet_counts.__dict__,
                         {'facet_fields': {u'cat': [(u'book', 3),
                                                    (u'paperback', 2),
                                                    (u'hardcover', 1)]},
                          'facet_dates': {},
                          'facet_queries': {},
                          'facet_pivot': ()})
        si.delete_all()

    @scorched.testing.skip_unless_solr
    def test_filter_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(si.Q(**{"*": "*"})).filter(cat="hardcover").filter(
            genre_s="fantasy").execute()
        self.assertEqual(res.result.numFound, 1)
        self.assertEqual([x['name'] for x in res.result.docs],
                         [u'The Lightning Thief'])
        si.delete_all()

    @scorched.testing.skip_unless_solr
    def test_edismax_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(si.Q(**{"*": "*"})).filter(cat="hardcover").filter(
            genre_s="fantasy").alt_parser('edismax').execute()
        self.assertEqual(res.result.numFound, 1)
        self.assertEqual([x['name'] for x in res.result.docs],
                         [u'The Lightning Thief'])
        si.delete_all()
