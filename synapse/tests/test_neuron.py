import io
import threading

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.neuron as s_neuron
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.session as s_session

from synapse.common import *
from synapse.tests.common import *

# some syntax sugar
class Net:
    def __init__(self, info):
        self.info = info
    def __getattr__(self, name):
        return self.info[name]

class FooBar:
    def __init__(self):
        pass

    def foo(self, x):
        return x + 20

    def bar(self, x):
        raise Exception('hi')

    def getsess(self, prop):
        sess = s_session.current()
        return sess.get(prop)

    def setsess(self, prop, valu):
        sess = s_session.current()
        sess.set(prop,valu)

import unittest
@unittest.skip('neuron tests temp disabled')
class TestNeuron(SynTest):

    def initNeuNet(self, usepki=False):
        '''
        Construct a neuron mesh making sure to wait for all
        link events ( so the mesh is "settled" before the test )
        '''
        neu0 = s_neuron.Neuron()
        neu1 = s_neuron.Neuron()
        neu2 = s_neuron.Neuron()
        neu3 = s_neuron.Neuron()

        if usepki:
            root = neu0.pki.genRootToken(bits=512)

            neu1.pki.setTokenTufo(root)
            neu2.pki.setTokenTufo(root)
            neu3.pki.setTokenTufo(root)

            tokn0 = neu0.pki.genUserToken(neu0.iden, can=('mesh:join',), bits=512)
            tokn1 = neu1.pki.genUserToken(neu1.iden, can=('mesh:join',), bits=512)
            tokn2 = neu2.pki.genUserToken(neu2.iden, can=('mesh:join',), bits=512)
            tokn3 = neu3.pki.genUserToken(neu3.iden, can=('mesh:join',), bits=512)

            cert0 = neu0.pki.genTokenCert(tokn0, signas=root[0])
            cert1 = neu0.pki.genTokenCert(tokn1, signas=root[0])
            cert2 = neu0.pki.genTokenCert(tokn2, signas=root[0])
            cert3 = neu0.pki.genTokenCert(tokn3, signas=root[0])

            neu0.pki.setTokenCert(neu0.iden, cert0)
            neu1.pki.setTokenCert(neu1.iden, cert1)
            neu2.pki.setTokenCert(neu2.iden, cert2)
            neu3.pki.setTokenCert(neu3.iden, cert3)

            neu0.setNeuProp('usepki',1)
            neu1.setNeuProp('usepki',1)
            neu2.setNeuProp('usepki',1)
            neu3.setNeuProp('usepki',1)

        #print('NEU0: %r' % (neu0.iden,))
        #print('NEU1: %r' % (neu1.iden,))
        #print('NEU2: %r' % (neu2.iden,))
        #print('NEU3: %r' % (neu3.iden,))

        link0 = neu0.listen('tcp://127.0.0.1:0/neuron')
        link1 = neu1.listen('tcp://127.0.0.1:0/neuron')
        link2 = neu2.listen('tcp://127.0.0.1:0/neuron')
        link3 = neu3.listen('tcp://127.0.0.1:0/neuron')

        full0 = self.getTestWait(neu0,6,'neu:link:init')
        full1 = self.getTestWait(neu1,6,'neu:link:init')
        full2 = self.getTestWait(neu2,4,'neu:link:init')
        full3 = self.getTestWait(neu3,2,'neu:link:init')

        # connect neu0->neu1

        wait0 = self.getTestWait(neu0,2,'neu:link:init')
        wait1 = self.getTestWait(neu1,2,'neu:link:init')

        neu0.connect('tcp://127.0.0.1:0/', port=link1[1]['port'] )

        wait0.wait()
        wait1.wait()

        # connect neu0->neu2

        wait0 = self.getTestWait(neu0,2,'neu:link:init')
        wait2 = self.getTestWait(neu2,2,'neu:link:init')

        neu0.connect('tcp://127.0.0.1:0/', port=link2[1]['port'] )

        wait0.wait()
        wait2.wait()

        # connect neu2->neu3
        wait2 = self.getTestWait(neu2,2,'neu:link:init')
        wait3 = self.getTestWait(neu3,2,'neu:link:init')

        neu2.connect('tcp://127.0.0.1:0/', port=link3[1]['port'] )

        wait2.wait()
        wait3.wait()

        # make sure all neu:link:init mesgs have been consumed

        full0.wait()
        full1.wait()
        full2.wait()
        full3.wait()

        return Net(locals())

    def finiNeuNet(self, net):

        w0 = self.getTestWait(net.neu0,1,'test:fini')
        w1 = self.getTestWait(net.neu1,1,'test:fini')
        w2 = self.getTestWait(net.neu2,1,'test:fini')
        w3 = self.getTestWait(net.neu3,1,'test:fini')

        net.neu0.storm('test:fini')

        w0.wait()
        w1.wait()
        w2.wait()
        w3.wait()

        net.neu0.fini()
        net.neu1.fini()
        net.neu2.fini()
        net.neu3.fini()

    def newp_neuron_basics(self):

        net = self.initNeuNet()

        net.neu3.share('foo',FooBar())

        dend = s_neuron.openlink(net.link0)

        path = '%s/foo' % (net.neu3.iden,)
        prox = dend.open(path)

        task = ('foo',(30,),{})

        job = dend.call( net.neu3.iden, 'foo', task )

        self.assertIsNotNone(job)

        self.assertEqual( dend.sync(job), 50)

        self.assertEqual( prox.foo(11), 31 )

        data = {}
        def ondone(j):
            data['ret'] = s_async.jobret(j)

        job = prox.foo(12, ondone=ondone)

        self.assertEqual( dend.sync(job), 32 )
        self.assertEqual( data.get('ret'), 32 )

        self.finiNeuNet(net)

    def test_neuron_tree(self):
        net = self.initNeuNet()

        def flat(x):
            ret = set()
            todo = [ t for t in x ]
            while todo:
                n = todo.pop()
                ret.add(n[0])

                for k in n[1]:
                    todo.append(k)
            return ret

        # ensure each can build a tree to 
        # all the others...

        iall = set([
            net.neu0.iden,
            net.neu1.iden,
            net.neu2.iden,
            net.neu3.iden,
        ])

        set0 = flat( net.neu0.getPathTrees() )
        set1 = flat( net.neu1.getPathTrees() )
        set2 = flat( net.neu2.getPathTrees() )
        set3 = flat( net.neu3.getPathTrees() )

        self.assertEqual( len( iall & set0 ), 3 )
        self.assertEqual( len( iall & set1 ), 3 )
        self.assertEqual( len( iall & set2 ), 3 )
        self.assertEqual( len( iall & set3 ), 3 )

        self.finiNeuNet(net)

    def test_neuron_storm(self):
        net = self.initNeuNet()

        w2 = self.getTestWait(net.neu2, 1, 'woot:baz')
        w3 = self.getTestWait(net.neu3, 1, 'woot:baz')

        net.neu1.storm('woot:baz', faz=30)

        w2.wait()
        w3.wait()

        self.finiNeuNet(net)

    def newp_neuron_ping(self):
        net = self.initNeuNet()

        dend = s_neuron.openlink(net.link0)

        path = '%s/neuron' % (net.neu2.iden,)
        prox1 = dend.open(path)

        pong = prox1.ping()

        self.assertIsNotNone(pong)
        self.assertEqual( pong.get('iden'), net.neu2.iden )

        self.finiNeuNet(net)

    def newp_dendrite_share(self):
        net = self.initNeuNet()

        dend0 = s_neuron.openlink(net.link0)
        dend3 = s_neuron.openlink(net.link3)

        w0 = self.getTestWait(net.neu0, 2, 'neu:dend:init')

        dend3.share('foobar0', FooBar(), tags=('foo.bar.0',))
        dend3.share('foobar1', FooBar(), tags=('foo.bar.1',))

        w0.wait()

        self.assertIsNotNone( dend0.getDendByIden('foobar0') )
        self.assertIsNotNone( dend0.getDendByIden('foobar1') )

        bytag = dend0.getDendsByTag('foo.bar')
        self.assertEqual( len(bytag), 2 )

        bytag = dend0.getDendsByTag('foo.bar.0')
        self.assertEqual( len(bytag), 1 )

    def test_neuron_usepki_basics(self):
        net = self.initNeuNet(usepki=True)

        net.neu3.share('foo',FooBar())

        dend = s_neuron.openlink(net.link0)

        path = '%s/foo' % (net.neu3.iden,)
        prox = dend.open(path)

        task = ('foo',(30,),{})

        job = dend.call( net.neu3.iden, 'foo', task )

        self.assertIsNotNone(job)

        self.assertEqual( dend.sync(job), 50)

        self.assertEqual( prox.foo(11), 31 )

        data = {}
        def ondone(j):
            data['ret'] = s_async.jobret(j)

        job = prox.foo(12, ondone=ondone)

        self.assertEqual( dend.sync(job), 32 )
        self.assertEqual( data.get('ret'), 32 )

        self.finiNeuNet(net)

