from __future__ import unicode_literals
import datetime
import pytz

from scorched.compat import str
from scorched.dates import solr_date

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
