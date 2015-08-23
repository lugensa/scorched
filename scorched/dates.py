from __future__ import unicode_literals
import datetime
import fnmatch
import math
import pytz
import re
import scorched.exc

from scorched.compat import basestring
from scorched.compat import python_2_unicode_compatible


year = r'[+/-]?\d+'
tzd = r'Z|((?P<tzd_sign>[-+])(?P<tzd_hour>\d\d):(?P<tzd_minute>\d\d))'
extended_iso_template = r'(?P<year>' + year + r""")
               (-(?P<month>\d\d)
               (-(?P<day>\d\d)
            ([T%s](?P<hour>\d\d)
                :(?P<minute>\d\d)
               (:(?P<second>\d\d)
               (.(?P<fraction>\d+))?)?
               (""" + tzd + """)?)?
               )?)?"""
extended_iso = extended_iso_template % " "
extended_iso_re = re.compile('^' + extended_iso + '$', re.X)


def datetime_from_w3_datestring(s):
    """ We need to extend ISO syntax (as permitted by the standard) to allow
    for dates before 0AD and after 9999AD. This is how to parse such a string
    """
    m = extended_iso_re.match(s)
    if not m:
        raise ValueError
    d = m.groupdict()
    d['year'] = int(d['year'])
    d['month'] = int(d['month'] or 1)
    d['day'] = int(d['day'] or 1)
    d['hour'] = int(d['hour'] or 0)
    d['minute'] = int(d['minute'] or 0)
    d['fraction'] = d['fraction'] or '0'
    d['second'] = float("%s.%s" % ((d['second'] or '0'), d['fraction']))
    del d['fraction']
    if d['tzd_sign']:
        if d['tzd_sign'] == '+':
            tzd_sign = 1
        elif d['tzd_sign'] == '-':
            tzd_sign = -1
        tz_delta = datetime_delta_factory(tzd_sign * int(d['tzd_hour']),
                                          tzd_sign * int(d['tzd_minute']))
    else:
        tz_delta = datetime_delta_factory(0, 0)
    del d['tzd_sign']
    del d['tzd_hour']
    del d['tzd_minute']
    d['tzinfo'] = pytz.utc
    dt = datetime_factory(**d) + tz_delta
    return dt


class DateTimeRangeError(ValueError):
    pass


def datetime_factory(**kwargs):
    second = kwargs.get('second')
    if second is not None:
        f, i = math.modf(second)
        kwargs['second'] = int(i)
        kwargs['microsecond'] = int(f * 1000000)
    try:
        return datetime.datetime(**kwargs)
    except ValueError as e:
        raise DateTimeRangeError(e.args[0])


def datetime_delta_factory(hours, minutes):
    return datetime.timedelta(hours=hours, minutes=minutes)


class solr_date(object):
    """
    This class can be initialized from native python datetime
    objects and will serialize to a format appropriate for Solr
    """
    def __init__(self, v):
        if isinstance(v, solr_date):
            self._dt_obj = v._dt_obj
        elif isinstance(v, basestring):
            self._dt_obj = datetime_from_w3_datestring(v)
        elif hasattr(v, "strftime"):
            self._dt_obj = self.from_date(v)
        else:
            raise scorched.exc.SolrError(
                "Cannot initialize solr_date from %s object" % type(v))

    @staticmethod
    def from_date(dt_obj):
        # Python datetime objects may include timezone information
        if hasattr(dt_obj, 'tzinfo') and dt_obj.tzinfo:
            # but Solr requires UTC times.
            return dt_obj.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            return dt_obj

    @property
    def microsecond(self):
        return self._dt_obj.microsecond

    def __repr__(self):
        return repr(self._dt_obj)

    @python_2_unicode_compatible
    def __str__(self):
        """ Serialize a datetime object in the format required
        by Solr. See http://wiki.apache.org/solr/IndexingDates
        """
        return "%sZ" % (self._dt_obj.isoformat(), )

    def __lt__(self, other):
        try:
            other = other._dt_obj
        except AttributeError:
            pass
        return self._dt_obj < other

    def __eq__(self, other):
        try:
            other = other._dt_obj
        except AttributeError:
            pass
        return self._dt_obj == other


def is_datetime_field(name, datefields):
    if name in datefields:
        return True
    for fieldpattern in [d for d in datefields if '*' in d]:
        # XXX: there is better than fnmatch ?
        if fnmatch.fnmatch(name, fieldpattern):
            return True
    return False
