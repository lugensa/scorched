CHANGES
=======

0.11.0 (2016-10-11)
-------------------

- Highlighting is now available in the result documents as the
  ``solr_highlights`` field (mlissner)

- smaller documentation cleanup


0.10.2 (2016-09-27)
-------------------

- Fix is_iter implementation #30 (mamico)

- Multi-value date fields work (mlissner)

- Fixes error in the readme so that DEBUG mode works as documented (mlissner)


0.10.1 (2016-06-15)
-------------------

- Fixing setup.py classifier.


0.10 (2016-06-15)
-----------------

- Return response for update actions (mamico)

- Add support for Solr cursors (Chronial)

- Added stats option (rlskoeser)


0.9 (2015-11-09)
----------------

- Better check datetime dynamicfields (mamico)

- RealTime Get (Chronial)

- TermVector support (Chronial)


0.8 (2015-08-26)
----------------

- use compat.basestring over compat.str in date convert (mamico)

- remove test from core requirements (mamico)

- added search_timeout paramter to SolrConnection (mamico)

- fix. Do not alter documents while adding new documents


0.7 (2015-04-17)
----------------

- Test against Solr 4.10.2 and added Python 3.4 to travis.

- Added support for dismax queries.

- Added support edismax field aliases.

- Added support for facet ranges.


0.6 (2014-06-23)
----------------

- Add spellchecking for scorched queries. (#9707)


0.5 (2014-06-05)
----------------

- Add `debugQuery` parameter to search. (#9903)

- Add possibility to specify the request handler to use per query. (#9704)


0.4.1 (2014-04-16)
------------------

- Fixed again fields in field_limiter.


0.4 (2014-04-16)
----------------

- Fixed fields convert to arrays.

- Added FacetPivotOptions.

- Added PostingsHighlightOptions.

- Added boundaryScanner to HighlightOptions.


0.3 (2014-04-03)
----------------

- Makes SolrResponse iterable.


0.2 (2014-03-24)
----------------

- Added more tests

- Added description in setup.py


0.1 (2014-03-20)
----------------

- Python 3

- Cleaner api moved redundant functions

- Cleaner api removed filter_exclude use ~si.Q()

- Cleaner api removed exclude use ~si.Q()

- Fixed mlt_search (mlt component and handler)

- Removed mx.DateTime

- Removed redundant more_like_this

- Offspring of sunburnt is born
