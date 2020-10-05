from __future__ import print_function
from __future__ import unicode_literals
import requests
import os
import unittest
if not hasattr(unittest, "skip"):
    try:
        import unittest2 as unittest
    except:
        pass
import warnings

from scorched.compat import str


def is_solr_available(dsn=None):
    if not dsn:
        dsn = os.environ.get("SOLR_URL",
                             "http://localhost:8983/solr")
    if dsn is not None:
        try:
            requests.get(dsn, timeout=1)
            return True
        except Exception as e:
            print("Connection error:%s" % str(e))
    return False


def skip_unless_solr(func):
    """
    Use this decorator to skip tests which need a functional Solr connection.
    The connection is given by the environment SOLR_URL
    """

    if is_solr_available():
        return func
    msg = "Test needs a running Solr connection (SOLR_URL)"
    warnings.warn(msg + str(func))
    return unittest.skip(msg)(func)
