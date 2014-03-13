import requests
import os
import unittest
import urlparse
import warnings


def is_solr_available():
    dsn = os.environ.get("SOLR_INDEX",
                         "http://localhost:8983/solr")
    if dsn is not None:
        try:
            requests.get(dsn, timeout=1)
            return True
        except Exception as e:
            print "Connection error:%s" % str(e)
    return False


def skip_unless_solr(func):
    """
    Use this decorator to skip tests which need a functional solr connection.
    The connection is given by the environment SOLR_INDEX
    """

    if is_solr_available():
        return func
    msg = "Test needs a running solr connection (SOLR_INDEX)"
    warnings.warn(msg + str(func))
    return unittest.skip(msg)(func)
