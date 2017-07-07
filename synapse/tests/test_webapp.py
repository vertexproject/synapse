import ssl
import json

from tornado.httpclient import HTTPError
from tornado.testing import gen_test, AsyncTestCase, AsyncHTTPClient

import synapse.cortex
import synapse.lib.webapp as s_webapp
import synapse.datamodel as s_datamodel
import synapse.lib.certdir as s_certdir

from synapse.tests.common import *

class Horked(Exception): pass

class Foo:

    def bar(self):
        return 'baz'

    @s_datamodel.parsetypes('int', y='int')
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

        wapp = s_webapp.WebApp(boss_minsize=13, boss_maxsize=37)
        self.eq(wapp.boss.pool._pool_maxsize, 37)

        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/horked', foo.horked)
        wapp.addApiPath('/v1/addup/([0-9]+)', foo.addup)

        client = AsyncHTTPClient(self.io_loop)
        port = wapp.getServBinds()[0][1]
        resp = yield client.fetch('http://127.0.0.1:%d/v1/addup/30?y=40' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.eq(resp.get('ret'), 70)
        self.eq(resp.get('status'), 'ok')

        resp = yield client.fetch('http://127.0.0.1:%d/v1/addup/20' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.eq(resp.get('ret'), 20)
        self.eq(resp.get('status'), 'ok')

        resp = yield client.fetch('http://127.0.0.1:%d/v1/horked' % port)
        resp = json.loads(resp.body.decode('utf-8'))

        self.eq(resp.get('err'), 'Horked')
        self.eq(resp.get('status'), 'err')

        wapp.fini()

    @gen_test
    def test_webapp_body(self):

        # tornado does not support windows (yet)
        self.thisHostMustNot(platform='windows')

        class Haha:
            def bar(self, hehe, body=None):
                return (hehe, body.decode('utf8'))

        haha = Haha()

        wapp = s_webapp.WebApp()
        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/haha/bar/([a-z]+)', haha.bar)

        client = AsyncHTTPClient(self.io_loop)
        port = wapp.getServBinds()[0][1]

        headers = {'Content-Type': 'application/octet-stream'}

        resp = yield client.fetch('http://127.0.0.1:%d/v1/haha/bar/visi' % port, headers=headers, body='GRONK', allow_nonstandard_methods=True)
        resp = json.loads(resp.body.decode('utf-8'))
        self.eq(tuple(resp.get('ret')), ('visi', 'GRONK'))

        resp = yield client.fetch('http://127.0.0.1:%d/v1/haha/bar/visi' % port, method='POST', headers=headers, body='GRONK')
        resp = json.loads(resp.body.decode('utf-8'))
        self.eq(tuple(resp.get('ret')), ('visi', 'GRONK'))

        wapp.fini()

    @gen_test
    def test_webapp_ssl(self):

        # tornado does not support windows (yet)
        self.thisHostMustNot(platform='windows')

        foo = Foo()

        with self.getTestDir() as dirname:

            cdir = s_certdir.CertDir(path=dirname)

            cdir.genCaCert('syntest') # Generate a new CA
            cdir.genUserCert('visi@vertex.link', signas='syntest')  # Generate a new user cert and key, signed by the new CA
            cdir.genHostCert('localhost', signas='syntest')  # Generate a new server cert and key, signed by the new CA

            ca_cert = cdir.getCaCertPath('syntest')
            host_key = cdir.getHostKeyPath('localhost')
            host_cert = cdir.getHostCertPath('localhost')

            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            ssl_ctx.load_cert_chain(host_cert, host_key)
            ssl_ctx.load_verify_locations(ca_cert)
            srv_config = {'ssl_options': ssl_ctx}

            wapp = s_webapp.WebApp(srv_config=srv_config)
            wapp.listen(0, host='127.0.0.1')
            wapp.addApiPath('/v1/bar', foo.bar)

            client = AsyncHTTPClient(self.io_loop)
            port = wapp.getServBinds()[0][1]
            http_url = 'http://127.0.0.1:%d/v1/bar' % port
            https_url = 'https://127.0.0.1:%d/v1/bar' % port
            user_key = cdir.getUserKeyPath('visi@vertex.link')
            user_cert = cdir.getUserCertPath('visi@vertex.link')
            client_opts = {
                'ca_certs': ca_cert,
                'client_key': user_key,
                'client_cert': user_cert
            }

            # Assert that the request fails w/ http protocol
            with self.raises(TestSSLConnectionResetErr):
                resp = yield client.fetch(http_url)

            # Assert that the request fails w/ no client SSL config
            with self.raises(ssl.SSLError):
                resp = yield client.fetch(https_url)

            # Assert that the request fails w/ no client SSL config, even if client does not validate cert
            # (server must also validate client cert)
            with self.raises(TestSSLInvalidClientCertErr):
                resp = yield client.fetch(https_url, validate_cert=False)

            resp = yield client.fetch(https_url, **client_opts)
            resp = json.loads(resp.body.decode('utf-8'))

            self.eq(resp.get('ret'), 'baz')
            self.eq(resp.get('status'), 'ok')

            wapp.fini()
