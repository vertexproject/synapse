import synapse.lib.version as s_version
import synapse.lib.httpclient as s_httpclient

import synapse.tests.utils as s_tests

class HttpClientTest(s_tests.SynTest):

    def test_httpclient_useragent(self):

        ua = s_httpclient.getUserAgent('Synapse-Cortex', '3.1.0')
        self.eq(ua, f'Synapse-Cortex/3.1.0 (Synapse/{s_version.version}; https://vertex.link)')

        # formatting is cached -- the same (prod, vers) pair returns the identical object
        self.true(s_httpclient.getUserAgent('a', '1') is s_httpclient.getUserAgent('a', '1'))

        # different args format differently
        self.ne(s_httpclient.getUserAgent('a', '1'), s_httpclient.getUserAgent('b', '1'))
        self.ne(s_httpclient.getUserAgent('a', '1'), s_httpclient.getUserAgent('a', '2'))

    def test_httpclient_setdefaultuseragent(self):

        # every input shape returns a list of pairs -- there is one return shape

        # headers=None -> just the default
        self.eq([('User-Agent', 'DEF')], s_httpclient.setDefaultUserAgent(None, 'DEF'))

        # empty dict / empty list -> default added
        self.eq([('User-Agent', 'DEF')], s_httpclient.setDefaultUserAgent({}, 'DEF'))
        self.eq([('User-Agent', 'DEF')], s_httpclient.setDefaultUserAgent([], 'DEF'))

        # exact-case User-Agent already present -> value left alone
        self.eq([('User-Agent', 'Mine')], s_httpclient.setDefaultUserAgent({'User-Agent': 'Mine'}, 'DEF'))

        # any-case User-Agent already present -> still left alone, and the original casing is preserved
        for key in ('user-agent', 'USER-AGENT', 'uSeR-aGeNt'):
            self.eq([(key, 'Mine')], s_httpclient.setDefaultUserAgent({key: 'Mine'}, 'DEF'))
            self.eq([(key, 'Mine')], s_httpclient.setDefaultUserAgent([(key, 'Mine')], 'DEF'))

        # other headers are carried through and the default appended, without mutating the input
        headers = {'X-Foo': 'bar'}
        self.eq([('X-Foo', 'bar'), ('User-Agent', 'DEF')], s_httpclient.setDefaultUserAgent(headers, 'DEF'))
        self.eq({'X-Foo': 'bar'}, headers)

        headers = [('X-Foo', 'bar')]
        self.eq([('X-Foo', 'bar'), ('User-Agent', 'DEF')], s_httpclient.setDefaultUserAgent(headers, 'DEF'))
        self.eq([('X-Foo', 'bar')], headers)

        # a tuple of pairs is accepted and normalized to a list like everything else
        self.eq([('X-Foo', 'bar'), ('User-Agent', 'DEF')],
                s_httpclient.setDefaultUserAgent((('X-Foo', 'bar'),), 'DEF'))

        # a repeated header name survives -- the reason the list is the single shape
        ret = s_httpclient.setDefaultUserAgent([('X-Foo', 'one'), ('X-Foo', 'two')], 'DEF')
        self.eq([('X-Foo', 'one'), ('X-Foo', 'two'), ('User-Agent', 'DEF')], ret)
