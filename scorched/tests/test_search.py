from __future__ import print_function
from __future__ import unicode_literals
import datetime
from scorched.exc import SolrError
from scorched.search import (SolrSearch, MltSolrSearch, PaginateOptions,
                             SortOptions, FieldLimitOptions, FacetOptions,
                             GroupOptions, HighlightOptions, DismaxOptions,
                             MoreLikeThisOptions, EdismaxOptions,
                             PostingsHighlightOptions, FacetPivotOptions,
                             RequestHandlerOption, DebugOptions,
                             params_from_dict, FacetRangeOptions,
                             TermVectorOptions, StatOptions,
                             is_iter)
from scorched.strings import WildcardString
from nose.tools import assert_equal


debug = False

base_good_query_data = {
    "query_by_term": [
        (["hello"], {},
         [("q", b"hello")]),
        (["hello"], {"int_field": 3},
         [("q", b"hello AND int_field:3")]),
        (["hello", "world"], {},
         [("q", b"hello AND world")]),
        # NB this next is not really what we want,
        # probably this should warn
        (["hello world"], {},
         [("q", b"hello\\ world")]),
    ],

    "query_by_phrase": [
        (["hello"], {},
         [("q", b"hello")]),
        (["hello"], {"int_field": 3},
         # Non-text data is always taken to be a term, and terms come before
         # phrases, so order is reversed
         [("q", b"int_field:3 AND hello")]),
        (["hello", "world"], {},
         [("q", b"hello AND world")]),
        (["hello world"], {},
         [("q", b"hello\\ world")]),
        ([], {'string_field': ['hello world', 'goodbye, cruel world']},
         [("q", b"string_field:goodbye,\\ cruel\\ world AND string_field:hello\\ world")]),
    ],

    "query": [
        # Basic queries
        (["hello"], {},
         [("q", b"hello")]),
        (["hello"], {"int_field": 3},
         [("q", b"hello AND int_field:3")]),
        (["hello", "world"], {},
         [("q", b"hello AND world")]),
        (["hello world"], {},
         [("q", b"hello\\ world")]),
        # Test fields
        # Boolean fields take any truth-y value
        ([], {"boolean_field": True},
         [("q", b"boolean_field:true")]),
        ([], {"boolean_field": 'true'},
         [("q", b"boolean_field:true")]),
        ([], {"boolean_field": "false"},
         [("q", b"boolean_field:false")]),
        ([], {"boolean_field": False},
         [("q", b"boolean_field:false")]),
        ([], {"int_field": 3},
         [("q", b"int_field:3")]),
        ([], {"sint_field": 3},
         [("q", b"sint_field:3")]),
        ([], {"long_field": 2 ** 31},
         [("q", b"long_field:2147483648")]),
        ([], {"slong_field": 2 ** 31},
         [("q", b"slong_field:2147483648")]),
        ([], {"float_field": 3.0},
         [("q", b"float_field:3.0")]),
        ([], {"sfloat_field": 3.0},
         [("q", b"sfloat_field:3.0")]),
        ([], {"double_field": 3.0},
         [("q", b"double_field:3.0")]),
        ([], {"sdouble_field": 3.0},
         [("q", b"sdouble_field:3.0")]),
        ([], {"date_field": datetime.datetime(2009, 1, 1)},
         [("q", b"date_field:2009\\-01\\-01T00\\:00\\:00Z")]),
        # Test ranges
        ([], {"int_field__any": True},
         [("q", b"int_field:[* TO *]")]),
        ([], {"int_field__lt": 3},
         [("q", b"int_field:{* TO 3}")]),
        ([], {"int_field__gt": 3},
         [("q", b"int_field:{3 TO *}")]),
        ([], {"int_field__rangeexc": (-3, 3)},
         [("q", b"int_field:{\-3 TO 3}")]),
        ([], {"int_field__rangeexc": (3, -3)},
         [("q", b"int_field:{\-3 TO 3}")]),
        ([], {"int_field__lte": 3},
         [("q", b"int_field:[* TO 3]")]),
        ([], {"int_field__gte": 3},
         [("q", b"int_field:[3 TO *]")]),
        ([], {"int_field__range": (-3, 3)},
         [("q", b"int_field:[\-3 TO 3]")]),
        ([], {"int_field__range": (3, -3)},
         [("q", b"int_field:[\-3 TO 3]")]),
        ([], {"date_field__lt": datetime.datetime(2009, 1, 1)},
         [("q", b"date_field:{* TO 2009\\-01\\-01T00\\:00\\:00Z}")]),
        ([], {"date_field__gt": datetime.datetime(2009, 1, 1)},
         [("q", b"date_field:{2009\\-01\\-01T00\\:00\\:00Z TO *}")]),
        ([], {
            "date_field__rangeexc": (datetime.datetime(2009, 1, 1), datetime.datetime(2009, 1, 2))},
         [("q", b"date_field:{2009\\-01\\-01T00\\:00\\:00Z TO 2009\\-01\\-02T00\\:00\\:00Z}")]),
        ([], {"date_field__lte": datetime.datetime(2009, 1, 1)},
         [("q", b"date_field:[* TO 2009\\-01\\-01T00\\:00\\:00Z]")]),
        ([], {"date_field__gte": datetime.datetime(2009, 1, 1)},
         [("q", b"date_field:[2009\\-01\\-01T00\\:00\\:00Z TO *]")]),
        ([], {
            "date_field__range": (datetime.datetime(2009, 1, 1), datetime.datetime(2009, 1, 2))},
         [("q", b"date_field:[2009\\-01\\-01T00\\:00\\:00Z TO 2009\\-01\\-02T00\\:00\\:00Z]")]),
        ([], {'string_field': ['hello world', 'goodbye, cruel world']},
         [("q", b"string_field:goodbye,\\ cruel\\ world AND string_field:hello\\ world")]),
        # Raw strings
        ([], {'string_field': "abc*???"},
         [("q", b"string_field:abc\\*\\?\\?\\?")]),
    ],
}

