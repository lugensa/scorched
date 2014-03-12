import datetime
import collections
import copy
import operator
import re
try:
    import mx.DateTime
    HAS_MX_DATETIME = True
except ImportError:
    HAS_MX_DATETIME = False
import numbers
import scorched.strings

from scorched.dates import solr_date
from scorched.exc import SolrError

PARSERS = ("edismax", "dismax")


class LuceneQuery(object):

    default_term_re = re.compile(r'^\w+$')

    def __init__(self, option_flag=None, original=None,
                 multiple_tags_allowed=False):
        self.normalized = False
        if original is None:
            self.option_flag = option_flag
            self.multiple_tags_allowed = multiple_tags_allowed
            self.terms = collections.defaultdict(set)
            self.phrases = collections.defaultdict(set)
            self.ranges = set()
            self.subqueries = []
            self._and = True
            self._or = self._not = self._pow = False
            self.boosts = []
        else:
            self.option_flag = original.option_flag
            self.multiple_tags_allowed = original.multiple_tags_allowed
            self.terms = copy.copy(original.terms)
            self.phrases = copy.copy(original.phrases)
            self.ranges = copy.copy(original.ranges)
            self.subqueries = copy.copy(original.subqueries)
            self._or = original._or
            self._and = original._and
            self._not = original._not
            self._pow = original._pow
            self.boosts = copy.copy(original.boosts)

    def clone(self):
        return LuceneQuery(original=self)

    def options(self):
        opts = {}
        s = self.__unicode_special__()
        if s:
            opts[self.option_flag] = s
        return opts

    # Below, we sort all our value_sets - this is for predictability when
    # testing.
    def serialize_term_queries(self, terms):
        s = []
        for name, value_set in terms.items():
            if name:
                tmp = [u'%s:%s' % (name, self.to_query(value))
                       for value in value_set]
                if name == '*':
                    tmp = [u'%s:%s' % (name, value)
                           for value in value_set]
                s += tmp
            else:
                s += [self.to_query(value) for value in value_set]
        return sorted(s)

    def to_solr(self, value):
        if isinstance(value, bool):
            return u"true" if value else u"false"
        if HAS_MX_DATETIME:
            if isinstance(value, mx.DateTime.DateTimeType):
                return unicode(solr_date(value))
        if isinstance(value, datetime.datetime):
            return unicode(solr_date(value))
        return unicode(value)

    def to_query(self, value):
        ret = scorched.strings.RawString(
            self.to_solr(value)).escape_for_lqs_term()
        if isinstance(value, scorched.strings.WildcardString):
            ret = value.escape_for_lqs_term()
        return ret

    range_query_templates = {
        "any": u"[* TO *]",
        "lt": u"{* TO %s}",
        "lte": u"[* TO %s]",
        "gt": u"{%s TO *}",
        "gte": u"[%s TO *]",
        "rangeexc": u"{%s TO %s}",
        "range": u"[%s TO %s]",
    }

    def serialize_range_queries(self):
        s = []
        for name, rel, values in sorted(self.ranges):
            range_s = self.range_query_templates[rel]
            if values:
                values = values[0]
                if not hasattr(values, "__iter__"):
                    values = [values]
                values = sorted(values)
                values = [self.to_query(v) for v in values]
                range_s = self.range_query_templates[rel] % tuple(
                    values)
            s.append(u"%s:%s" % (name, range_s))
        return s

    def child_needs_parens(self, child):
        if len(child) == 1:
            return False
        elif self._or:
            return not (child._or or child._pow)
        elif (self._and or self._not):
            return not (child._and or child._not or child._pow)
        elif self._pow is not False:
            return True
        else:
            return True

    @staticmethod
    def merge_term_dicts(*args):
        d = collections.defaultdict(set)
        for arg in args:
            for k, v in arg.items():
                d[k].update(v)
        return dict((k, v) for k, v in d.items())

    def normalize(self):
        if self.normalized:
            return self, False
        mutated = False
        _subqueries = []
        _terms = self.terms
        _phrases = self.phrases
        _ranges = self.ranges
        for s in self.subqueries:
            _s, changed = s.normalize()
            if not _s or changed:
                mutated = True
            if _s:
                if (_s._and and self._and) or (_s._or and self._or):
                    mutated = True
                    _terms = self.merge_term_dicts(_terms, _s.terms)
                    _phrases = self.merge_term_dicts(_phrases, _s.phrases)
                    _ranges = _ranges.union(_s.ranges)
                    _subqueries.extend(_s.subqueries)
                else:
                    _subqueries.append(_s)
        if mutated:
            newself = self.clone()
            newself.terms = _terms
            newself.phrases = _phrases
            newself.ranges = _ranges
            newself.subqueries = _subqueries
            self = newself

        if self._not:
            if not len(self.subqueries):
                newself = self.clone()
                newself._not = False
                newself._and = True
                self = newself
                mutated = True
            elif len(self.subqueries) == 1:
                if self.subqueries[0]._not:
                    newself = self.clone()
                    newself.subqueries = self.subqueries[0].subqueries
                    newself._not = False
                    newself._and = True
                    self = newself
                    mutated = True
            else:
                raise ValueError
        elif self._pow:
            if not len(self.subqueries):
                newself = self.clone()
                newself._pow = False
                self = newself
                mutated = True
        elif self._and or self._or:
            if not self.terms and not self.phrases and not self.ranges \
               and not self.boosts:
                if len(self.subqueries) == 1:
                    self = self.subqueries[0]
                    mutated = True
        self.normalized = True
        return self, mutated

    def __unicode__(self):
        return self.__unicode_special__(force_serialize=True)

    def __unicode_special__(self, level=0, op=None, force_serialize=False):
        if not self.normalized:
            self, _ = self.normalize()
        if self.boosts:
            # Clone and rewrite to effect the boosts.
            newself = self.clone()
            newself.boosts = []
            boost_queries = [self.Q(**kwargs) ** boost_score
                             for kwargs, boost_score in self.boosts]
            newself = newself | (newself & reduce(operator.or_, boost_queries))
            newself, _ = newself.normalize()
            return newself.__unicode_special__(level=level, force_serialize=force_serialize)
        else:
            alliter = [self.serialize_term_queries(self.terms),
                       self.serialize_term_queries(self.phrases),
                       self.serialize_range_queries()]
            u = []
            for iterator in alliter:
                u.extend(iterator)
            for q in self.subqueries:
                op_ = u'OR' if self._or else u'AND'
                if self.child_needs_parens(q):
                    u.append(
                        u"(%s)" % q.__unicode_special__(level=level + 1, op=op_))
                else:
                    u.append(
                        u"%s" % q.__unicode_special__(level=level + 1, op=op_))
            if self._and:
                if (not force_serialize and
                    level == 0 and
                        self.multiple_tags_allowed):
                    return u
                else:
                    return u' AND '.join(u)
            elif self._or:
                return u' OR '.join(u)
            elif self._not:
                assert len(u) == 1
                if level == 0 or (level == 1 and op == "AND"):
                    return u'NOT %s' % u[0]
                else:
                    return u'(*:* AND NOT %s)' % u[0]
            elif self._pow is not False:
                assert len(u) == 1
                return u"%s^%s" % (u[0], self._pow)
            else:
                raise ValueError

    def __len__(self):
        # How many terms in this (sub) query?
        if len(self.subqueries) == 1:
            subquery_length = len(self.subqueries[0])
        else:
            subquery_length = len(self.subqueries)
        return sum([sum(len(v) for v in self.terms.values()),
                    sum(len(v) for v in self.phrases.values()),
                    len(self.ranges),
                    subquery_length])

    def Q(self, *args, **kwargs):
        q = LuceneQuery()
        q.add(args, kwargs)
        return q

    def __nonzero__(self):
        return bool(self.terms) or bool(self.phrases) or bool(self.ranges) or bool(self.subqueries)

    def __or__(self, other):
        q = LuceneQuery()
        q._and = False
        q._or = True
        q.subqueries = [self, other]
        return q

    def __and__(self, other):
        q = LuceneQuery()
        q.subqueries = [self, other]
        return q

    def __invert__(self):
        q = LuceneQuery()
        q._and = False
        q._not = True
        q.subqueries = [self]
        return q

    def __pow__(self, value):
        try:
            float(value)
        except ValueError:
            raise ValueError("Non-numeric value supplied for boost")
        q = LuceneQuery()
        q.subqueries = [self]
        q._and = False
        q._pow = value
        return q

    def add(self, args, kwargs):
        self.normalized = False
        _args = []
        for arg in args:
            if isinstance(arg, LuceneQuery):
                self.subqueries.append(arg)
            else:
                _args.append(arg)
        args = _args
        try:
            terms_or_phrases = kwargs.pop("__terms_or_phrases")
        except KeyError:
            terms_or_phrases = None
        for value in args:
            self.add_exact(None, value, terms_or_phrases)
        for k, v in kwargs.items():
            try:
                field_name, rel = k.split("__")
            except ValueError:
                field_name, rel = k, 'eq'
            if not field_name:
                if (k, v) != ("*", "*"):
                    # the only case where wildcards in field names are allowed
                    raise ValueError("%s is not a valid field name" % k)
            if rel == 'eq':
                self.add_exact(field_name, v, terms_or_phrases)
            else:
                self.add_range(field_name, rel, v)

    def add_exact(self, field_name, values, term_or_phrase):
        # We let people pass in a list of values to match.
        # This really only makes sense for text fields or
        # multivalued fields.
        if not hasattr(values, "__iter__"):
            values = [values]
        # We can only do a field_name == "*" if:
        if not field_name or field_name == "*":
            if len(values) == 1 and values[0] == "*":
                self.terms["*"].add("*")
                return
        insts = values
        for inst in insts:
            this_term_or_phrase = term_or_phrase or self.term_or_phrase(inst)
            if isinstance(inst, numbers.Number):
                this_term_or_phrase = 'terms'
            getattr(self, this_term_or_phrase)[field_name].add(inst)

    def add_range(self, field_name, rel, value):
        if rel not in self.range_query_templates:
            raise SolrError("No such relation '%s' defined" % rel)
        insts = (value,)
        if rel in ('range', 'rangeexc'):
            try:
                assert len(value) == 2
            except (AssertionError, TypeError):
                raise SolrError("'%s__%s' argument must be a length-2 iterable"
                                % (field_name, rel))
        elif rel == 'any':
            if value is not True:
                raise SolrError("'%s__%s' argument must be True")
            insts = ()
        self.ranges.add((field_name, rel, insts))

    def term_or_phrase(self, arg, force=None):
        return 'terms' if self.default_term_re.match(str(arg)) else 'phrases'

    def add_boost(self, kwargs, boost_score):
        self.boosts.append((kwargs, boost_score))


