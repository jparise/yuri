"""Yuri is a URI manipulation module.

Jon Parise <jon@indelible.org>

Yuri attempts to conform to the following standards:

    RFC 3986 - "Uniform Resource Identifiers"
    T. Berners-Lee, R. Fielding and L.  Masinter, January 2005.
"""

import re

__all__ = ['parse', 'URI']

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
            uri += '?' + self.query
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
