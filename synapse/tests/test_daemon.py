import io
import os
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

from synapse.tests.common import *


class Woot:
    def foo(self,x,y=20):
        return x + y

    def pid(self):
        return os.getpid()

class Blah:
    def __init__(self, woot):
        self.woot = woot

class DaemonTest(SynTest):

    def test_daemon_timeout(self):

        daemon = s_daemon.Daemon()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.assertEqual( sock.recvobj(),None)

        sock.fini()
        daemon.fini()

    def test_daemon_on(self):

        class Foo:
            def bar(self):
                return 'baz'

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/')

        bus = s_eventbus.EventBus()
        foo = Foo()

        dmon.share('bus', bus)
        dmon.share('foo', foo)

        port = link[1].get('port')

        bprox = s_telepath.openurl('tcp://127.0.0.1/bus', port=port)
        fprox = s_telepath.openurl('tcp://127.0.0.1/foo', port=port)

        evt = threading.Event()
        def woot(mesg):
            evt.set()

        bprox.on('woot', woot)
        fprox.on('woot', woot)

        bus.fire('woot')

        evt.wait(timeout=2)

        fprox.off('woot', woot)

        self.assertTrue( evt.is_set() )

    def test_daemon_conf(self):

        class DmonConfTest(s_daemon.DmonConf,s_eventbus.EventBus):

            def __init__(self):
                s_eventbus.EventBus.__init__(self)
                s_daemon.DmonConf.__init__(self)

        conf = {

            'vars':{
                'hehe':10,
            },
            'ctors':(
                ('woot','ctor://synapse.tests.test_daemon.Woot()'),
                ('blah','ctor://synapse.tests.test_daemon.Blah(woot)'),
            ),
        }

        dcon = DmonConfTest()
        dcon.loadDmonConf(conf)

        self.assertEqual( dcon.locs.get('hehe'), 10 )
        self.assertEqual( dcon.locs.get('woot').foo(10,y=30), 40 )
        self.assertEqual( dcon.locs.get('blah').woot.foo(10,y=30), 40 )

    def test_daemon_conf_onfini(self):

        conf = {
            'ctors': (
                ('fini', 'ctor://synapse.eventbus.EventBus()'),
            ),
            'share': (
                ('fini', {'onfini': True}),
            ),
        }

        dmon = s_daemon.Daemon()
        dmon.loadDmonConf(conf)
        dmon.fini()
        self.assertTrue(dmon.shared.get('fini').isfini)

    def test_daemon_conf_fork(self):
        self.thisHostMustNot(platform='windows')

        iden = guid()

        conf = {
            'forks':(
                ('fork0',{
                    'ctors':(
                        ('haha','ctor://synapse.tests.test_daemon.Woot()'),
                    ),
                    'share': (
                        ('haha',{}),
                    ),
                    'listen':(
                        'local://%s' % (iden,),
                    ),
                }),
            ),
        }

        dmon = s_daemon.Daemon()
        dmon.loadDmonConf(conf)

        prox = s_telepath.openurl('local://%s/haha?retry=6' % (iden,))

        pid0 = prox.pid()
        self.assertNotEqual( pid0, os.getpid() )

        prox.fini()

        #dmon.killDmonFork('fork0')

        #prox = s_telepath.openurl('local://%s/haha?retry=6' % (iden,))

        #pid1 = prox.pid()
        #self.assertNotEqual( pid0, pid1 )
        #self.assertNotEqual( pid1, os.getpid() )

        #prox.fini()
        dmon.fini()

    def test_daemon_sessconf(self):

        with self.getTestDir() as dirname:

            dmon = s_daemon.Daemon()

            conf = {
                'sessions':{
                    'maxtime':99999,
                    'savefile':os.path.join(dirname,'sessions.sql3'),
                },
            }

            dmon.loadDmonConf(conf)

            sess0 = dmon.getNewSess()
            iden = sess0.iden

            sess0.put('woot',10)

            dmon.fini()

            dmon = s_daemon.Daemon()
            dmon.loadDmonConf(conf)

            sess1 = dmon.getSessByIden(iden)
            self.eq( sess1.get('woot'), 10 )

            dmon.fini()

    def test_daemon_ctor_config(self):

        conf = {

            'ctors':(
                ('foo','ctor://synapse.cortex.openurl("ram://")', {'config':'woot'}),
                ('bar','ctor://synapse.cortex.openurl("ram://")', {'configs':('woot','blah')}),
            ),

            'configs':{
                'woot':{},
            }

        }

        with s_daemon.Daemon() as dmon:
            self.assertRaises(NoSuchConf, dmon.loadDmonConf, conf )

        conf['configs']['blah'] = {'newp':1}

        with s_daemon.Daemon() as dmon:
            self.assertRaises(NoSuchOpt, dmon.loadDmonConf, conf )

        conf['configs']['blah'].pop('newp',None)
        conf['configs']['blah']['caching'] = 'TRUE'

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            core = dmon.locs.get('bar')
            self.eq( core.caching, 1 )