class BaseSearch(object):

    """Base class for common search options management"""
    option_modules = ('query_obj', 'filter_obj', 'paginator',
                      'more_like_this', 'highlighter', 'faceter',
                      'grouper', 'sorter', 'facet_querier', 'field_limiter',
                      'parser')

    def _init_common_modules(self):
        self.query_obj = LuceneQuery(u'q')
        self.filter_obj = LuceneQuery(u'fq',
                                      multiple_tags_allowed=True)
        self.paginator = PaginateOptions()
        self.highlighter = HighlightOptions()
        self.faceter = FacetOptions()
        self.grouper = GroupOptions()
        self.sorter = SortOptions()
        self.field_limiter = FieldLimitOptions()
        self.facet_querier = FacetQueryOptions()

    def clone(self):
        return self.__class__(interface=self.interface, original=self)

    def Q(self, *args, **kwargs):
        q = LuceneQuery()
        q.add(args, kwargs)
        return q

    def query(self, *args, **kwargs):
        newself = self.clone()
        newself.query_obj.add(args, kwargs)
        return newself

    def query_by_term(self, *args, **kwargs):
        return self.query(__terms_or_phrases="terms", *args, **kwargs)

    def query_by_phrase(self, *args, **kwargs):
        return self.query(__terms_or_phrases="phrases", *args, **kwargs)

    def exclude(self, *args, **kwargs):
        # cloning will be done by query
        return self.query(~self.Q(*args, **kwargs))

    def boost_relevancy(self, boost_score, **kwargs):
        if not self.query_obj:
            raise TypeError("Can't boost the relevancy of an empty query")
        try:
            float(boost_score)
        except ValueError:
            raise ValueError("Non-numeric boost value supplied")

        newself = self.clone()
        newself.query_obj.add_boost(kwargs, boost_score)
        return newself

    def filter(self, *args, **kwargs):
        newself = self.clone()
        newself.filter_obj.add(args, kwargs)
        return newself

    def filter_by_term(self, *args, **kwargs):
        return self.filter(__terms_or_phrases="terms", *args, **kwargs)

    def filter_by_phrase(self, *args, **kwargs):
        return self.filter(__terms_or_phrases="phrases", *args, **kwargs)

    def filter_exclude(self, *args, **kwargs):
        # cloning will be done by filter
        return self.filter(~self.Q(*args, **kwargs))

    def facet_by(self, field, **kwargs):
        newself = self.clone()
        newself.faceter.update(field, **kwargs)
        return newself

    def group_by(self, field, **kwargs):
        newself = self.clone()
        kwargs['field'] = field

        if 'ngroups' not in kwargs:
            kwargs['ngroups'] = True

        newself.grouper.update(None, **kwargs)
        return newself

    def facet_query(self, *args, **kwargs):
        newself = self.clone()
        newself.facet_querier.update(self.Q(*args, **kwargs))
        return newself

    def highlight(self, fields=None, **kwargs):
        newself = self.clone()
        newself.highlighter.update(fields, **kwargs)
        return newself

    def mlt(self, fields, query_fields=None, **kwargs):
        newself = self.clone()
        newself.more_like_this.update(fields, query_fields, **kwargs)
        return newself

    def alt_parser(self, parser, **kwargs):
        if parser not in PARSERS:
            raise SolrError("Parser (%s) is not supported choose between (%s)"
                            % (parser, PARSERS))
        newself = self.clone()
        if parser == 'dismax':
            newself.parser = DismaxOptions()
        elif parser == 'edismax':
            newself.parser = EdismaxOptions()
        newself.parser.update(**kwargs)
        return newself

    def paginate(self, start=None, rows=None):
        newself = self.clone()
        newself.paginator.update(start, rows)
        return newself

    def sort_by(self, field):
        newself = self.clone()
        newself.sorter.update(field)
        return newself

    def field_limit(self, fields=None, score=False, all_fields=False):
        newself = self.clone()
        newself.field_limiter.update(fields, score, all_fields)
        return newself

    def field_limit_exclude(self, exclude=None, score=False, all_fields=False,
                            default_fields=[]):
        newself = self.clone()
        if exclude is None:
            exclude = []
        if isinstance(exclude, basestring):
            exclude = [exclude]
        fields = list(set(default_fields) - set(exclude))
        newself.field_limiter.update(fields, score, all_fields)
        return newself

    def options(self):
        options = {}
        for option_module in self.option_modules:
            if hasattr(self, option_module):
                _attr = getattr(self, option_module)
                options.update(_attr.options())
        # Next line is for pre-2.6.5 python
        return dict((k.encode('utf8'), v) for k, v in options.items())

    def results_as(self, constructor):
        newself = self.clone()
        return newself

    def params(self):
        return params_from_dict(**self.options())

    def constructor(self, result, constructor):
        construct_docs = lambda docs: [constructor(**d) for d in docs]
        result.result.docs = construct_docs(result.result.docs)
        for key in result.more_like_these:
            result.more_like_these[key].docs = construct_docs(
                result.more_like_these[key].docs)
        return result


