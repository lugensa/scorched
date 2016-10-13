Scorched
========

Scorched is a sunburnt offspring and like all offspring it tries to make
things better or at least different.

Git Repository and issue tracker: https://github.com/lugensa/scorched

Documentation: http://scorched.readthedocs.org/en/latest/

.. |travisci| image::  https://travis-ci.org/lugensa/scorched.png
.. _travisci: https://travis-ci.org/lugensa/scorched

.. image:: https://coveralls.io/repos/lugensa/scorched/badge.png
    :target: https://coveralls.io/r/lugensa/scorched

|travisci|_

.. _Solr : http://lucene.apache.org/solr/
.. _Lucene : http://lucene.apache.org/java/docs/index.html


Following some major differences:

- No validation of queries in client code (make code much more lightweight)

- Send and receive as json. (Faster 20k docs from 6.5s to 1.3s)

- API is more lightweight e.g. ``add`` consumes now only dicts.

- Wildcard search strings need to be explicitly set.

- Python 3

- Drops support for Solr < 4.3.0

- ...


Local testing
=============

First checkout the sources::

  https://github.com/lugensa/scorched.git

Now create a virtual-env and install some dependencies::

  cd scorched
  virtualenv ./
  bin/pip install -e .
  bin/pip install -e .[test]

Start the Solr server to test against::

  # DEBUG=true|false: verbose output of Solr server on|off
  # SOLR_VERSION=x.y.z (the version to test against)
  # the Solr startup script reports the pid of the Solr process
  SOLR_VERSION=4.10.2 SOLR_PORT=44177 DEBUG=true SOLR_CONFS="scorched/tests/solrconfig.xml" ./testing-solr.sh

  # stop Solr
  kill -9 $pid

Running the tests::

  SOLR_URL=http://localhost:44177/solr/core0 ./bin/nosetests -s scorched
