import binascii
import doctest
import unittest
import yuri

def hexed(s):
    return '%' + binascii.hexlify(s).upper()

class EncodingTests(unittest.TestCase):

    def test_unreserved_characters(self):
        result = yuri.encode(yuri.unreserved_characters, query=False)
        self.assertEqual(result, yuri.unreserved_characters)

        result = yuri.encode(yuri.unreserved_characters, query=True)
        self.assertEqual(result, yuri.unreserved_characters)

    def test_path_encoding(self):
        self.assertEqual(yuri.encode('/', query=False), '/')
        self.assertEqual(yuri.encode(' ', query=False), '%20')

    def test_query_encoding(self):
        self.assertEqual(yuri.encode('/', query=True), '%2F')
        self.assertEqual(yuri.encode(' ', query=True), '+')

    def test_basic_encoding(self):
        should_encode = [chr(num) for num in range(32)] # For 0x00 - 0x1F
        should_encode.append('<>#%"{}|\^[]`')
        should_encode.append(chr(127)) # For 0x7F
        should_encode = ''.join(should_encode)

        for char in should_encode:
            result = yuri.encode(char, query=False)
            self.assertEqual(hexed(char), result)
            result = yuri.encode(char, query=True)
            self.assertEqual(hexed(char), result)

        del should_encode
        partial_encode = 'ab[]cd'
        expected = 'ab%5B%5Dcd'
        result = yuri.encode(partial_encode, query=True)
        self.assertEqual(expected, result)
        result = yuri.encode(partial_encode, query=False)
        self.assertEqual(expected, result)
        self.assertRaises(TypeError, yuri.encode, None)

class DecodingTests(unittest.TestCase):

    def test_ascii(self):
        escape_list = []
        for num in range(128):
            given = hexed(chr(num))
            expected = chr(num)
            result = yuri.decode(given, query=False)
            self.assertEqual(expected, result)
            result = yuri.decode(given, query=True)
            self.assertEqual(expected, result)
            escape_list.append(given)
        escape_string = ''.join(escape_list)
        del escape_list
        result = yuri.decode(escape_string)
        self.assertEqual(result.count('%'), 1)

    def test_badpercent(self):
        given = '%xab'
        expect = given
        result = yuri.decode(given)
        self.assertEqual(expect, result)
        given = '%x'
        expect = given
        result = yuri.decode(given)
        self.assertEqual(expect, result)
        given = '%'
        expect = given
        result = yuri.decode(given)
        self.assertEqual(expect, result)

    def test_mixedcase(self):
        given = '%Ab%eA'
        expect = '\xab\xea'
        result = yuri.decode(given)
        self.assertEqual(expect, result)

    def test_parts(self):
        given = 'ab%sd' % hexed('c')
        expect = "abcd"
        result = yuri.decode(given)
        self.assertEqual(expect, result)

    def test_query_decoding(self):
        given = "multiple+words+with+spaces"
        expect = given
        result = yuri.decode(given, query=False)
        self.assertEqual(expect, result)
        expect = given.replace('+', ' ')
        result = yuri.decode(given, query=True)
        self.assertEqual(expect, result)

    def test_unicode(self):
        r = yuri.decode(u'br%C3%BCckner_sapporo_20050930.doc')
        self.assertEqual(r, u'br\xc3\xbcckner_sapporo_20050930.doc')

class ParsingTests(unittest.TestCase):

    def test_parsing(self):
        tests = [
            ('file:///tmp/junk.txt',
                {'fragment': None,
                 'host': None,
                 'path': '/tmp/junk.txt',
                 'port': None,
                 'query': None,
                 'scheme': 'file',
                 'userinfo': None}),
            ('git+ssh://git@github.com/user/project.git',
                {'fragment': None,
                 'host': 'github.com',
                 'path': '/user/project.git',
                 'port': None,
                 'query': None,
                 'scheme': 'git+ssh',
                 'userinfo': 'git'}),
            ('http://www.python.org#abc',
                {'fragment': 'abc',
                 'host': 'www.python.org',
                 'path': '',
                 'port': None,
                 'query': None,
                 'scheme': 'http',
                 'userinfo': None}),
            ('http://www.python.org?q=abc',
                {'fragment': None,
                 'host': 'www.python.org',
                 'path': '',
                 'port': None,
                 'query': 'q=abc',
                 'scheme': 'http',
                 'userinfo': None}),
            ('http://www.python.org/#abc',
                {'fragment': 'abc',
                 'host': 'www.python.org',
                 'path': '/',
                 'port': None,
                 'query': None,
                 'scheme': 'http',
                 'userinfo': None}),
            ('http://a/b/c/d;p?q#f',
                {'fragment': 'f',
                 'host': 'a',
                 'path': '/b/c/d;p',
                 'port': None,
                 'query': 'q',
                 'scheme': 'http',
                 'userinfo': None}),
        ]

        for uri, expected in tests:
            result = yuri.parse(uri)
            self.assertEqual(result, expected)

class QueryDictTests(unittest.TestCase):

    def test_parsing(self):
        tests = [
            ('',            {}),
            ('&',           {}),
            ('&&',          {}),
            ('=',           {'': ''}),
            ('=a',          {'': 'a'}),
            ('a',           {'a': ''}),
            ('a=',          {'a': ''}),
            ('&a=b',        {'a': 'b'}),
            ('a=a+b&b=b+c', {'a': 'a b', 'b': 'b c'}),
            ('a=1&a=2',     {'a': ['1', '2']}),
        ]

        for given, expected in tests:
            d = yuri.QueryDict(given)
            self.assertEqual(d, expected)

    def test_dict(self):
        d = yuri.QueryDict('a=1')
        self.assertIn('a', d)
        self.assertEqual(d['a'], '1')
        del d['a']
        self.assertNotIn('a', d)

        d['b'] = 2
        self.assertIn('b', d)
        d.clear()
        self.assertFalse(d)

    def test_get(self):
        d = yuri.QueryDict('a=1')
        self.assertEqual(d.get('a'), '1')
        self.assertEqual(d.get('b', '2'), '2')

    def test_mixedcase(self):
        d = yuri.QueryDict('a=1')
        self.assertIn('A', d)

    def test_add(self):
        d = yuri.QueryDict('a=1')
        d.add('a', '2')
        self.assertListEqual(d['a'], ['1', '2'])

    def test_remove(self):
        d = yuri.QueryDict('a=1&a=2')
        d.remove('a', '1')
        self.assertEqual(d['a'], '2')

def load_tests(loader, tests, ignore):
    optionflags = doctest.NORMALIZE_WHITESPACE
    tests.addTests(doctest.DocTestSuite(yuri, optionflags=optionflags))
    return tests

if __name__ == '__main__':
    unittest.main()