class SolrSearch(BaseSearch):

    def __init__(self, interface, original=None):
        self.interface = interface
        if original is None:
            self.more_like_this = MoreLikeThisOptions()
            self._init_common_modules()
        else:
            for opt in self.option_modules:
                if hasattr(original, opt):
                    _attr = getattr(original, opt)
                    setattr(self, opt, _attr.clone())

    def options(self):
        options = super(SolrSearch, self).options()
        if 'q' not in options:
            options['q'] = '*:*'  # search everything
        return options

    def execute(self, constructor=None):
        ret = self.interface.search(**self.options())
        if constructor:
            ret = self.constructor(ret, constructor)
        return ret


class MltSolrSearch(BaseSearch):

    """Manage parameters to build a MoreLikeThisHandler query"""
    trivial_encodings = [
        "utf_8", "u8", "utf", "utf8", "ascii", "646", "us_ascii"]

    def __init__(self, interface, content=None, content_charset=None, url=None,
                 original=None):
        self.interface = interface
        if original is None:
            if content is not None and url is not None:
                raise ValueError(
                    "Cannot specify both content and url")
            if content is not None:
                if content_charset is None:
                    content_charset = 'utf-8'
                if isinstance(content, unicode):
                    content = content.encode('utf-8')
                elif content_charset.lower().replace('-', '_') not in self.trivial_encodings:
                    content = content.decode(content_charset).encode('utf-8')
            self.content = content
            self.url = url
            self.more_like_this = MoreLikeThisHandlerOptions()
            self._init_common_modules()
        else:
            self.content = original.content
            self.url = original.url
            for opt in self.option_modules:
                if hasattr(original, opt):
                    _attr = getattr(original, opt)
                    setattr(self, opt, _attr.clone())

    def query(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).query(*args, **kwargs)

    def query_by_term(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).query_by_term(*args, **kwargs)

    def query_by_phrase(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).query_by_phrase(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).exclude(*args, **kwargs)

    def Q(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).Q(*args, **kwargs)

    def boost_relevancy(self, *args, **kwargs):
        if self.content is not None or self.url is not None:
            raise ValueError(
                "Cannot specify query as well as content on an MltSolrSearch")
        return super(MltSolrSearch, self).boost_relevancy(*args, **kwargs)

    def options(self):
        options = super(MltSolrSearch, self).options()
        if self.url is not None:
            options['stream.url'] = self.url
        return options

    def execute(self, constructor=None):
        ret = self.interface.mlt_search(content=self.content, **self.options())
        if constructor:
            ret = self.constructor(ret, constructor)
        return ret


