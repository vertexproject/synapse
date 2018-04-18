import random

import synapse.dyndeps as s_dyndeps

from synapse.tests.common import *

logger = logging.getLogger(__name__)


class Woot:
    def foo(self, x, y=20):
        return x + y

    def pid(self):
        return os.getpid()

    def getSet(self):
        s = {1, 2}
        return s

class Blah:
    def __init__(self, woot):
        self.woot = woot

class WokeApi:

    def __init__(self, woke):
        self.woke = woke

    def hehe(self, x):
        return x + 20

class Woke(s_telepath.Aware):

    def getTeleApi(self, dmon):
        return WokeApi(self)

class DaemonTest(SynTest):

    def test_daemon_error_unserializable(self):
        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/')
        port = link[1].get('port')

        woot = Woot()
        dmon.share('woot', woot)
        flag = False

        with s_telepath.openurl('tcp://127.0.0.1/woot', port=port) as wprox:
            try:
                # Ask for a unserializaoble object. Don't do this in real code.
                blah = wprox.getSet()
            except SynErr as e:
                flag = True
                self.eq(e.errinfo.get('excname'), 'TypeError')
                self.isin('msgpack', e.errinfo.get('errfile'))
                # The following line will fail if the msgpack.fallpack serializer is used.
                self.isin("can't serialize", e.errinfo.get('errmsg'))
        self.true(flag)
        dmon.fini()

    def test_daemon_timeout(self):

        daemon = s_daemon.Daemon()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.eq(sock.recvobj(), None)

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

        self.true(evt.is_set())

        fprox.fini()
        bprox.fini()
        dmon.fini()

    def test_daemon_conf(self):

        class DmonConfTest(s_daemon.DmonConf, s_eventbus.EventBus):

            def __init__(self):
                s_eventbus.EventBus.__init__(self)
                s_daemon.DmonConf.__init__(self)

        conf = {

            'vars': {
                'hehe': 10,
            },
            'ctors': (
                ('woot', 'ctor://synapse.tests.test_daemon.Woot()'),
                ('blah', 'ctor://synapse.tests.test_daemon.Blah(woot)'),
            ),
            'modules': (
                ('synapse.tests.nopmod', {}),
            ),
        }

        dcon = DmonConfTest()
        dcon.loadDmonConf(conf)

        self.eq(dcon.locs.get('hehe'), 10)
        self.eq(dcon.locs.get('woot').foo(10, y=30), 40)
        self.eq(dcon.locs.get('blah').woot.foo(10, y=30), 40)
        self.nn(sys.modules.get('synapse.tests.nopmod'))

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
        self.true(dmon.shared.get('fini').isfini)

    def test_daemon_conf_fork(self):
        self.thisHostMustNot(platform='windows')

        iden = guid()

        conf = {
            'forks': (
                ('fork0', {
                    'ctors': (
                        ('haha', 'ctor://synapse.tests.test_daemon.Woot()'),
                    ),
                    'share': (
                        ('haha', {}),
                    ),
                    'listen': (
                        'local://%s' % (iden,),
                    ),
                }),
            ),
        }

        dmon = s_daemon.Daemon()
        dmon.loadDmonConf(conf)

        prox = s_telepath.openurl('local://%s/haha?retry=20' % (iden,))

        pid0 = prox.pid()
        self.ne(pid0, os.getpid())

        prox.fini()
        dmon.fini()

    def test_daemon_ctor_config(self):

        conf = {

            'ctors': (
                ('foo', 'ctor://synapse.cortex.openurl("ram://")', {'config': 'woot'}),
                ('bar', 'ctor://synapse.cortex.openurl("ram://")', {'configs': ('woot', 'blah')}),
            ),

            'configs': {
                'woot': {},
            }

        }

        with s_daemon.Daemon() as dmon:
            self.raises(NoSuchConf, dmon.loadDmonConf, conf)

        conf['configs']['blah'] = {'newp': 1}

        with s_daemon.Daemon() as dmon:
            self.raises(NoSuchOpt, dmon.loadDmonConf, conf)

        conf['configs']['blah'].pop('newp', None)
        conf['configs']['blah']['caching'] = 'TRUE'

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            core = dmon.locs.get('bar')
            self.eq(core.caching, 1)

    def test_daemon_fini_items(self):
        conf = {

            'ctors': (
                ('foo', 'ctor://synapse.cortex.openurl("ram://")'),
                ('alias', 'syn:cortex', {'caching': 1, 'url': 'ram://'}),
            )
        }
        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)

        # Ensure that we fini'd the objects specified with onfini in the ctors
        self.true(dmon.locs.get('foo').isfini)
        self.true(dmon.locs.get('alias').isfini)

    def test_daemon_ctor_nonurl(self):

        s_dyndeps.addDynAlias('test:blah', Blah)

        conf = {
            'ctors': (
                ('foo', 'test:blah', {'lulz': 'rofl'}),
            ),
        }

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            item = dmon.locs.get('foo')
            self.eq(item.woot.get('lulz'), 'rofl')

        s_dyndeps.delDynAlias('test:blah')

    def test_daemon_ctor_dmonurl(self):

        conf = {
            'ctors': [
                ('thing0', 'synapse.tests.test_daemon.Blah', {'lulz': 'hehe'}),
                ('thing1', 'test:check:blah', {}),
            ],
        }

        self.raises(NoSuchName, s_telepath.openurl, 'dmon://thing0')

        with s_daemon.Daemon() as dmon:

            def checkblah(conf):
                self.eq(dmon.locs.get('thing0'), s_telepath.openurl('dmon://thing0'))
                self.raises(NoSuchName, s_telepath.openurl, 'dmon://newp0/')
                return 1

            s_dyndeps.addDynAlias('test:check:blah', checkblah)

            dmon.loadDmonConf(conf)

            s_dyndeps.delDynAlias('test:check:blah')

    def test_daemon_cells(self):

        with self.getTestDir() as dirn:
            celldir1 = os.path.join(dirn, 'cell1')
            celldir2 = os.path.join(dirn, 'cell2')
            port1 = random.randint(10000, 50000)
            port2 = random.randint(10000, 50000)

            conf = {
                'cells': [
                    (celldir1, {'ctor': 'synapse.lib.cell.Cell',
                                'port': port1,
                                'host': '127.0.0.1',
                                }),
                    (celldir2, {'ctor': 'synapse.lib.cell.Cell',
                                'port': port2,
                                'host': '127.0.0.1',
                                }),
                ],
            }

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            with genfile(celldir1, 'cell.lock') as fd:
                self.true(checkLock(fd, 30))
            with genfile(celldir2, 'cell.lock') as fd:
                self.true(checkLock(fd, 30))

        # ensure dmon cell processes are fini'd
        for celldir, proc in dmon.cellprocs.items():
            self.false(proc.is_alive())

    def test_daemon_aware(self):

        woke = Woke()
        with s_daemon.Daemon() as dmon:
            dmon.share('woke', woke)
            self.true(isinstance(dmon.shared.get('woke'), WokeApi))
