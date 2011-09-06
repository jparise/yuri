"""Yuri is a URI manipulation module.

Jon Parise <jon@indelible.org>

Yuri attempts to conform to the following standards:

    RFC 3986 - "Uniform Resource Identifiers"
    T. Berners-Lee, R. Fielding and L.  Masinter, January 2005.
"""

import binascii
import re

__all__ = ['parse', 'encode', 'decode', 'querylist', 'URI']

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

    >>> d = parse('http://jon@www.example.com:1000/path?query#fragment')
    >>> for k in sorted(d.keys()): print "%s: %s" % (k, d[k])
    fragment:   fragment
    host:       www.example.com
    path:       /path
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
    # Split the string into chunks at % boundaries.  The first two characters
    # of each chunk after the first should be hex digits in need of decoding.
    chunks = s.split('%')
    decoded = chunks[0]
    for chunk in chunks[1:]:
        decoded += binascii.unhexlify(chunk[:2])
        decoded += chunk[2:]
    if query:
        decoded = decoded.replace('+', ' ')
    return decoded

def querylist(query):
    """Convert a query string into a list of name-value tuples.

    Name-value pairs can be separated by either ampersands or semicolons:
    >>> querylist('a=1&b=2;c=3')
    [('a', '1'), ('b', '2'), ('c', '3')]

    Multiple values can be associated with a single name:
    >>> querylist('name=value1&name=value2')
    [('name', 'value1'), ('name', 'value2')]

    Fields without values are ignored:
    >>> querylist('lonely')
    []

    Names and values are percent-encoded as necessary:
    >>> querylist('name=two words')
    [('name', 'two+words')]
    """
    l = []
    for pair in re.split('[&;]', query):
        try:
            name, value = pair.split('=')
            name = encode(name, query=True)
            value = encode(value, query=True)
            l.append((name, value))
        except ValueError:
            continue
    return l

class URI(object):

    def __init__(self, scheme=None, userinfo=None, host=None, port=None,
            path=None, query=None, fragment=None):
        self.scheme = scheme
        self.userinfo = userinfo
        self.host = host
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment

    @classmethod
    def parse(cls, uri):
        """Construct a URI object by parsing the given URI string.

        >>> URI.parse('http://www.example.com:8080/path')
        <URI scheme=http, userinfo=None, host=www.example.com,
         port=8080, path=/path, query=None, fragment=None>
        """
        components = parse(uri)
        return cls(**components)

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
            pairs = ['='.join(pair) for pair in self.query]
            uri += '?' + '&'.join(pairs)
        if self.fragment:
            uri += '#' + self.fragment
        return uri

    def __repr__(self):
        return '<URI scheme=%(scheme)s, userinfo=%(userinfo)s, ' \
               'host=%(host)s, port=%(port)s, path=%(path)s, ' \
               'query=%(query)s, fragment=%(fragment)s>' % self.__dict__

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

    @property
    def query(self):
        """Access the URI's query string component.

        Query strings are always given in their "exploded" form: as a list of
        name-value tuples.

        >>> uri = URI(query='a=1&b=2')
        >>> uri.query
        [('a', '1'), ('b', '2')]

        The query list can be manipulated directly:
        >>> uri.query.append(('c', '3'))
        >>> uri.query
        [('a', '1'), ('b', '2'), ('c', '3')]
        >>> uri.query.pop()
        ('c', '3')
        >>> uri.query
        [('a', '1'), ('b', '2')]
        """
        return self.__dict__.get('query')

    @query.setter
    def query(self, query):
        # Convert queries strings to a list of query values.
        if isinstance(query, basestring):
            query = querylist(query)

        # At this point, our query must be None or a list.
        if query is not None and not isinstance(query, list):
            raise ValueError('value must be a list (got %r)' % type(query))

        self.__dict__['query'] = query

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