class Options(object):

    def clone(self):
        return self.__class__(self)

    def invalid_value(self, msg=""):
        assert False, msg

    def update(self, fields=None, **kwargs):
        if fields:
            if isinstance(fields, basestring):
                fields = [fields]
            for field in set(fields) - set(self.fields):
                self.fields[field] = {}
        elif kwargs:
            fields = [None]
        checked_kwargs = self.check_opts(kwargs)
        for k, v in checked_kwargs.items():
            for field in fields:
                self.fields[field][k] = v

    def check_opts(self, kwargs):
        checked_kwargs = {}
        for k, v in kwargs.items():
            if k not in self.opts:
                raise SolrError(
                    "No such option for %s: %s" % (self.option_name, k))
            opt_type = self.opts[k]
            try:
                if isinstance(opt_type, (list, tuple)):
                    assert v in opt_type
                elif isinstance(opt_type, type):
                    v = opt_type(v)
                else:
                    v = opt_type(self, v)
            except:
                raise SolrError(
                    "Invalid value for %s option %s: %s" % (self.option_name,
                                                            k, v))
            checked_kwargs[k] = v
        return checked_kwargs

    def options(self):
        opts = {}
        if self.fields:
            opts[self.option_name] = True
            fields = [field for field in self.fields if field]
            self.field_names_in_opts(opts, fields)
        for field_name, field_opts in self.fields.items():
            if not field_name:
                for field_opt, v in field_opts.items():
                    opts['%s.%s' % (self.option_name, field_opt)] = v
            else:
                for field_opt, v in field_opts.items():
                    opts['f.%s.%s.%s' %
                         (field_name, self.option_name, field_opt)] = v
        return opts


