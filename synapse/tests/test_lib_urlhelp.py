import synapse.exc as s_exc
import synapse.lib.urlhelp as s_urlhelp

import synapse.tests.utils as s_t_utils

class UrlTest(s_t_utils.SynTest):
    def test_urlchop(self):

        url = 'http://vertex.link:8080/hehe.html'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'http',
                 'port': 8080,
                 'host': 'vertex.link',
                 'path': '/hehe.html',
                 },
                info
                )

        url = 'tcp://pennywise:candy@vertex.link/'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'tcp',
                 'user': 'pennywise',
                 'host': 'vertex.link',
                 'path': '/',
                 'passwd': 'candy',
                 },
                info
                )

        url = 'tcp://pennywise@vertex.link'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'tcp',
                 'user': 'pennywise',
                 'host': 'vertex.link',
                 'path': '',
                 },
                info
                )

        url = 'tcp://1.2.3.4:8080/api/v1/wow?key=valu&foo=bar'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'tcp',
                 'host': '1.2.3.4',
                 'port': 8080,
                 'path': '/api/v1/wow',
                 'query': {'key': 'valu',
                           'foo': 'bar',
                           }
                 },
                info
                )

        url = 'http://[1fff:0:a88:85a3::ac1f]:8001/index.html'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'http',
                 'host': '1fff:0:a88:85a3::ac1f',
                 'port': 8001,
                 'path': '/index.html',
                 },
                info
                )

        url = 'http://::1/index.html'
        info = s_urlhelp.chopurl(url)
        self.eq({'scheme': 'http',
                 'host': '::1',
                 'path': '/index.html',
                 },
                info
                )

        self.raises(s_exc.BadUrl, s_urlhelp.chopurl,
                    'www.vertex.link')
