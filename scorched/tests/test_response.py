import unittest
import os.path
import scorched.response


class ResultsTestCase(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), "dumps",
                            "request_w_facets.json")
        with open(file) as f:
            self.data = f.read()

    def test_reponse(self):
        res = scorched.response.SolrResponse.from_json(self.data)
        self.assertEqual(res.status, 0)
        self.assertEqual(res.QTime, 1)
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
