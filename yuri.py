"""Yuri is a URI manipulation module.

Jon Parise <jon@indelible.org>

Yuri attempts to conform to the following standards:

    RFC 3986 - "Uniform Resource Identifiers"
    T. Berners-Lee, R. Fielding and L.  Masinter, January 2005.
"""

# TODO:
# - Anything necessary for IDN support?
# - Proper Unicode handling (encoding paths)
# - Consistent encoding rules
# - Port urlparse, urllib unit test suites

__version__ = '0.1.0'

import binascii
import collections
import re

# We prefer to use OrderedDict, but if it's not available (< Python 2.7), we
# fall back to the normal dict implementation.  In the latter case, some of
# our doctests may fail due to non-determistic key ordering.  That can be
# addressed later if it becomes an actual problem in practice.
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

__all__ = ['parse', 'encode', 'decode', 'QueryDict', 'URI']

# A regular expression that splits a well-formed URI reference into its
# components (adapted from RFC 3986, Appendix B).
uri_re = re.compile(r"""^
        (?:(?P<scheme>[^:/?#]+):)?          # scheme:
        (?://(                              # //authority
            (?:(?P<userinfo>[^/?#@]+)@)?    # userinfo@
            (?:(?P<host>[^/?#:]+))?         # host
            (?::(?P<port>[0-9]+))?          # :port
        ))?                              
        (?P<path>[^?#]*)                    # path
        (?:\?(?P<query>[^#]*))?             # ?query
        (?:\#(?P<fragment>.*))?             # #fragment
        """,
        re.VERBOSE)

# A regular expression that implements a simple (and naive) heuristic for
# extracting the domain name portion of a fully-qualified hostname.  It looks
# for the last domain component that is followed by 2-to-6 characters of valid
# TLD-like characters (e.g. '.com', '.co.uk', '.info').
domain_re = re.compile(".*?([a-z0-9][a-z0-9\-]{1,63}\.[a-z\.]{2,6})$", re.I)

# Unreserved characters are allowed in a URI but should not be %-encoded.
# (RFC 3986, Section 2.3)
unreserved_characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                        'abcdefghijklmnopqrstuvwxyz' \
                        '0123456789' \
                        '_.-~'

def parse(uri):
    """Parse a URI string into a dictionary of its major components.

    This implementation follows the rules established by RFC 2396.
    Specifically, that means that parameters (marked by a semicolon) are
    allowed in the path portion of the URI.

    >>> d = parse('http://jon@www.example.com:1000/path;p?query#fragment')
    >>> for k in sorted(d.keys()): print "%s: %s" % (k, d[k])
    fragment:   fragment
    host:       www.example.com
    path:       /path;p
    port:       1000
    query:      query
    scheme:     http
    userinfo:   jon
    """
    match = uri_re.match(uri)
    if match is not None:
        return match.groupdict()
    return {}

def encode(s, query=False):
    """Percent-encode a string.

    >>> encode('ab[]cd')
    'ab%5B%5Dcd'

    The encoding rules default to path encoding (which preserves /'s), but
    query string encoding can also be requested:
    >>> encode('/two words')
    '/two%20words'
    >>> encode('/two words', query=True)
    '%2Ftwo+words'

    Unreserved characters are never encoded:
    >>> encode(unreserved_characters)
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~'
    """
    safe = unreserved_characters
    safe += ' ' if query else '/'
    encoded = ''
    for char in s:
        ordinal = ord(char)
        if ordinal < 128 and char in safe:
            encoded += char
        else:
            encoded += '%{:02X}'.format(ordinal)
    if query:
        encoded = encoded.replace(' ', '+')
    return encoded