class FacetOptions(Options):
    option_name = "facet"
    opts = {"prefix": unicode,
            "sort": [True, False, "count", "index"],
            "limit": int,
            "offset": lambda self, x: int(x) >= 0 and int(x) or self.invalid_value(),
            "mincount": lambda self, x: int(x) >= 0 and int(x) or self.invalid_value(),
            "missing": bool,
            "method": ["enum", "fc"],
            "enum.cache.minDf": int,
            }

    def __init__(self, original=None):
        if original is None:
            self.fields = collections.defaultdict(dict)
        else:
            self.fields = copy.copy(original.fields)

    def field_names_in_opts(self, opts, fields):
        if fields:
            opts["facet.field"] = sorted(fields)


class GroupOptions(Options):
    option_name = "group"
    opts = {
        "field": unicode,
        "limit": int,
        "main": bool,
        "ngroups": bool
    }

    def __init__(self, original=None):
        if original is None:
            self.fields = collections.defaultdict(dict)
        else:
            self.fields = copy.copy(original.fields)

    def field_names_in_opts(self, opts, fields):
        if fields:
            opts["facet.field"] = sorted(fields)


class DismaxOptions(Options):
    _name = "dismax"
    option_name = "defType"
    opts = {
        "qf": dict,
        "mm": int,
        "pf": dict,
        "ps": int,
        "qs": int,
        "tie": float,
        "bq": unicode,
        "bf": unicode,
    }

    def __init__(self, original=None):
        if original is None:
            self.kwargs = {}
        else:
            self.kwargs = original.kwargs.copy()

    def update(self, **kwargs):
        checked_kwargs = self.check_opts(kwargs)
        for f in ('qf', 'pf'):
            field = kwargs.get(f, {})
            for k, v in field.items():
                if v is not None:
                    try:
                        v = float(v)
                    except ValueError:
                        raise SolrError(
                            "'%s' has non-numerical boost value" % k)
        self.kwargs.update(checked_kwargs)

    def options(self):
        opts = {}
        opts[self.option_name] = self._name
        for opt_name, opt_value in self.kwargs.items():
            opt_type = self.opts[opt_name]
            opts[opt_name] = opt_type(opt_value)

            if opt_name in ("qf", "pf"):
                qf_arg = []
                for k, v in opt_value.items():
                    if v is None:
                        qf_arg.append(k)
                    else:
                        qf_arg.append("%s^%s" % (k, float(v)))
                opts[opt_name] = " ".join(qf_arg)
        return opts


