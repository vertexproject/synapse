import threading

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.const as s_const
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.persist as s_persist

import synapse.tests.common as s_test

class PersistTest(s_test.SynTest):

    def test_add_get(self):
        self.none(s_persist.add('test', print))
        ret = s_persist.getQueues()
        queues = {name: path for name, path in ret}
        self.isin('cryo:cell', queues)
        self.isin('cryo:tank', queues)
        self.isin('test', queues)
        self.eq(queues.get('test'), 'builtins.print')

    def test_storm_task(self):

        # Test cryo:cell configuration. This automatically splits tasks into their own
        # cryotanks, which then need dedicated nommers.
        with self.getTestDmon(mirror='cryodmon') as dmon:
            host, port = dmon.addr
            url = f'tcp://{host}:{port}/cryo00'
            tconf = {'type': 'cryo:cell',
                     'url': url}
            conf = {'task:queue': tconf,
                    'modules': ['synapse.tests.utils.TestModule', ],
                    }
            dirn = s_scope.get('dirn')
            with self.getTestCell(dirn, 'cortex', conf=conf) as core:
                w = core.waiter(1, 'persist:task:cryo:cell')
                q = '[teststr=foobar] [teststr=haha] | task knight ni --kwarg ip 1.2.3.4'
                mesgs = list(core.storm(q))
                self.true(w.wait(5))

                # Validate the task record stored in the cryotank is shaped like the following
                # {
                #   'kwargs': {...},
                #   'node': (a packed node)
                #   'tid': '<guid>',
                #   'tick': 1234..
                #   'user': None or str
                # }
                with dmon._getTestProxy('cryo00') as cryo:
                    tanks = cryo.list()
                    self.len(2, tanks)
                    d = {k: v for k, v in tanks}
                    self.ge(d.get('knight').get('indx'), 1)
                    self.ge(d.get('ni').get('indx'), 1)
                    rec = list(cryo.slice('knight', 0, 1))[0][1]
                    self.isinstance(rec.get('tid'), str)
                    self.isnode(rec.get('node'))
                    self.isinstance(rec.get('tick'), int)
                    # We are not currently in a auth cortex so user is None
                    self.none(rec.get('user', s_common.novalu))
                    # kwargs is a dict
                    self.eq(rec.get('kwargs'), {'ip': '1.2.3.4'})

                # A task can be fired without inbound nodes
                w = core.waiter(1, 'persist:task:cryo:cell')
                q = 'task ipthing --kwarg ip 1.2.3.4'
                mesgs = list(core.storm(q))
                self.true(w.wait(5))
                with dmon._getTestProxy('cryo00') as cryo:
                    d = {k: v for k, v in cryo.list()}
                    self.eq(d.get('ipthing').get('indx'), 1)
                    rec = list(cryo.slice('ipthing', 0, 1))[0][1]
                    # The 'node' field is None if there was no inbound node
                    self.none(rec.get('user', s_common.novalu))

        # Test cryo:tank configuration. This automatically puts all task events
        # into a single tank which is connected to directly.
        with self.getTestDmon(mirror='cryodmon') as dmon:
            host, port = dmon.addr
            url = f'tcp://{host}:{port}/cryo00/tasks'
            tconf = {'type': 'cryo:tank',
                     'url': url}
            conf = {'task:queue': tconf,
                    'modules': ['synapse.tests.utils.TestModule', ],
                    }
            dirn = s_scope.get('dirn')
            with self.getTestCell(dirn, 'cortex', conf=conf) as core:
                w = core.waiter(1, 'persist:task:cryo:tank')
                q = '[teststr=foobar] [teststr=haha] | task knight ni --kwarg ip 1.2.3.4'
                mesgs = list(core.storm(q))
                self.true(w.wait(5))

                # Validate the task record stored in the cryotank is shaped like the following
                # (name,
                #  {
                #    'kwargs': {...},
                #    'node': (a packed node)
                #    'tid': '<guid>',
                #    'tick': 1234..
                #    'user': None or str
                #  })
                with dmon._getTestProxy('cryo00') as cryo:
                    d = {k: v for k, v in cryo.list()}
                    self.eq(d.get('tasks').get('indx'), 4)
                    recs = [rec for offset, rec in cryo.slice('tasks', 0, 10)]
                    rec = recs[0]
                    rectype, rec = rec
                    self.isin(rectype, ['knight', 'ni'])
                    self.isinstance(rec.get('tid'), str)
                    self.isnode(rec.get('node'))
                    self.isinstance(rec.get('tick'), int)
                    # We are not currently in a auth cortex so user is None
                    self.none(rec.get('user', s_common.novalu))
                    # kwargs is a dict
                    self.eq(rec.get('kwargs'), {'ip': '1.2.3.4'})

                    # all the rectypes are accounted for
                    self.eq({rectype for rectype, _ in recs}, {'knight', 'ni'})

        # Null configuration throws an error
        with self.getTestCore() as core:
            q = 'task knight --kwarg ip 1.2.3.4'
            mesgs = list(core.storm(q))
            self.len(3, mesgs)
            err = ('err', ('NoSuchConf', {'mesg': 'Cortex is not configured for tasking.'}))
            self.eq(mesgs[1], err)

    def test_cryo_sadpath(self):
        class PsuedoCortex(s_eventbus.EventBus):
            # Minimial implementation for the built in queue functions to operate.
            def __init__(self):
                s_eventbus.EventBus.__init__(self)
                self.tqueue = s_queue.Queue()
                self.onfini(self.tqueue.fini)

        rec0 = {
            'tick': s_common.now(),
            'user': None,
            'tid': s_common.guid(),
            'node': None,
            'kwargs': {
                'buf': '0' * (s_const.mebibyte - (s_const.kibibyte * 45)),
            }
        },
        rec1 = {
            'tick': s_common.now(),
            'user': None,
            'tid': s_common.guid(),
            'node': None,
            'kwargs': {
                'buf': '0' * 2,
            }
        }
        core = PsuedoCortex()

        with PsuedoCortex() as core:
            with self.getTestDmon(mirror='cryodmon') as dmon:
                host, port = dmon.addr
                url = f'tcp://{host}:{port}/cryo00'
                tconf = {'url': url}
                with dmon._getTestProxy('cryo00') as cryo:
                    cryo.init('test:1', {'mapsize': s_const.mebibyte * 1,
                                         'noindex': True})
                    core.tqueue.put(('test:1', rec0))
                    evt = threading.Event()
                    def boom(mesg):
                        if evt.is_set():
                            return
                        evt.set()
                        core.tqueue.put(('test:1', rec1))

                    core.on('persist:task:cryo:cell', boom)
                    self.raises(s_exc.SynErr, s_persist.cryoCellQueue, core, tconf)

        with PsuedoCortex() as core:
            with self.getTestDmon(mirror='cryodmon') as dmon:
                host, port = dmon.addr
                url = f'tcp://{host}:{port}/cryo00/test:1'
                tconf = {'url': url}
                with dmon._getTestProxy('cryo00') as cryo:
                    cryo.init('test:1', {'mapsize': s_const.mebibyte * 1,
                                         'noindex': True})
                    core.tqueue.put(('test:1', rec0))
                    evt = threading.Event()
                    def boom(mesg):
                        if evt.is_set():
                            return
                        evt.set()
                        core.tqueue.put(('test:1', rec1))

                    core.on('persist:task:cryo:tank', boom)
                    self.raises(s_exc.SynErr, s_persist.cryoTankQueue, core, tconf)