def decode(s, query=False):
    """Decode a percent-encoded string.

    >>> decode('abc%20def')
    'abc def'

    The decoding rules default to path encoding, but query string encoding can
    also be requested:
    >>> decode('two%20words')
    'two words'
    >>> decode('two+words', query=True)
    'two words'
    """
    if query:
        s = s.replace('+', ' ')
    # Split the string into chunks at % boundaries.  The first two characters
    # of each chunk after the first should be hex digits in need of decoding.
    chunks = s.split('%')
    decoded = chunks[0]
    for chunk in chunks[1:]:
        if len(chunk) < 2:
            decoded += '%' + chunk
            continue
        try:
            decoded += binascii.unhexlify(chunk[:2])
            decoded += chunk[2:]
        except TypeError:
            decoded += '%' + chunk
        except UnicodeDecodeError:
            decoded += unichr(int(chunk[:2], 16))
            decoded += chunk[2:]
    return decoded

class QueryDict(OrderedDict):
    """A QueryDict manages a collection of query fields.

    It is based on an ordered dictionary to provide familiar access patterns.
    It adds support for multiple values per field, per the URI query string
    specification.

    It always store unencoded strings.  Strings are properly encoded once the
    QueryDict's URI string representation is request (via the __str__ method).
    """
    def __init__(self, query=None):
        """Initialize a QueryDict.

        If a query string is provided, it will be parsed and used as the basis
        for the QueryDict's fields.

        Name-value pairs can be separated by either ampersands or semicolons:
        >>> QueryDict('a=1&b=2;c=3')
        {'a': '1', 'b': '2', 'c': '3'}

        Multiple values can be associated with a single name:
        >>> QueryDict('name=value1&name=value2')
        {'name': ['value1', 'value2']}

        Fields without values are supported:
        >>> QueryDict('lonely')
        {'lonely': ''}

        Names and values are percent-encoded as necessary:
        >>> QueryDict('name=two words')
        {'name': 'two words'}
        """
        OrderedDict.__init__(self)
        if query is not None:
            self.parse(query)

    def __repr__(self):
        """Return the QueryDict's simplified dictionary representation.

        >>> QueryDict('a=1&b=2&b=3')
        {'a': '1', 'b': ['2', '3']}
        """
        fields = []
        for name, values in self.iteritems():
            fields.append("'%s': %r" % (name, values))
        return '{%s}' % ', '.join(fields)

    def __str__(self):
        """Return the query list's URI query string representation.

        >>> str(QueryDict('a=1&b=2'))
        'a=1&b=2'
        """
        pairs = []
        for name, values in self.iteritems():
            name = encode(name, query=True)
            for value in values:
                value = encode(value, query=True)
                pairs.append('%s=%s' % (name, value))
        return '&'.join(pairs)

    def __contains__(self, name):
        name = name.lower()
        return OrderedDict.__contains__(self, name)

    def __setitem__(self, name, value):
        """Set a field to one or more values."""
        name = name.lower()
        OrderedDict.__setitem__(self, name, str(value))

    def __delitem__(self, name):
        """Delete a field and all of its values."""
        name = name.lower()
        OrderedDict.__delitem__(self, name)

    def get(self, name, default=None):
        return OrderedDict.get(self, name.lower(), default)

    def update(self, *args, **kwargs):
        # Make sure we use our custom __setitem__.
        for k, v in OrderedDict(*args, **kwargs).iteritems():
            self[k] = v

    def add(self, name, value):
        """Add a new value to the given field name.

        >>> q = QueryDict(); q
        {}
        >>> q.add('a', '1'); q
        {'a': '1'}
        >>> q.add('a', '2'); q
        {'a': ['1', '2']}
        """
        name = name.lower()
        if name in self:
            values = self[name]
            if type(values) is not list:
                values = [values]
            values.append(str(value))
            OrderedDict.__setitem__(self, name, values)
        else:
            OrderedDict.__setitem__(self, name, str(value))

    def remove(self, name, value):
        """Remove a single value for the given field name.

        Once all of a field's values are removed, the value itself will be
        removed.

        >>> q = QueryDict('a=1&a=2'); q
        {'a': ['1', '2']}
        >>> q.remove('a', '2'); q
        {'a': '1'}
        >>> q.remove('a', '2'); q
        {'a': '1'}
        >>> q.remove('a', '1'); q
        {}
        >>> q.remove('a', '1')
        Traceback (most recent call last):
            ...
        KeyError: 'a'
        """
        name = name.lower()
        values = self[name]
        if type(values) is list:
            values.remove(value)
            if len(values) == 1:
                self[name] = values[0]
            elif not values:
                del self[name]
        elif value == values:
            del self[name]

    def parse(self, query):
        """Parse the given query string and add its fields."""
        for pair in re.split('[&;]', query):
            try:
                name, value = pair.split('=')
            except ValueError:
                # Skip completely empty items.
                if not pair:
                    continue
                # Allow names without values.
                name, value = pair, ''
            name = decode(name, query=True)
            value = decode(value, query=True)
            self.add(name, value)

