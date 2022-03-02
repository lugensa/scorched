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

We changed to pytest and pytest-docker to spin-off
the tests.

The account on your os under which you run the tests
should have permissions to start docker processes.

First checkout the sources::

  https://github.com/lugensa/scorched.git

Now use tox for testing::

  cd scorched
  tox

Additionally use pytest directly::

  cd scorched
  python3.10 -mvenv .
  ./bin/pip install -e .[test]
  ./bin/pytest ./scorched

Running the tests will start a solr-8.11.1 in docker
(see scorched/tests/docker-compose.yml).
