import json
import requests

import synapse.cortex
import synapse.datamodel as s_datamodel
import synapse.lib.webapp as s_webapp

from synapse.tests.common import *

class Horked(Exception):pass

class Foo:

    def bar(self):
        return 'baz'

    @s_datamodel.parsetypes('int', y='int')
    def addup(self, x, y=0):
        return x + y

    def horked(self):
        raise Horked('you are so horked')


class TestCrudHand(SynTest):

    def setUp(self):
        core = synapse.cortex.openurl('ram://')
        self.wapp = s_webapp.WebApp()
        self.wapp.listen(0, host='127.0.0.1')
        self.host = 'http://127.0.0.1:%d' % (self.wapp.getServBinds()[0][1])
        for model_name in ['foo', 'bar']:
            self.wapp.addHandPath('/v1/(%s)' % (model_name), s_webapp.CrudHand, core=core)
            self.wapp.addHandPath('/v1/(%s)/([^/]+)' % (model_name), s_webapp.CrudHand, core=core)

    def tearDown(self):
        self.wapp.fini()

    def test_invalid_model(self):
        self.thisHostMustNot(platform='windows')
        resp = requests.get(self.host + '/v1/horked', timeout=1)
        self.assertEqual(resp.status_code, 404)

    def test_crud_single(self):
        self.thisHostMustNot(platform='windows')

        # Can we create a tufo?
        data = json.dumps({'foo': 'val1', 'key2': 'val2'})
        tufo = {'foo': 'val1', 'foo:foo': 'val1', 'foo:key2': 'val2', 'tufo:form': 'foo'}
        resp = requests.post(self.host + '/v1/foo', data=data, headers={'Content-Type': 'application/json'}, timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        #self.assertEqual(resp['ret'][1], tufo)
        self.assertDictMust(resp['ret'][1], tufo)
        iden = resp['ret'][0]

        # Does it persist?
        resp = requests.get(self.host + '/v1/foo/' + iden, timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(resp['ret'], [iden, tufo])

        # Can it be updated?
        data = json.dumps({'key2': 'val22', 'key3': 'val3'})
        tufo = {'foo': 'val1', 'foo:foo': 'val1', 'foo:key2': 'val22', 'foo:key3': 'val3', 'tufo:form': 'foo'}
        resp = requests.patch(self.host + '/v1/foo/' + iden, data=data, headers={'Content-Type': 'application/json'}, timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(resp['ret'][1], tufo)

        # Can it be deleted?
        resp = requests.delete(self.host + '/v1/foo/' + iden, timeout=1).json()
        self.assertEqual(resp['status'], 'ok')

        resp = requests.get(self.host + '/v1/foo/' + iden, timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        assert resp['ret'] is None

    def assertDictMust(self, info, must):
        for k,v in must.items():
            if info.get(k) != v:
                raise Exception('%s != %r' % (k,v))

    def test_crud_multi(self):
        self.thisHostMustNot(platform='windows')

        # Can we create tufos?
        tufo = {}
        for i in range(2):
            i = str(i)
            data = json.dumps({'bar': i, 'key' + i: 'val' + i})
            resp = requests.post(self.host + '/v1/bar', data=data, headers={'Content-Type': 'application/json'}, timeout=1).json()
            self.assertEqual(resp['status'], 'ok')
            self.assertDictMust(resp['ret'][1], {'bar': i, 'bar:bar': i, 'bar:key' + i: 'val' + i, 'tufo:form': 'bar',})
            tufo[resp['ret'][0]] = resp['ret'][1]

        # Do they persist?
        resp = requests.get(self.host + '/v1/bar', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(len(resp['ret']), len(tufo))
        for rslt in resp['ret']:
            self.assertDictMust(tufo[rslt[0]],rslt[1])

        # Can we get a subset?
        resp = requests.get(self.host + '/v1/bar?prop=bar:key1&value=val1', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(len(resp['ret']), 1)
        for rslt in resp['ret']:
            self.assertDictMust(tufo[rslt[0]],rslt[1])
            self.assertEqual(rslt[1]['bar:key1'], 'val1')

        # Can we delete a subset?
        resp = requests.delete(self.host + '/v1/bar?prop=bar:key1&value=val1', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')

        resp = requests.get(self.host + '/v1/bar', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(len(resp['ret']), 1)
        for rslt in resp['ret']:
            self.assertDictMust(tufo[rslt[0]], rslt[1])
            self.assertEqual(rslt[1]['bar:key0'], 'val0')

        # Can they be deleted?
        resp = requests.delete(self.host + '/v1/bar', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')

        resp = requests.get(self.host + '/v1/bar', timeout=1).json()
        self.assertEqual(resp['status'], 'ok')
        self.assertEqual(resp['ret'], [])


class WebAppTest(SynTest):

    def test_webapp_publish(self):

        # tornado does not support windows (yet)
        self.thisHostMustNot(platform='windows')
        foo = Foo()

        wapp = s_webapp.WebApp()
        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/horked', foo.horked )
        wapp.addApiPath('/v1/addup/([0-9]+)', foo.addup )

        port = wapp.getServBinds()[0][1]
        resp = requests.get('http://127.0.0.1:%d/v1/addup/30?y=40' % port, timeout=1).json()

        self.assertEqual( resp.get('ret'), 70 )
        self.assertEqual( resp.get('status'), 'ok' )

        resp = requests.get('http://127.0.0.1:%d/v1/addup/20' % port, timeout=1).json()

        self.assertEqual( resp.get('ret'), 20 )
        self.assertEqual( resp.get('status'), 'ok' )

        resp = requests.get('http://127.0.0.1:%d/v1/horked' % port, timeout=1).json()

        self.assertEqual( resp.get('err'), 'Horked' )
        self.assertEqual( resp.get('status'), 'err' )

        wapp.fini()

    def test_webapp_body(self):

        # python requests module has windows bug?!?!?
        self.thisHostMustNot(platform='windows')

        class Haha:
            def bar(self, hehe, body=None):
                return (hehe,body.decode('utf8'))

        haha = Haha()

        wapp = s_webapp.WebApp()
        wapp.listen(0, host='127.0.0.1')
        wapp.addApiPath('/v1/haha/bar/([a-z]+)', haha.bar)

        port = wapp.getServBinds()[0][1]

        headers={'Content-Type': 'application/octet-stream'}

        resp = requests.get('http://127.0.0.1:%d/v1/haha/bar/visi' % port, timeout=1, headers=headers, data='GRONK').json()
        self.assertEqual( tuple(resp.get('ret')), ('visi','GRONK') )

        resp = requests.post('http://127.0.0.1:%d/v1/haha/bar/visi' % port, timeout=1, headers=headers, data='GRONK').json()
        self.assertEqual( tuple(resp.get('ret')), ('visi','GRONK') )

        wapp.fini()