class URI(object):

    def __init__(self, scheme=None, userinfo=None, host=None, port=None,
            path=None, query=None, fragment=None):
        self.scheme = scheme
        self.userinfo = userinfo
        self.host = host
        self.port = port
        self.path = path
        self.query = QueryDict(query)
        self.fragment = fragment

    @classmethod
    def parse(cls, uri):
        """Construct a URI object by parsing the given URI string.

        >>> URI.parse('http://www.example.com:8080/path')
        <URI scheme='http', userinfo=None, host='www.example.com',
         port=8080, path='/path', query={}, fragment=None>
        """
        components = parse(uri)
        return cls(**components)

    def __repr__(self):
        return '<URI scheme=%(scheme)r, userinfo=%(userinfo)r, ' \
               'host=%(host)r, port=%(port)r, path=%(path)r, ' \
               'query=%(query)r, fragment=%(fragment)r>' % self.__dict__

    def __str__(self):
        """Return this object's corresponding URI reference string.

        >>> str(URI(scheme='http', host='www.example.com'))
        'http://www.example.com'
        >>> str(URI(scheme='http', host='www.example.com', path='/foo'))
        'http://www.example.com/foo'
        >>> str(URI(scheme='http', host='www.example.com', port=8080))
        'http://www.example.com:8080'
        >>> str(URI(scheme='http', host='www.example.com', userinfo='jon'))
        'http://jon@www.example.com'
        >>> str(URI(scheme='http', host='www.example.com', query='a=1'))
        'http://www.example.com?a=1'
        """
        uri = ''
        if self.scheme:
            uri += self.scheme + ':'
        if self.userinfo or self.host or self.port:
            uri += '//'
            if self.userinfo:
                uri += self.userinfo + '@'
            if self.host:
                uri += self.host
            if self.port:
                uri += ':' + str(self.port)
        if self.path:
            uri += self.path
        if self.query:
            uri += '?' + str(self.query)
        if self.fragment:
            uri += '#' + self.fragment
        return uri

    @property
    def domain(self):
        """Get just the domain portion of the host component.

        >>> URI(host='localhost').domain
        'localhost'
        >>> URI(host='example.com').domain
        'example.com'
        >>> URI(host='www.example.com').domain
        'example.com'
        >>> URI(host='www.example.co.uk').domain
        'example.co.uk'
        """
        # Just use our regular expression in our attempt to extract the domain
        # name portion of the host string.  A more correct approach would
        # involve maintaining a list of all registered top-level domains plus
        # DNS SOA queries for each subdomain portion of the host, but both of
        # those approaches are expensive and beyond our current intent.
        match = domain_re.match(self.host)
        if match is not None:
            return match.group(1)
        return self.host

    @property
    def port(self):
        """Access the URI's port component.

        If not None, the port value must be numeric and fall within the valid
        port number range (0-65535).

        >>> URI(port=8080).port
        8080
        >>> URI(port='8080').port
        8080
        >>> URI(port=-100).port
        Traceback (most recent call last):
            ...
        ValueError: -100 is outside the valid port range (0-65535)
        """
        return self.__dict__.get('port')

    @port.setter
    def port(self, port):
        if port is not None:
            # We always store the port as a number internally.
            port = int(port)
            if port < 0 or port > 65535:
                raise ValueError('%d is outside the valid port range '
                                 '(0-65535)' % port)
        self.__dict__['port'] = port

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
