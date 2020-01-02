import synapse.exc as s_exc
import synapse.lib.urlhelp as s_urlhelp

import synapse.tests.utils as s_t_utils

urlcomps = (
    ('http://vertex.link:8080/hehe.html', {
        'scheme': 'http',
        'port': 8080,
        'host': 'vertex.link',
        'path': '/hehe.html',
    }),
    ('tcp://pennywise:candy@vertex.link/', {
        'scheme': 'tcp',
        'user': 'pennywise',
        'host': 'vertex.link',
        'path': '/',
        'passwd': 'candy',
    }),
    ('tcp://pennywise@vertex.link', {
        'scheme': 'tcp',
        'user': 'pennywise',
        'host': 'vertex.link',
        'path': '',
    }),
    ('tcp://1.2.3.4:8080/api/v1/wow?key=valu&foo=bar', {
        'scheme': 'tcp',
        'host': '1.2.3.4',
        'port': 8080,
        'path': '/api/v1/wow',
        'query': {
            'key': 'valu',
            'foo': 'bar',
        },
    }),
    ('http://[1fff:0:a88:85a3::ac1f]:8001/index.html', {
        'scheme': 'http',
        'host': '1fff:0:a88:85a3::ac1f',
        'port': 8001,
        'path': '/index.html',
    }),
    ('http://::1/index.html', {
        'scheme': 'http',
        'host': '::1',
        'path': '/index.html',
    }),
    ('www.vertex.link', {}),
)

class UrlTest(s_t_utils.SynTest):

    def test_urlchop(self):

        url = urlcomps[0][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[0][1], info)

        url = urlcomps[1][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[1][1], info)

        url = urlcomps[2][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[2][1], info)

        url = urlcomps[3][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[3][1], info)

        url = urlcomps[4][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[4][1], info)

        url = urlcomps[5][0]
        info = s_urlhelp.chopurl(url)
        self.eq(urlcomps[5][1], info)

        self.raises(s_exc.BadUrl, s_urlhelp.chopurl, urlcomps[6][0])

    def test_joinurlinfo(self):
        url = urlcomps[0][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, url)

        url = urlcomps[1][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, url)

        url = urlcomps[2][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, url)

        url = urlcomps[3][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, url)

        url = urlcomps[4][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, url)

        # the joined url will have added brackets since chopurl() does not provided whether it was enclosed
        url = urlcomps[5][0]
        info = s_urlhelp.chopurl(url)
        joined = s_urlhelp.joinurlinfo(info)
        self.eq(joined, 'http://[::1]/index.html')

        self.raises(KeyError, s_urlhelp.joinurlinfo, urlcomps[6][1])

    def test_hidepasswd(self):
        replw = '*****'

        url = urlcomps[0][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url)

        url = urlcomps[1][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url.replace('candy', replw))

        url = urlcomps[2][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url)

        url = urlcomps[3][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url)

        url = 'tcp://uname37:my-passwd@1.2.3.4:8080/api/v1/wow?key=valu&foo=bar'
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url.replace('my-passwd', replw))

        url = urlcomps[4][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url)

        url = 'http://foo:74barz@[1fff:0:a88:85a3::ac1f]:8001/index.html'
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url.replace('74barz', replw))

        url = urlcomps[5][0]
        hidden = s_urlhelp.hidepasswd(url)
        self.eq(hidden, url)

        self.raises(s_exc.BadUrl, s_urlhelp.chopurl, urlcomps[6][0])
