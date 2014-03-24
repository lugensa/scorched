from __future__ import unicode_literals
import unittest
import scorched.testing
import mock


class TestTesting(unittest.TestCase):

    def test_solr(self):
        self.assertRaises(Exception,
                          scorched.testing.is_solr_available("http://foo"))

    def test_solr_decorator(self):
        with mock.patch.object(scorched.testing, "is_solr_available",
                               return_value=False):
            func = lambda x: x
            self.assertTrue(hasattr(scorched.testing.skip_unless_solr(func),
                                    '__unittest_skip_why__'))