class TempDisabled:

    def getNeuNet(self):

        env = TestEnv()

        dmon = s_daemon.Daemon()
        env.add('dmon',dmon,fini=True)

        link = dmon.listen('tcp://127.0.0.1:0/')

        neu0 = s_neuron.Neuron()

        env.add('neu0', s_neuron.Neuron(), fini=True)
        env.add('neu1', s_neuron.Neuron(), fini=True)
        env.add('neu2', s_neuron.Neuron(), fini=True)

        env.dmon.share('neu0', env.neu0)
        env.dmon.share('neu1', env.neu1)
        env.dmon.share('neu2', env.neu2)

        #dmon.onfini( neu0.fini )
        #dmon.onfini( neu1.fini )
        #dmon.onfini( neu2.fini )

        #dmon.share('neu0',neu0)
        #dmon.share('neu1',neu1)
        #dmon.share('neu2',neu2)

        port = link[1].get('port')

        env.add('neup0', s_telepath.openurl('tcp://127.0.0.1/neu0', port=port), fini=True)
        env.add('neup1', s_telepath.openurl('tcp://127.0.0.1/neu1', port=port), fini=True)
        env.add('neup2', s_telepath.openurl('tcp://127.0.0.1/neu2', port=port), fini=True)

        wai0 = self.getTestWait(env.neu1, 1, 'neu:link:init')
        env.neu0.link( env.neup1 )
        wai0.wait()

        wai0 = self.getTestWait(env.neu1, 1, 'neu:link:init')
        env.neu0.link( env.neup2 )
        wai0.wait()

        return env

    def test_neuron_route(self):

        neu0 = s_neuron.Neuron()
        neu1 = s_neuron.Neuron()
        neu2 = s_neuron.Neuron()

        neu0.link( neu1 )
        neu0.link( neu2 )

        wait0 = self.getTestWait(neu1, 1, 'woot')
        neu2.route( neu1.getIden(), 'woot', x=10)

        events = wait0.wait()
        self.assertEqual( events[0][1].get('x'), 10 )

        neu0.fini()
        neu1.fini()
        neu2.fini()

    def test_neuron_storm(self):

        neu0 = s_neuron.Neuron()
        neu1 = s_neuron.Neuron()
        neu2 = s_neuron.Neuron()

        neu0.link( neu1 )
        neu0.link( neu2 )

        wai0 = self.getTestWait(neu1, 1, 'woot')

        neu2.storm('woot', x=10)

        events = wai0.wait()
        self.assertEqual( events[0][1].get('x'), 10 )

        neu0.fini()
        neu1.fini()
        neu2.fini()

    def test_neuron_ping(self):
        env = self.getNeuNet()

        dend = s_neuron.Dendrite(env.neup1)
        info = dend.ping(env.neu2.getIden())

        self.assertIsNotNone( info.get('shared') )

        env.fini()

    def test_neuron_call(self):

        env = self.getNeuNet()
        #dmon,neu,pxy = self.getNeuNet()

        env.neu2.share('foo',FooBar())

        dend = s_neuron.Dendrite(env.neup1)

        path = '%s/foo' % (env.neup2.getIden(),)
        foo = dend.open(path)

        self.assertEqual( foo.foo(10), 30 )

        e = threading.Event()
        data = {}
        def jobdone(job):
            data['ret'] = s_async.jobret(job)
            e.set()

        foo.foo(20, onfini=jobdone)
        e.wait(timeout=3)

        self.assertEqual( data.get('ret'), 40 )
        envi.fini()

    def test_neuron_sess(self):

        env = self.getNeuNet()
        #dmon,neu,pxy = self.getNeuNet()

        iden2 = env.neu2.getIden()
        env.neu2.share('foo',FooBar())

        dend0 = s_neuron.Client(env.neup1)
        dend1 = s_neuron.Client(env.neup1)

        self.assertIsNotNone( dend0.getSidByIden(iden2) )

        foo0 = dend0.open((iden2,None),'foo')
        foo1 = dend1.open((iden2,None),'foo')

        self.assertIsNone( foo0.getsess('hehe') )
        self.assertIsNone( foo1.getsess('hehe') )

        foo0.setsess('hehe','lulz')

        self.assertIsNone( foo1.getsess('hehe') )
        self.assertEqual( foo0.getsess('hehe'), 'lulz' )

        env.fini()

    def test_neuron_dend_find(self):
        env = self.getNeuNet()

        foo = FooBar()

        dend0 = s_neuron.Client(env.neup1)

        env.fini()

    def test_neuron_usepki_call(self):

        env = self.getNeuNet(usepki=True)
        #dmon,neu,pxy = self.getNeuNet()

        env.neu2.share('foo',FooBar())

        dend = s_neuron.Dendrite(env.neup1)

        path = '%s/foo' % (env.neup2.getIden(),)
        foo = dend.open(path)

        self.assertEqual( foo.foo(10), 30 )

        e = threading.Event()
        data = {}
        def jobdone(job):
            data['ret'] = s_async.jobret(job)
            e.set()

        foo.foo(20, onfini=jobdone)
        e.wait(timeout=3)

        self.assertEqual( data.get('ret'), 40 )
        envi.fini()
