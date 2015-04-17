# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import unittest
import os
import json
import scorched.testing
from scorched import SolrInterface


class Book:
    def __init__(self, name, author, **other_kwargs):
        self.title = name
        self.author = author
        self.other_kwargs = other_kwargs

    def __repr__(self):
        return 'Book("%s", "%s")' % (self.title, self.author)


class TestUtils(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), "dumps",
                            "books.json")
        with open(file) as f:
            self.datajson = f.read()
            self.docs = json.loads(self.datajson)

    def tearDown(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.delete_all()

    @scorched.testing.skip_unless_solr
    def test_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(genre_s="fantasy").execute()
        self.assertEqual(res.result.numFound, 3)
        # delete
        si.delete_by_ids(res.result.docs[0]['id'])
        si.commit()
        res = si.query(genre_s="fantasy").execute()
        self.assertEqual(res.result.numFound, 2)
        res = si.query(genre_s="fantasy").execute(constructor=Book)
        # test constructor
        self.assertEqual([x.title for x in res.result.docs],
                         [u'The Sea of Monsters',
                          u"Sophie's World : The Greek Philosophers"])
        # TODO rollback
        # we see a rollback in solr log but entry is still deleted
        #si.rollback()
        #res = si.query(genre_s="fantasy").execute()
        #self.assertEqual(res.result.numFound, 3)

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
                          'facet_ranges': {},
                          'facet_pivot': ()})

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

    @scorched.testing.skip_unless_solr
    def test_mlt_component_query(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.query(id="978-0641723445").mlt(
            "genre_s", mintf=1, mindf=1).execute()
        # query shows only one
        self.assertEqual(res.result.numFound, 1)
        # but in more like this we get two
        self.assertEqual(len(res.more_like_these["978-0641723445"].docs), 2)
        self.assertEqual([x['author'] for x in res.more_like_these[
            "978-0641723445"].docs], [u'Rick Riordan', u'Jostein Gaarder'])

    @scorched.testing.skip_unless_solr
    def test_encoding(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        docs = {
            "id": "978-0641723445",
            "cat": ["book", "hardcover"],
            "name": u"The Höhlentripp Strauß",
            "author": u"Röüß Itoa",
            "series_t": u"Percy Jackson and \N{UMBRELLA}nicode",
            "sequence_i": 1,
            "genre_s": "fantasy",
            "inStock": True,
            "price": 12.50,
            "pages_i": 384
            }
        si.add(docs)
        si.commit()
        res = si.query(author=u"Röüß").execute()
        self.assertEqual(res.result.numFound, 1)
        for k, v in docs.items():
            self.assertEqual(res.result.docs[0][k], v)

    @scorched.testing.skip_unless_solr
    def test_debug(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        docs = {
            "id": "978-0641723445",
            "cat": ["book", "hardcover"],
            "name": u"The Höhlentripp Strauß",
            "author": u"Röüß Itoa",
            "series_t": u"Percy Jackson and \N{UMBRELLA}nicode",
            "sequence_i": 1,
            "genre_s": "fantasy",
            "inStock": True,
            "price": 12.50,
            "pages_i": 384
            }
        si.add(docs)
        si.commit()
        res = si.query(author=u"Röüß").debug().execute()
        self.assertEqual(res.result.numFound, 1)
        for k, v in docs.items():
            self.assertEqual(res.result.docs[0][k], v)
        self.assertTrue('explain' in res.debug)
        # deactivate
        res = si.query(author=u"Röüß").execute()
        self.assertFalse('explain' in res.debug)

    @scorched.testing.skip_unless_solr
    def test_spellcheck(self):
        dsn = os.environ.get("SOLR_URL", "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        opts = si.query(name=u"Monstes").spellcheck().options()
        self.assertEqual({u'q': u'name:Monstes', u'spellcheck': True}, opts)


class TestMltHandler(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), "dumps",
                            "books.json")
        with open(file) as f:
            self.datajson = f.read()
            self.docs = json.loads(self.datajson)

    @scorched.testing.skip_unless_solr
    def test_mlt(self):
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
        si = SolrInterface(dsn)
        si.add(self.docs)
        si.commit()
        res = si.mlt_query("genre_s",
                           interestingTerms="details", mintf=1, mindf=1
                           ).query(id="978-0641723445").execute()
        self.assertEqual(res.result.numFound, 2)
        self.assertEqual(res.interesting_terms, [u'genre_s:fantasy', 1.0])
        self.assertEqual([x['author'] for x in res.result.docs],
                         [u'Rick Riordan', u'Jostein Gaarder'])