class EdismaxOptions(DismaxOptions):
    _name = "edismax"


class HighlightOptions(Options):
    option_name = "hl"
    opts = {"snippets": int,
            "fragsize": int,
            "mergeContinuous": bool,
            "requireFieldMatch": bool,
            "maxAnalyzedChars": int,
            "alternateField": unicode,
            "maxAlternateFieldLength": int,
            "formatter": ["simple"],
            "simple.pre": unicode,
            "simple.post": unicode,
            "fragmenter": unicode,
            "useFastVectorHighlighter": bool,  # available as of Solr 3.1
            "usePhraseHighlighter": bool,
            "highlightMultiTerm": bool,
            "regex.slop": float,
            "regex.pattern": unicode,
            "regex.maxAnalyzedChars": int
            }

    def __init__(self, original=None):
        if original is None:
            self.fields = collections.defaultdict(dict)
        else:
            self.fields = copy.copy(original.fields)

    def field_names_in_opts(self, opts, fields):
        if fields:
            opts["hl.fl"] = ",".join(sorted(fields))


class MoreLikeThisOptions(Options):
    option_name = "mlt"
    opts = {"count": int,
            "mintf": int,
            "mindf": int,
            "minwl": int,
            "maxwl": int,
            "maxqt": int,
            "maxntp": int,
            "boost": bool,
            }

    def __init__(self, original=None):
        if original is None:
            self.fields = set()
            self.query_fields = {}
            self.kwargs = {}
        else:
            self.fields = copy.copy(original.fields)
            self.query_fields = copy.copy(original.query_fields)
            self.kwargs = copy.copy(original.kwargs)

    def update(self, fields, query_fields=None, **kwargs):
        if fields is None:
            return
        if isinstance(fields, basestring):
            fields = [fields]
        self.fields.update(fields)

        if query_fields is not None:
            for k, v in query_fields.items():
                if k not in self.fields:
                    raise SolrError(
                        "'%s' specified in query_fields but not fields" % k)
                if v is not None:
                    try:
                        v = float(v)
                    except ValueError:
                        raise SolrError(
                            "'%s' has non-numerical boost value" % k)
            self.query_fields.update(query_fields)

        checked_kwargs = self.check_opts(kwargs)
        self.kwargs.update(checked_kwargs)

    def options(self):
        opts = {}
        if self.fields:
            opts['mlt'] = True
            opts['mlt.fl'] = ','.join(sorted(self.fields))

        if self.query_fields:
            qf_arg = []
            for k, v in self.query_fields.items():
                if v is None:
                    qf_arg.append(k)
                else:
                    qf_arg.append("%s^%s" % (k, float(v)))
            opts["mlt.qf"] = " ".join(qf_arg)

        for opt_name, opt_value in self.kwargs.items():
            opt_type = self.opts[opt_name]
            opts["mlt.%s" % opt_name] = opt_type(opt_value)

        return opts


