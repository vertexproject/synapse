import time

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.scope as s_scope
import synapse.lib.service as s_service
import synapse.lib.threads as s_threads
import synapse.lib.userauth as s_userauth

from synapse.tests.common import *

class Foo:

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise Exception('derp')

    def echo(self, x):
        return x

    def speed(self):
        return

class TelePathTest(SynTest):

    def getFooServ(self):
        dmon = s_daemon.Daemon()

        link = dmon.listen('tcp://127.0.0.1:0/foo')
        dmon.share('foo',Foo())

        return dmon,link

    def getFooEnv(self, url='tcp://127.0.0.1:0/foo'):
        env = TestEnv()
        env.add('dmon', s_daemon.Daemon(), fini=True)
        env.add('link', env.dmon.listen(url))

        env.dmon.share('foo',Foo())

        return env

    def test_telepath_basics(self):

        env = self.getFooEnv()

        foo = s_telepath.openlink(env.link)

        s = time.time()
        for i in range(1000):
            foo.speed()

        e = time.time()

        self.assertEqual( foo.bar(10,20), 30 )
        self.assertRaises( JobErr, foo.faz, 10, 20 )
        self.assertRaises( JobErr, foo.baz, 10, 20 )

        foo.fini()
        env.fini()

    def test_telepath_chop(self):

        dmon,link = self.getFooServ()

        port = link[1].get('port')

        foo = s_telepath.openurl('tcp://localhost:%d/foo' % (port,))

        self.assertEqual( foo.bar(10,20), 30 )

        foo.fini()
        dmon.fini()

    def test_telepath_nosuchobj(self):
        dmon,link = self.getFooServ()
        port = link[1].get('port')

        newp = s_telepath.openurl('tcp://localhost:%d/newp' % (port,))
        self.assertRaises( JobErr, newp.foo )

        dmon.fini()

    def test_telepath_call(self):
        dmon,link = self.getFooServ()

        foo = s_telepath.openlink(link)

        job = foo.call('bar', 10, 20)
        self.assertIsNotNone( job )

        self.assertEqual( foo.syncjob(job), 30 )

        foo.fini()
        dmon.fini()

    def test_telepath_push(self):

        # override default timeout=None for tests
        with s_scope.enter({'syntimeout':5}):

            env = self.getFooEnv()
            port = env.link[1].get('port')

            prox0 = s_telepath.openurl('tcp://127.0.0.1/', port=port)
            prox0.push('foo1', Foo() )

            prox1 = s_telepath.openurl('tcp://127.0.0.1/foo1', port=port)

            self.eq( prox1.bar(10,20), 30 )

            prox0.fini()

            self.assertRaises( s_async.JobErr, prox1.bar, 10, 20 )

            prox1.fini()

            env.fini()

    def test_telepath_callx(self):

        class Baz:
            def faz(self, x, y=10):
                return '%d:%d' % (x,y)

        env = self.getFooEnv()
        env.dmon.share('baz', Baz())

        port = env.link[1].get('port')
        foo = s_telepath.openurl('tcp://127.0.0.1/foo', port=port)

        # make sure proxy is working normally...
        self.assertEqual( foo.bar(10,20), 30 )

        # carry out a cross item task
        job = foo.callx( 'baz', ('faz', (30,), {'y':40}), )

        self.assertEqual( foo.syncjob(job), '30:40' )

    def test_telepath_fakesync(self):
        env = self.getFooEnv()
        port = env.link[1].get('port')

        class DeadLock(s_eventbus.EventBus):

            def hork(self):
                self.fire('foo:bar')

            def bar(self, x, y):
                return x + y

        dead = DeadLock()
        env.dmon.share('dead',dead)

        data = {}
        evt = threading.Event()

        prox = s_telepath.openurl('tcp://127.0.0.1/dead', port=port)
        def foobar(mesg):
            data['foobar'] = prox.bar(10,20)
            evt.set()

        prox.on('foo:bar', foobar)

        prox.hork()

        evt.wait(timeout=2)

        self.assertEqual( data.get('foobar'), 30 )

        prox.fini()
        dead.fini()
        env.fini()

    def test_telepath_reshare(self):
        env0 = self.getFooEnv()
        env1 = self.getFooEnv()

        port = env0.link[1].get('port')
        prox0 = s_telepath.openurl('tcp://127.0.0.1/foo', port=port)

        env1.dmon.share('bar', prox0)

        port = env1.link[1].get('port')
        prox1 = s_telepath.openurl('tcp://127.0.0.1/bar', port=port)

        self.assertEqual( prox1.bar(33,44), 77 )

        env0.fini()
        env1.fini()

    def test_telepath_eval(self):

        foo = s_telepath.evalurl('ctor://synapse.tests.test_telepath.Foo()')
        self.assertEqual( foo.bar(10,20), 30 )

        env0 = self.getFooEnv()
        port = env0.link[1].get('port')

        foo = s_telepath.evalurl('tcp://127.0.0.1/foo', port=port)
        self.assertEqual( foo.bar(10,20), 30 )

        foo.fini()
        env0.fini()

    def test_telepath_reconnect(self):
        tenv = self.getFooEnv()

        port = tenv.link[1].get('port')
        prox = s_telepath.openurl('tcp://127.0.0.1/foo', port=port)

        url = 'tcp://127.0.0.1:%d/foo' % (port,)
        self.assertEqual( prox.bar(10,20), 30 )

        waiter = self.getTestWait(prox, 1, 'tele:sock:init')

        # shut down the daemon
        tenv.dmon.fini()

        dmon = s_daemon.Daemon()
        dmon.share('foo',Foo())
        dmon.listen(url)

        waiter.wait()

        self.assertEqual( prox.bar(10,20), 30 )

        prox.fini()
        dmon.fini()
        tenv.fini()

    def test_telepath_yielder(self):

        class YieldTest:

            def woot(self):
                yield 10
                yield 20
                yield 30

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/hehe')

        dmon.share('hehe', YieldTest() )

        prox = s_telepath.openlink(link)

        items = []

        for item in prox.woot():
            items.append(item)

        self.assertEqual( tuple(items), (10,20,30) )

        self.assertEqual( len(dmon._dmon_yields), 0 )

        prox.fini()
        dmon.fini()

    def test_telepath_server_badvers(self):

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/')

        rlay = s_link.getLinkRelay(link)

        jid = guid()
        sock = rlay.connect()

        sock.tx( tufo('tele:syn', jid=jid, vers=(0,0)) )

        mesg = sock.recvobj()

        sock.fini()

        self.eq( mesg[0],'job:done')
        self.eq( mesg[1].get('err'), 'BadMesgVers' )

    def test_telepath_gzip(self):

        with s_daemon.Daemon() as dmon:

            link = dmon.listen('tcp://127.0.0.1:0/foo')

            dmon.share('foo', Foo() )

            with s_telepath.openlink(link) as prox:

                wait0 = self.getTestWait(prox, 1, 'sock:gzip')
                #wait1 = self.getTestWait(dmon., 1, 'sock:gzip')

                ping = 'V' * 50000
                self.eq( prox.echo(ping), ping )

                wait0.wait(timeout=2)

    def test_telepath_auth(self):

        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        userkey = getTestPath('user.key')
        usercert = getTestPath('user.crt')

        with s_userauth.opencore('ram:///') as auth:

            with s_daemon.Daemon() as dmon:

                dmon.setUserAuth(auth)

                dmon.share('foo', Foo() )

                link0 = dmon.listen('tcp://localhost:0/')
                link1 = dmon.listen('ssl://localhost:0/', cafile=cafile, keyfile=keyfile, certfile=certfile)

                port0 = link0[1].get('port')
                port1 = link1[1].get('port')

                url = 'ssl://localhost/foo'

                with s_telepath.openurl('tcp://localhost/foo', port=port0) as foo:
                    self.assertRaises( JobErr, foo.bar, 20, 30 )

                with s_telepath.openurl(url, port=port1, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                    self.assertRaises( JobErr, foo.bar, 20, 30 )

                auth.addUser('user@localhost')

                # even with the user added we should fail
                with s_telepath.openurl(url, port=port1, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                    self.assertRaises( JobErr, foo.bar, 20, 30 )

                auth.addUserRule('user@localhost','tele:call:foo:bar')

                # now with a rule we should succeed
                with s_telepath.openurl(url, port=port1, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                    self.eq( foo.bar(10,30), 40 )

                # but echo should still fail
                with s_telepath.openurl(url, port=port1, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                    self.assertRaises( JobErr, foo.echo, 'woot' )

                # until we add a * rule
                auth.addUserRule('user@localhost','tele:call:foo:*')

                # and now it succeeds
                with s_telepath.openurl(url, port=port1, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                    self.eq( foo.echo('woot'), 'woot' )

    def test_telepath_events(self):
        with s_daemon.Daemon() as dmon:
            with s_service.SvcBus() as sbus:
                urlt = 'tcp://127.0.0.1:%d'
                url = urlt % (0)
                link = dmon.listen(url)
                port = link[1].get('port')
                url = urlt % (port)
                dmon.share('sbus', sbus)
                proxy0 = s_telepath.openurl(url + '/sbus')
                proxy1 = s_telepath.openurl(url + '/sbus')
                counters = [0, 0]

                def count(offset):
                    def on(*args, **kwargs):
                        counters[offset] += 1
                    return on

                proxy0.on('tufo:tag:add', count(0))
                proxy1.on('tufo:tag:add', count(1))
                wait = s_eventbus.Waiter(proxy1, 1, 'tufo:tag:add')
                proxy0.fire('tufo:tag:add', tag='tagu', tufo=('iden', {'prop': 'valu'}))
                wait.wait()
                self.assertEqual(counters[0], 1)
                self.assertEqual(counters[1], 1)