good_query_data = {
    "filter_by_term": [
        (["hello"], {},
         [("fq", b"hello"), ("q", b"*:*")]),
        # test multiple fq
        (["hello"], {"int_field": 3},
         [("fq", b"hello"), ("fq", b"int_field:3"), ("q", b"*:*")]),
        (["hello", "world"], {},
         [("fq", b"hello"), ("fq", b"world"), ("q", b"*:*")]),
        # NB this next is not really what we want,
        # probably this should warn
        (["hello world"], {},
         [("fq", b"hello\\ world"), ("q", b"*:*")]),
    ],

    "filter_by_phrase": [
        (["hello"], {},
         [("fq", b"hello"), ("q", b"*:*")]),
        # test multiple fq
        (["hello"], {"int_field": 3},
         [("fq", b"hello"), ("fq", b"int_field:3"), ("q", b"*:*")]),
        (["hello", "world"], {},
         [("fq", b"hello"), ("fq", b"world"), ("q", b"*:*")]),
        (["hello world"], {},
         [("fq", b"hello\\ world"), ("q", b"*:*")]),
    ],

    "filter": [
        (["hello"], {},
         [("fq", b"hello"), ("q", b"*:*")]),
        # test multiple fq
        (["hello"], {"int_field": 3},
         [("fq", b"hello"), ("fq", b"int_field:3"), ("q", b"*:*")]),
        (["hello", "world"], {},
         [("fq", b"hello"), ("fq", b"world"), ("q", b"*:*")]),
        (["hello world"], {},
         [("fq", b"hello\\ world"), ("q", b"*:*")]),
    ],
}
good_query_data.update(base_good_query_data)


def check_query_data(method, args, kwargs, output):
    solr_search = SolrSearch(None)
    p = getattr(solr_search, method)(*args, **kwargs).params()
    assert p == output, "Unequal: %r, %r" % (p, output)


def check_mlt_query_data(method, args, kwargs, output):
    solr_search = MltSolrSearch(None)
    p = getattr(solr_search, method)(*args, **kwargs).params()
    assert p == output, "Unequal: %r, %r" % (p, output)


