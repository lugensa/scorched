Scorched
========

Scorched is a sunburnt offspring and like all offspring it tries to make
things better or at least different.

Git Repository and issue tracker: https://github.com/lugensa/scorched

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

- API is more lightweight e.g. ``add`` consums now only dicts.

- Wildcard search strings need to be explicitly set.

- ...
