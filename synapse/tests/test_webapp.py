
import json

from tornado.httpclient import HTTPError
from tornado.testing import gen_test, AsyncTestCase, AsyncHTTPClient

import synapse.cortex
import synapse.datamodel as s_datamodel
import synapse.lib.webapp as s_webapp

from synapse.tests.common import *

class Horked(Exception):pass

model = s_datamodel.DataModel()

class Foo:

    def bar(self):
        return 'baz'

    @model.parsetypes('int', y='int')
    def addup(self, x, y=0):
        return x + y

    def horked(self):
        raise Horked('you are so horked')

class WebAppTest(AsyncTestCase, SynTest):

    @gen_test
    def test_webapp_publish(self):

        # tornado does not support windows (yet)
        self.thisHostMustNot(platform='windows')
        foo = Foo()

        wapp = s_webapp.WebApp()
        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/horked', foo.horked )
        wapp.addApiPath('/v1/addup/([0-9]+)', foo.addup )

        client = AsyncHTTPClient(self.io_loop)
        port = wapp.getServBinds()[0][1]
        resp = yield client.fetch('http://127.0.0.1:%d/v1/addup/30?y=40' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.assertEqual( resp.get('ret'), 70 )
        self.assertEqual( resp.get('status'), 'ok' )

        resp = yield client.fetch('http://127.0.0.1:%d/v1/addup/20' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.assertEqual( resp.get('ret'), 20 )
        self.assertEqual( resp.get('status'), 'ok' )

        resp = yield client.fetch('http://127.0.0.1:%d/v1/horked' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.assertEqual( resp.get('err'), 'Horked' )
        self.assertEqual( resp.get('status'), 'err' )

        wapp.fini()

    @gen_test
    def test_webapp_body(self):

        class Haha:
            def bar(self, hehe, body=None):
                return (hehe,body.decode('utf8'))

        haha = Haha()

        wapp = s_webapp.WebApp()
        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/haha/bar/([a-z]+)', haha.bar)

        client = AsyncHTTPClient(self.io_loop)
        port = wapp.getServBinds()[0][1]

        headers={'Content-Type': 'application/octet-stream'}

        resp = yield client.fetch('http://127.0.0.1:%d/v1/haha/bar/visi' % port, headers=headers, body='GRONK', allow_nonstandard_methods=True)
        resp = json.loads(resp.body.decode('utf-8'))
        self.assertEqual( tuple(resp.get('ret')), ('visi','GRONK') )

        resp = yield client.fetch('http://127.0.0.1:%d/v1/haha/bar/visi' % port, method='POST', headers=headers, body='GRONK')
        resp = json.loads(resp.body.decode('utf-8'))
        self.assertEqual( tuple(resp.get('ret')), ('visi','GRONK') )

        wapp.fini()