class MoreLikeThisHandlerOptions(MoreLikeThisOptions):
    opts = {'match.include': bool,
            'match.offset': int,
            'interestingTerms': ["list", "details", "none"],
            }
    opts.update(MoreLikeThisOptions.opts)
    del opts['count']

    def options(self):
        opts = {}
        if self.fields:
            opts['mlt.fl'] = ','.join(sorted(self.fields))

        if self.query_fields:
            qf_arg = []
            for k, v in self.query_fields.items():
                if v is None:
                    qf_arg.append(k)
                else:
                    qf_arg.append("%s^%s" % (k, float(v)))
            opts["mlt.qf"] = " ".join(qf_arg)

        for opt_name, opt_value in self.kwargs.items():
            opts["mlt.%s" % opt_name] = opt_value

        return opts


class PaginateOptions(Options):

    def __init__(self, original=None):
        if original is None:
            self.start = None
            self.rows = None
        else:
            self.start = original.start
            self.rows = original.rows

    def update(self, start, rows):
        if start is not None:
            if start < 0:
                raise SolrError("paginator start index must be 0 or greater")
            self.start = start
        if rows is not None:
            if rows < 0:
                raise SolrError("paginator rows must be 0 or greater")
            self.rows = rows

    def options(self):
        opts = {}
        if self.start is not None:
            opts['start'] = self.start
        if self.rows is not None:
            opts['rows'] = self.rows
        return opts


class SortOptions(Options):
    option_name = "sort"

    def __init__(self, original=None):
        if original is None:
            self.fields = []
        else:
            self.fields = copy.copy(original.fields)

    def update(self, field):
        # We're not allowing function queries a la Solr1.5
        if field.startswith('-'):
            order = "desc"
            field = field[1:]
        elif field.startswith('+'):
            order = "asc"
            field = field[1:]
        else:
            order = "asc"
        self.fields.append([order, field])

    def options(self):
        if self.fields:
            return {"sort": ", ".join("%s %s" % (field, order) for order, field in self.fields)}
        else:
            return {}


class FieldLimitOptions(Options):
    option_name = "fl"

    def __init__(self, original=None):
        if original is None:
            self.fields = set()
            self.score = False
            self.all_fields = False
        else:
            self.fields = copy.copy(original.fields)
            self.score = original.score
            self.all_fields = original.all_fields

    def update(self, fields=None, score=False, all_fields=False):
        if fields is None:
            fields = []
        if isinstance(fields, basestring):
            fields = [fields]
        self.fields.update(fields)
        self.score = score
        self.all_fields = all_fields

    def options(self):
        opts = {}
        if self.all_fields:
            fields = set("*")
        else:
            fields = self.fields
        if self.score:
            fields.add("score")
        if fields:
            opts['fl'] = ','.join(sorted(fields))
        return opts


class FacetQueryOptions(Options):

    def __init__(self, original=None):
        if original is None:
            self.queries = []
        else:
            self.queries = [q.clone() for q in original.queries]

    def update(self, query):
        self.queries.append(query)

    def options(self):
        if self.queries:
            return {'facet.query': [unicode(q) for q in self.queries],
                    'facet': True}
        else:
            return {}


def params_from_dict(**kwargs):
    utf8_params = []
    for k, vs in kwargs.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        # We allow for multivalued options with lists.
        if not hasattr(vs, "__iter__"):
            vs = [vs]
        for v in vs:
            if isinstance(v, bool):
                v = u"true" if v else u"false"
            else:
                v = unicode(v)
            v = v.encode('utf-8')
            utf8_params.append((k, v))
    return sorted(utf8_params)
