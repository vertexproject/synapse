import os

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.tests.common import *

byts = os.urandom(1024000)
class FooBar:
    def bar(self):
        return byts * 50

class SslTest(SynTest):

    def test_ssl_hugetx(self):

        # FIXME some kind of cert validation diffs in *py* vers killed us
        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        with s_daemon.Daemon() as dmon:

            dmon.share('foobar', FooBar())

            link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)

            port = link[1].get('port')

            url = 'ssl://localhost/foobar'

            with s_telepath.openurl(url, port=port, cafile=cafile) as foo:
                self.nn(foo.bar())
