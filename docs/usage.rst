.. _usage:

First steps
===========

Installing scorched
-------------------

You can install scorched via setuptools, pip.

To use scorched, you'll need an Apache Solr installation. Scorched
currently requires at least version 3.6.1 of Apache Solr.

Using pip
~~~~~~~~~

If you have `pip <http://www.pip-installer.org>`_ installed, just type:

::

    $ pip install scorched

If you've got an old version of scorched installed, and want to
upgrade, then type:

::

    $ pip install -U scorched

That's all you need to do; all dependencies will be pulled in automatically.


Configuring a connection
------------------------

Whether you're querying or updating a Solr server, you need to set up a
connection to the Solr server. Pass the URL of the Solr server to a
SolrInterface object.

::

    >>> import scorched
    >>> si = scorched.SolrInterface("http://localhost:8983/solr/")


.. note:: Optional arguments to connection:
          :class:`scorched.connection.SolrConnection`


Adding documents
----------------

To add data to the scorched instance use a Python dictionary.

::

    >>> document = {"id":"0553573403",
    ...             "cat":"book",
    ...             "name":"A Game of Thrones",
    ...             "price":7.99,
    ...             "inStock": True,
    ...             "author_t":
    ...             "George R.R. Martin",
    ...             "series_t":"A Song of Ice and Fire",
    ...             "sequence_i":1,
    ...             "genre_s":"fantasy"}
    >>> si.add(document)

You can add lists of dictionaries in the same way. Given the example
"books.json" file, you could feed it to scorched like so:

::

    >>> file = os.path.join(os.path.dirname(__file__), "dumps",
    ...                     "books.json")
    >>> with open(file) as f:
    ...     datajson = f.read()
    ...     docs = json.loads(self.datajson)
    >>> si.add(docs)
    >>> si.commit()

.. note:: Optional arguments to add:

    See http://wiki.apache.org/solr/UpdateXmlMessages for details. Or the api
    documentation: TODO link

Deleting documents
------------------

You can delete documents individually, or delete all documents resulting from a
query.

To delete documents individually, you need to pass a list of the document ids
to scorched.

::

    >>> si.delete_by_ids([obj.id])
    >>> si.delete_by_ids([x.id for x in objs])

To delete documents by query, you construct one or more queries from `Q`
objects, in the same way that you construct a query as explained in
:ref:`optional-terms`.  You then pass those query into the
``delete_by_query()`` method:

::

    >>> si.delete_by_query(query=si.Q("game"))

To clear the entire index, there is a shortcut which simply deletes every
document in the index.

::

    >>> si.delete_all()

Deletions, like additions, only take effect after a commit (or autocommit).

.. note:: Optional arguments to delete:

    See http://wiki.apache.org/solr/UpdateXmlMessages for details. Or the api
    documentation: TODO link

Optimizing
----------

After updating an index with new data, it becomes fragmented and performance
suffers. This means that you need to optimize the index. When and how often you
do this is something you need to decide on a case by case basis.  If you only
add data infrequently, you should optimize after every new update; if you
trickle in data on a frequent basis, you need to think more about it.  See
http://wiki.apache.org/solr/SolrPerformanceFactors#Optimization_Considerations.

Either way, to optimize an index, simply call:

::

    >>> si.optimize()

A Solr optimize also performs a commit, so if you’re about to ``optimize()``
anyway, you can leave off the preceding ``commit()``. It doesn’t particularly
hurt to do both though.

Rollback
--------

If you haven’t yet added/deleted documents since the last commit, you can issue
a rollback to revert the index state to that of the last commit.

::

    >>> si.rollback()
