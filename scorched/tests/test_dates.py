from __future__ import unicode_literals
import datetime
import pytz
import unittest
import scorched.exc

from scorched.dates import (solr_date, datetime_from_w3_datestring,
                            datetime_factory)

not_utc = pytz.timezone('Etc/GMT-3')

samples_from_pydatetimes = {
    "2009-07-23T03:24:34.000376Z":
    [datetime.datetime(2009, 7, 23, 3, 24, 34, 376),
     datetime.datetime(2009, 7, 23, 3, 24, 34, 376, pytz.utc)],
    "2009-07-23T00:24:34.000376Z":
    [not_utc.localize(datetime.datetime(2009, 7, 23, 3, 24, 34, 376)),
     datetime.datetime(2009, 7, 23, 0, 24, 34, 376, pytz.utc)],
    "2009-07-23T03:24:34Z":
    [datetime.datetime(2009, 7, 23, 3, 24, 34),
     datetime.datetime(2009, 7, 23, 3, 24, 34, tzinfo=pytz.utc)],
    "2009-07-23T00:24:34Z":
    [not_utc.localize(datetime.datetime(2009, 7, 23, 3, 24, 34)),
     datetime.datetime(2009, 7, 23, 0, 24, 34, tzinfo=pytz.utc)]
}

samples_from_strings = {
    # These will not have been serialized by us, but we should deal with them
    "2009-07-23T03:24:34Z":
    datetime.datetime(2009, 7, 23, 3, 24, 34, tzinfo=pytz.utc),
    "2009-07-23T03:24:34.1Z":
    datetime.datetime(2009, 7, 23, 3, 24, 34, 100000, pytz.utc),
    "2009-07-23T03:24:34.123Z":
    datetime.datetime(2009, 7, 23, 3, 24, 34, 122999, pytz.utc)
}


def check_solr_date_from_date(s, date, canonical_date):
    from scorched.compat import str
    assert str(solr_date(date)) == s, "Unequal representations of %r: %r and %r" % (
        date, str(solr_date(date)), s)
    check_solr_date_from_string(s, canonical_date)


def check_solr_date_from_string(s, date):
    assert solr_date(s)._dt_obj == date, "Unequal representations of %r: %r and %r" % (
        solr_date(s)._dt_obj, date, s)


def test_solr_date_from_pydatetimes():
    for k, v in list(samples_from_pydatetimes.items()):
        yield check_solr_date_from_date, k, v[0], v[1]


def test_solr_date_from_strings():
    for k, v in list(samples_from_strings.items()):
        yield check_solr_date_from_string, k, v


class TestDates(unittest.TestCase):

    def test_datetime_from_w3_datestring(self):
        self.assertRaises(ValueError,
                          datetime_from_w3_datestring, "")
        self.assertEqual(datetime_from_w3_datestring("2009-07-23T03:24:34.123+16:50"),
                         datetime.datetime(2009, 7, 23, 20, 14, 34, 122999,
                                           tzinfo=pytz.utc))
        self.assertEqual(datetime_from_w3_datestring("2009-07-23T03:24:34.123-16:50"),
                         datetime.datetime(2009, 7, 22, 10, 34, 34, 122999,
                                           tzinfo=pytz.utc))

    def test_datetime_factory(self):
        self.assertRaises(ValueError,
                          datetime_factory, year=1990, month=12,
                          day=12345)

    def test_solr_date(self):
        self.assertRaises(scorched.exc.SolrError, solr_date, None)
        s = solr_date("2009-07-23T03:24:34.000376Z")
        s_older = solr_date("2007-07-23T03:24:34.000376Z")
        self.assertEqual(s.microsecond, 376)
        self.assertEqual(s, solr_date(s))
        self.assertTrue(s == s)
        self.assertTrue(s > s_older)
        self.assertTrue(s_older < s)
        self.assertRaises(TypeError, s.__lt__, datetime.datetime(2009, 7, 22, 10))
        if scorched.compat.is_py2:  # pragma: no cover
            self.assertRaises(TypeError, s.__eq__, datetime.datetime(2009, 7, 22, 10))
        else:  # pragma: no cover
            self.assertFalse(s == "Foo")
        self.assertEqual(s.__repr__(), 'datetime.datetime(2009, 7, 23, 3, 24, 34, 376, tzinfo=<UTC>)')

    def test_solr_date_from_str(self):
        # str here is original str from python
        self.assertTrue("'str'" in repr(str))
        s = solr_date(str("2009-07-23T03:24:34.000376Z"))
        self.assertEqual(s, solr_date(s))
        self.assertTrue(s == s)