good_option_data = {
    PaginateOptions: (
        ({"start": 5, "rows": 10},
         {"start": 5, "rows": 10}),
        ({"start": 5, "rows": None},
         {"start": 5}),
        ({"start": None, "rows": 10},
         {"rows": 10}),
    ),
    FacetOptions: (
        ({"fields": "int_field"},
         {"facet": True, "facet.field": ["int_field"]}),
        ({"fields": ["int_field", "text_field"]},
         {"facet": True, "facet.field": ["int_field", "text_field"]}),
        ({"prefix": "abc"},
         {"facet": True, "facet.prefix": "abc"}),
        ({"prefix": "abc", "sort": True, "limit": 3, "offset": 25, "mincount": 1, "missing": False, "method": "enum"},
         {"facet": True, "facet.prefix": "abc", "facet.sort": True, "facet.limit": 3, "facet.offset": 25, "facet.mincount": 1, "facet.missing": False, "facet.method": "enum"}),
        ({"fields": "int_field", "prefix": "abc"},
         {"facet": True, "facet.field": ["int_field"], "f.int_field.facet.prefix": "abc"}),
        ({"fields": "int_field", "prefix": "abc", "limit": 3},
         {"facet": True, "facet.field": ["int_field"], "f.int_field.facet.prefix": "abc", "f.int_field.facet.limit": 3}),
        ({"fields": ["int_field", "text_field"], "prefix": "abc", "limit": 3},
         {"facet": True, "facet.field": ["int_field", "text_field"], "f.int_field.facet.prefix": "abc", "f.int_field.facet.limit": 3, "f.text_field.facet.prefix": "abc", "f.text_field.facet.limit": 3, }),
    ),
    FacetRangeOptions: (
        ({"fields": "field1", "start": 10, "end": 20, "gap": 2, "hardend": False,
          "include": "outer", "other": "all", "limit": 10, "mincount": 1},
         {"facet": True, "facet.range": ["field1"], "f.field1.facet.range.start": 10,
          "f.field1.facet.range.end": 20, "f.field1.facet.range.gap": 2,
          "f.field1.facet.range.hardend": "false", "f.field1.facet.range.include": "outer",
          "f.field1.facet.range.other": "all", "f.field1.facet.limit": 1,
          "f.field1.facet.mincount": 1}),
    ),
    FacetPivotOptions: (
        ({"fields": ["text_field"]},
         {"facet": True, "facet.pivot": "text_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"facet": True, "facet.pivot": "int_field,text_field"}),
        ({"fields": ["int_field", "text_field"], "mincount": 2},
         {"facet": True, "facet.pivot": "int_field,text_field", "facet.pivot.mincount": 2}),
    ),
    GroupOptions: (
        ({"field": "int_field", "limit": 10},
         {"group": True, "group.limit": 10, "group.field": "int_field"}),
    ),
    SortOptions: (
        ({"field": "int_field"},
         {"sort": "int_field asc"}),
        ({"field": "-int_field"},
         {"sort": "int_field desc"}),
    ),
    HighlightOptions: (
        ({"fields": "int_field"},
         {"hl": True, "hl.fl": "int_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"hl": True, "hl.fl": "int_field,text_field"}),
        ({"snippets": 3},
         {"hl": True, "hl.snippets": 3}),
        ({"snippets": 3, "fragsize": 5, "mergeContinuous": True, "requireFieldMatch": True, "maxAnalyzedChars": 500, "alternateField": "text_field", "maxAlternateFieldLength": 50, "formatter": "simple", "simple.pre": "<b>", "simple.post": "</b>", "fragmenter": "regex", "usePhraseHighlighter": True, "highlightMultiTerm": True, "regex.slop": 0.2, "regex.pattern": "\w", "regex.maxAnalyzedChars": 100},
         {"hl": True, "hl.snippets": 3, "hl.fragsize": 5, "hl.mergeContinuous": True, "hl.requireFieldMatch": True, "hl.maxAnalyzedChars": 500, "hl.alternateField": "text_field", "hl.maxAlternateFieldLength": 50, "hl.formatter": "simple", "hl.simple.pre": "<b>", "hl.simple.post": "</b>", "hl.fragmenter": "regex", "hl.usePhraseHighlighter": True, "hl.highlightMultiTerm": True, "hl.regex.slop": 0.2, "hl.regex.pattern": "\w", "hl.regex.maxAnalyzedChars": 100}),
        ({"fields": "int_field", "snippets": "3"},
         {"hl": True, "hl.fl": "int_field", "f.int_field.hl.snippets": 3}),
        ({"fields": "int_field", "snippets": 3, "fragsize": 5},
         {"hl": True, "hl.fl": "int_field", "f.int_field.hl.snippets": 3, "f.int_field.hl.fragsize": 5}),
        ({"fields": ["int_field", "text_field"], "snippets": 3, "fragsize": 5},
         {"hl": True, "hl.fl": "int_field,text_field", "f.int_field.hl.snippets": 3, "f.int_field.hl.fragsize": 5, "f.text_field.hl.snippets": 3, "f.text_field.hl.fragsize": 5}),
    ),
    PostingsHighlightOptions: (
        ({"fields": "int_field"},
         {"hl": True, "hl.fl": "int_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"hl": True, "hl.fl": "int_field,text_field"}),
        ({"snippets": 3},
         {"hl": True, "hl.snippets": 3}),
        ({"fields": ["int_field", "text_field"], "snippets": 1,
          "tag.pre": "&lt;em&gt;", "tag.post": "&lt;em&gt;",
          "tag.ellipsis": "...", "defaultSummary": True, "encoder": "simple",
          "score.k1": 1.2, "score.b": 0.75, "score.pivot": 87,
          "bs.type": "SENTENCE", "maxAnalyzedChars": 10000, },
         {'f.text_field.hl.score.b': 0.75, 'f.int_field.hl.encoder': u'simple',
          'f.int_field.hl.tag.pre': u'&lt;em&gt;', 'f.text_field.hl.tag.pre':
          u'&lt;em&gt;', 'f.text_field.hl.defaultSummary': True,
          'f.text_field.hl.tag.post': u'&lt;em&gt;', 'f.text_field.hl.bs.type':
          u'SENTENCE', 'f.int_field.hl.tag.ellipsis': u'...',
          'f.text_field.hl.score.k1': 1.2, 'f.text_field.hl.tag.ellipsis':
          u'...', 'f.int_field.hl.score.pivot': 87.0,
          'f.int_field.hl.tag.post': u'&lt;em&gt;', 'f.int_field.hl.bs.type':
          u'SENTENCE', 'f.int_field.hl.score.b': 0.75,
          'f.text_field.hl.maxAnalyzedChars': u'10000', 'hl': True,
          'f.text_field.hl.encoder': u'simple', 'hl.fl':
          'int_field,text_field', 'f.int_field.hl.snippets': 1,
          'f.text_field.hl.snippets': 1, 'f.int_field.hl.maxAnalyzedChars':
          u'10000', 'f.int_field.hl.score.k1': 1.2,
          'f.int_field.hl.defaultSummary': True, 'f.text_field.hl.score.pivot':
          87.0}),
    ),
    MoreLikeThisOptions: (
        ({"fields": "int_field"},
         {"mlt": True, "mlt.fl": "int_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"mlt": True, "mlt.fl": "int_field,text_field"}),
        ({"fields": ["text_field", "string_field"], "query_fields": {"text_field": 0.25, "string_field": 0.75}},
         {"mlt": True, "mlt.fl": "string_field,text_field", "mlt.qf": "text_field^0.25 string_field^0.75"}),
        ({"fields": "text_field", "count": 1},
         {"mlt": True, "mlt.fl": "text_field", "mlt.count": 1}),
    ),
    TermVectorOptions: (
        ({},
         {"tv": True}),
        ({"offsets": True},
         {"tv": True, "tv.offsets": True}),
        ({"fields": "text_field"},
         {"tv": True, "tv.fl": "text_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"tv": True, "tv.fl": "int_field, text_field"}),
        ({"all": True, "df": 1, "offsets": 0, "positions": False,
          "payloads": "true", "tf": False, "tf_idf": True},
         {'tv': True, 'tv.df': True, 'tv.all': True, 'tv.tf_idf': True,
          'tv.tf': False, 'tv.offsets': False, 'tv.payloads': True,
          'tv.positions': False}),
        ({"fields": "text_field", "all": True},
         {'tv': True, 'tv.fl': 'text_field', 'f.text_field.tv.all': True}),
        ({"fields": ["int_field", "text_field"], "tf": True},
         {'tv': True, 'tv.fl': 'int_field,text_field',
          'f.text_field.tv.tf': True, 'f.int_field.tv.tf': True}),
    ),
    DismaxOptions: (
        ({"qf": {"text_field": 0.25, "string_field": 0.75}},
         {'defType': 'dismax', 'qf': 'text_field^0.25 string_field^0.75'}),
        ({"pf": {"text_field": 0.25, "string_field": 0.75}},
         {'defType': 'dismax', 'pf': 'text_field^0.25 string_field^0.75'}),
        ({"qf": {"text_field": 0.25, "string_field": 0.75}, "mm": 2},
         {'mm': 2, 'defType': 'dismax', 'qf': 'text_field^0.25 string_field^0.75'}),
    ),
    EdismaxOptions: (
        ({"qf": {"text_field": 0.25, "string_field": 0.75}},
         {'defType': 'edismax', 'qf': 'text_field^0.25 string_field^0.75'}),
        ({"pf": {"text_field": 0.25, "string_field": 0.75}},
         {'defType': 'edismax', 'pf': 'text_field^0.25 string_field^0.75'}),
        ({"qf": {"text_field": 0.25, "string_field": 0.75}, "mm": 2},
         {'mm': 2, 'defType': 'edismax', 'qf': 'text_field^0.25 string_field^0.75'}),
    ),
    FieldLimitOptions: (
        ({},
         {}),
        ({"fields": "int_field"},
         {"fl": "int_field"}),
        ({"fields": ["int_field", "text_field"]},
         {"fl": "int_field,text_field"}),
        ({"score": True},
         {"fl": "score"}),
        ({"all_fields": True, "score": True},
         {"fl": "*,score"}),
        ({"fields": "int_field", "score": True},
         {"fl": "int_field,score"}),
    ),
    RequestHandlerOption: (
        ({"handler": None},
         {}),
        ({"handler": "hans"},
         {'qt': 'hans'}),
    ),
    DebugOptions: (
        ({"debug": None},
         {}),
        ({"debug": False},
         {}),
        ({"debug": True},
         {'debugQuery': True}),
    ),
    StatOptions: (
        ({"fields": "int_field"},
         {"stats": True, "stats.field": ['int_field']}),
        ({"fields": ["int_field", "float_field"]},
         {"stats": True, "stats.field": ['int_field', 'float_field']}),
        ({"fields": ["int_field", "float_field"], "facet": "field0"},
         {"stats": True, "stats.field": ['int_field', 'float_field'],
          "stats.facet": "field0"}),
    ),
}


def check_good_option_data(OptionClass, kwargs, output):
    optioner = OptionClass()
    optioner.update(**kwargs)
    assert set(optioner.options()) == set(output), "Unequal: %r, %r" % (
        optioner.options(), output)

# All these tests should really nominate which exception they're going to
# throw.
bad_option_data = {
    PaginateOptions: (
        {"start": -1, "rows": None},  # negative start
        {"start": None, "rows": -1},  # negative rows
    ),
    FacetOptions: (
        {"oops": True},  # undefined option
        {"limit": "a"},  # invalid type
        {"sort": "yes"},  # invalid choice
        {"offset": -1},  # invalid value
    ),
    SortOptions: (
    ),
    HighlightOptions: (
        {"oops": True},  # undefined option
        {"snippets": "a"},  # invalid type
    ),
    MoreLikeThisOptions: (
        # string_field in query_fields, not fields
        {"fields": "text_field", "query_fields":
            {"text_field": 0.25, "string_field": 0.75}},
        # Non-float value for boost
        {"fields": "text_field", "query_fields": {"text_field": "a"}},
        {"fields": "text_field", "oops": True},  # undefined option
        {"fields": "text_field", "count": "a"}  # Invalid value for option
    ),
    TermVectorOptions: (
        {"foobar": True},  # undefined option
    ),
    DismaxOptions: (
        # no ss
        {"ss": {"text_field": 0.25, "string_field": 0.75}},
        # no float in pf
        {"pf": {"text_field": 0.25, "string_field": "ABBS"}},
    ),
    StatOptions: (
        {"oops": True},  # undefined option
    )
}


def check_bad_option_data(OptionClass, kwargs):
    option = OptionClass()
    exception_raised = False
    try:
        option.update(**kwargs)
    except SolrError:
        exception_raised = True
    assert exception_raised


complex_boolean_queries = (
    (lambda q: q.query("hello world").filter(q.Q(text_field="tow") | q.Q(boolean_field=False, int_field__gt=3)),
     [('fq', b'text_field:tow OR (boolean_field:false AND int_field:{3 TO *})'), ('q', b'hello\\ world')]),
    # test multiple fq
    (lambda q: q.query("hello world").filter(q.Q(text_field="tow") & q.Q(boolean_field=False, int_field__gt=3)),
     [('fq', b'boolean_field:false'), ('fq', b'int_field:{3 TO *}'), ('fq', b'text_field:tow'), ('q',  b'hello\\ world')]),
    # Test various combinations of NOTs at the top level.
    # Sometimes we need to do the *:* trick, sometimes not.
    (lambda q: q.query(~q.Q("hello world")),
     [('q',  b'NOT hello\\ world')]),
    (lambda q: q.query(~q.Q("hello world") & ~q.Q(int_field=3)),
     [('q',  b'NOT hello\\ world AND NOT int_field:3')]),
    (lambda q: q.query("hello world", ~q.Q(int_field=3)),
     [('q', b'hello\\ world AND NOT int_field:3')]),
    (lambda q: q.query("abc", q.Q("def"), ~q.Q(int_field=3)),
     [('q', b'abc AND def AND NOT int_field:3')]),
    (lambda q: q.query("abc", q.Q("def") & ~q.Q(int_field=3)),
     [('q', b'abc AND def AND NOT int_field:3')]),
    (lambda q: q.query("abc", q.Q("def") | ~q.Q(int_field=3)),
     [('q', b'abc AND (def OR (*:* AND NOT int_field:3))')]),
    (lambda q: q.query(q.Q("abc") | ~q.Q("def")),
     [('q', b'abc OR (*:* AND NOT def)')]),
    (lambda q: q.query(q.Q("abc") | q.Q(~q.Q("def"))),
     [('q', b'abc OR (*:* AND NOT def)')]),
    # Make sure that ANDs are flattened
    (lambda q: q.query("def", q.Q("abc"), q.Q(q.Q("xyz"))),
     [('q', b'abc AND def AND xyz')]),
    # Make sure that ORs are flattened
    (lambda q: q.query(q.Q("def") | q.Q(q.Q("xyz"))),
     [('q', b'def OR xyz')]),
    # Make sure that empty queries are discarded in ANDs
    (lambda q: q.query("def", q.Q("abc"), q.Q(), q.Q(q.Q() & q.Q("xyz"))),
     [('q', b'abc AND def AND xyz')]),
    # Make sure that empty queries are discarded in ORs
    (lambda q: q.query(q.Q() | q.Q("def") | q.Q(q.Q() | q.Q("xyz"))),
     [('q', b'def OR xyz')]),
    # Test cancellation of NOTs.
    (lambda q: q.query(~q.Q(~q.Q("def"))),
     [('q', b'def')]),
    (lambda q: q.query(~q.Q(~q.Q(~q.Q("def")))),
     [('q', b'NOT def')]),
    # Test it works through sub-sub-queries
    (lambda q: q.query(~q.Q(q.Q(q.Q(~q.Q(~q.Q("def")))))),
     [('q', b'NOT def')]),
    # Even with empty queries in there
    (lambda q: q.query(~q.Q(q.Q(q.Q() & q.Q(q.Q() | ~q.Q(~q.Q("def")))))),
     [('q', b'NOT def')]),
    # Test escaping of AND, OR, NOT
    (lambda q: q.query("AND", "OR", "NOT"),
     [('q', b'"AND" AND "NOT" AND "OR"')]),
    # Test exclude
    (lambda q: q.query("blah").query(~q.Q(q.Q("abc") | q.Q("def") | q.Q("ghi"))),
     [('q', b'blah AND NOT (abc OR def OR ghi)')]),
    # Try boosts
    (lambda q: q.query("blah").query(q.Q("def") ** 1.5),
     [('q', b'blah AND def^1.5')]),
    (lambda q: q.query("blah").query((q.Q("def") | q.Q("ghi")) ** 1.5),
     [('q', b'blah AND (def OR ghi)^1.5')]),
    (lambda q: q.query("blah").query(q.Q("def", ~q.Q("pqr") | q.Q("mno")) ** 1.5),
     [('q', b'blah AND (def AND ((*:* AND NOT pqr) OR mno))^1.5')]),
    # wildcard
    (lambda q: q.query("blah").query(q.Q(WildcardString("def*"),
                                         ~q.Q(miu=WildcardString("pqr*")) | q.Q("mno")) ** 1.5),
     [('q', b'blah AND (def* AND ((*:* AND NOT miu:pqr*) OR mno))^1.5')]),
    (lambda q: q.query("blah").query(q.Q("def*", ~q.Q(miu="pqr*") | q.Q("mno")) ** 1.5),
     [('q', b'blah AND (def\\* AND ((*:* AND NOT miu:pqr\\*) OR mno))^1.5')]),
    # And boost_relevancy
    (lambda q: q.query("blah").boost_relevancy(1.5, int_field=3),
     [('q', b'blah OR (blah AND int_field:3^1.5)')]),
    (lambda q: q.query("blah").boost_relevancy(1.5, int_field=3).boost_relevancy(2, string_field='def'),
     [('q', b'blah OR (blah AND (int_field:3^1.5 OR string_field:def^2))')]),
    (lambda q: q.query("blah").query("blah2").boost_relevancy(1.5, int_field=3),
     [('q', b'(blah AND blah2) OR (blah AND blah2 AND int_field:3^1.5)')]),
    (lambda q: q.query(q.Q("blah") | q.Q("blah2")).boost_relevancy(1.5, int_field=3),
     [('q', b'blah OR blah2 OR ((blah OR blah2) AND int_field:3^1.5)')]),
    # And ranges
    (lambda q: q.query(int_field__any=True),
     [('q', b'int_field:[* TO *]')]),
    (lambda q: q.query("blah", ~q.Q(int_field__any=True)),
     [('q', b'blah AND NOT int_field:[* TO *]')]),
    # facet
    (lambda q: q.query("game").facet_query(price__lt=7).facet_query(price__gte=7),
     [('facet', b'true'), ('facet.query', b'price:[7 TO *]'),
      ('facet.query', b'price:{* TO 7}'), ('q', b'game')]),
    # group
    (lambda q: q.query().group_by('major_value', limit=10),
     [('group', b'true'), ('group.field', b'major_value'), ('group.limit', b'10'),
      ('group.ngroups', b'true'), ('q', b'*:*')]),
    # highlight
    (lambda q: q.query("hello world").filter(q.Q(text_field="tow")).highlight('title'),
     [('fq', b'text_field:tow'), ('hl', b'true'), ('hl.fl', b'title'), ('q', b'hello\\ world')]),
    # termVector
    (lambda q: q.query("hello world").filter(q.Q(text_field="tow")).term_vector(df=True),
     [('fq', b'text_field:tow'), ('tv', b'true'), ('tv.df', b'true'), ('q', b'hello\\ world')]),
    # sort
    (lambda q: q.query("hello world").filter(q.Q(text_field="tow")).sort_by('title'),
     [('fq', b'text_field:tow'), ('q', b'hello\\ world'), ('sort', b'title asc')]),
    # dismax
    (lambda q: q.query("hello").filter(q.Q(text_field="tow")).alt_parser(
        "dismax", qf={"text_field": 0.25, "string_field": 0.75}),
     [('defType', b'dismax'), ('fq', b'text_field:tow'), ('q', b'hello'),
      ('qf', b'text_field^0.25 string_field^0.75')]),
    # edismax
    (lambda q: q.query("hello").filter(q.Q(text_field="tow")).alt_parser(
        "edismax", qf={"text_field": 0.25, "string_field": 0.75},
        f={'alias1':['field1', 'field2']}
        ),
     [('defType', b'edismax'), ('fq', b'text_field:tow'), ('q', b'hello'),
      ('qf', b'text_field^0.25 string_field^0.75'),
      ('f.alias1.qf', b'field1 field2')]),
    # field_limit
    (lambda q: q.query().field_limit(['name', 'foo']),
     [('fl', b'foo,name'), ('q', b'*:*')]),
    (lambda q: q.query().field_limit('foo'),
     [('fl', b'foo'), ('q', b'*:*')]),
    # set_requesthandler
    (lambda q: q.query("hello").set_requesthandler("foo"),
     [('q', b'hello'), ('qt', b'foo')]),
    # debug
    (lambda q: q.query("hello").debug(),
     [('debugQuery', b'true'), ('q', b'hello')]),
)


def check_complex_boolean_query(solr_search, query, output):
    p = query(solr_search).params()
    assert set(p) == set(output), "Unequal: %r, %r" % (p, output)
    # And check no mutation of the base object
    q = query(solr_search).params()
    assert p == q, "Unequal: %r, %r" % (p, q)


param_encode_data = (
    ({"int": 3, "string": "string", "unicode": u"unicode"},
     [("int", b"3"), ("string", b"string"), ("unicode", b"unicode")]),
    ({"int": 3, "string": "string", "unicode": u"\N{UMBRELLA}nicode"},
     [("int", b"3"), ("string", b"string"), ("unicode", b"\xe2\x98\x82nicode")]),
    # python3 needs unicode as keys
    ({"int": 3, "string": "string", u"\N{UMBRELLA}nicode": u"\N{UMBRELLA}nicode"},
     [("int", b"3"), ("string", b"string"), (u"\N{UMBRELLA}nicode", b"\xe2\x98\x82nicode")]),
    ({"true": True, "false": False},
     [("false", b"false"), ("true", b"true")]),
    ({"list": ["first", "second", "third"]},
     [("list", b"first"), ("list", b"second"), ("list", b"third")]),
)


def check_url_encode_data(kwargs, output):
    p = params_from_dict(**kwargs)
    assert p == output, "Unequal: %r, %r" % (p, output)

mlt_query_options_data = (
    ('text_field', {}, {},
     [('mlt.fl', b'text_field'), ('q', b'*:*')]),
    (['string_field', 'text_field'], {'string_field': 3.0}, {},
     [('mlt.fl', b'string_field,text_field'), ('mlt.qf', b'string_field^3.0'),
      ('q', b'*:*')]),
    ('text_field', {}, {'mindf': 3, 'interestingTerms': 'details'},
     [('mlt.fl', b'text_field'), ('mlt.interestingTerms', b'details'),
      ('mlt.mindf', b'3'), ('q', b'*:*')]),
)


def check_mlt_query_options(fields, query_fields, kwargs, output):
    q = MltSolrSearch(None, content="This is the posted content.")
    q = q.mlt(fields, query_fields=query_fields, **kwargs)
    assert_equal(q.params(), output)


def test_query_data():
    for method, data in list(good_query_data.items()):
        for args, kwargs, output in data:
            yield check_query_data, method, args, kwargs, output


def test_mlt_query_data():
    for method, data in list(base_good_query_data.items()):
        for args, kwargs, output in data:
            yield check_mlt_query_data, method, args, kwargs, output


def test_good_option_data():
    for OptionClass, option_data in list(good_option_data.items()):
        for kwargs, output in option_data:
            yield check_good_option_data, OptionClass, kwargs, output


def test_bad_option_data():
    for OptionClass, option_data in list(bad_option_data.items()):
        for kwargs in option_data:
            yield check_bad_option_data, OptionClass, kwargs


def test_complex_boolean_queries():
    solr_search = SolrSearch(None)
    for query, output in complex_boolean_queries:
        yield check_complex_boolean_query, solr_search, query, output


def test_url_encode_data():
    for kwargs, output in param_encode_data:
        yield check_url_encode_data, kwargs, output


def test_mlt_query_options():
    for (fields, query_fields, kwargs, output) in mlt_query_options_data:
        yield check_mlt_query_options, fields, query_fields, kwargs, output


def test_is_iter():
    assert is_iter("abc") == False
    assert is_iter(1) == False
    assert is_iter([1, 2]) == True
    assert is_iter((1, 2)) == True
    assert is_iter(set([1, 2])) == True
