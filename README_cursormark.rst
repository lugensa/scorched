Brief description of cursormark implemntation

It's done by extending the Paginator class in search.py. There are several new attributes in this class.

    cursormark: boolean set to True to enable deep paging using cursormark. 
    cursorpos: cursor position: initially "*", and updated after a query from the nextcursormark parameter
    in the results.
    fetchsize: This is the number of rows which will be fetched with one query, and for doing a bulk data extract using deep paging it will typically be quite large ( ~1000). A suitable value will depend on the size of documents, available memory, etc. When the query is performed, this is copied to the 'rows' parameter and in the Solr Request
    rows: for cursormark queries doing a bulk data extract this may be very large (depending on the size of the index)
    userrows: For saving the user-provided 'rows' value.

The SolrSearch object is saved in the SolrResult objectt after a search so that it can be updated and reused if deep paging is enabled. A SolrResponse.__iter__ method will handle iteration through the result set and fire off a new search if needed.

The requirement that a cursormark query include a sort on a unique field is not checked in this implementation - if the sort parameter is absent then an error reponse will be returned.
