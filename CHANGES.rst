0.7 (2015-04-17)
----------------

- Test against solr 4.10.2 and added python 3.4 to travis.

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
