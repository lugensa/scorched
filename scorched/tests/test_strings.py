import unittest
from scorched.strings import (RawString, WildcardString)
from scorched.search import LuceneQuery


class TestStrings(unittest.TestCase):

    def test_string_escape(self):
        """ Ensure that string characters are escaped correctly for Solr queries.
        """
        test_str = '+-&|!(){}[]^"~*?: \t\v\\/'
        escaped = RawString(test_str).escape_for_lqs_term()
        self.assertEqual(
            escaped,
            '\\+\\-\\&\\|\\!\\(\\)\\{\\}\\[\\]\\^\\"\\~\\*\\?\\:\\ \\\t\\\x0b\\\\\\/')

    def test_wildcard_string(self):
        q = LuceneQuery()
        q = q.Q(WildcardString('occurrencetype$$pressemitteilung$$*'))
        output = {None: 'occurrencetype$$pressemitteilung$$*'}
        self.assertEqual(q.options(), output,
                         "Unequal: %r, %r" % (q.options(), output))
        # slash
        q = q.Q(WildcardString('occu/*/baum'))
        output = {None: 'occu\\/*\\/baum'}
        self.assertEqual(q.options(), output,
                         "Unequal: %r, %r" % (q.options(), output))
        # backslash
        q = q.Q(WildcardString('occu\*baum\?aus\\'))
        output = {None: 'occu\\*baum\\?aus\\\\'}
        self.assertEqual(q.options(), output,
                         "Unequal: %r, %r" % (q.options(), output))
        # question mark
        q = q.Q(WildcardString('occ?/*/baum'))
        output = {None: 'occ?\\/*\\/baum'}
        self.assertEqual(q.options(), output,
                         "Unequal: %r, %r" % (q.options(), output))
