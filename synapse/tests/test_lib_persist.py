import threading

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.const as s_const
import synapse.lib.queue as s_queue
import synapse.lib.persist as s_persist

import synapse.tests.common as s_test

class TstQ(s_persist.QueueBase):
    pass

class PersistTest(s_test.SynTest):

    def test_validate(self):
        conf = ('clownQueue', {'type': 'cryotank',
                               'desc': 'A queue for clowns.',
                               'url': 'tcp://pennywise:floaties@1.2.3.4:8080/cryo/clown:v1',
                               })
        self.true(s_persist.validate(conf))
        # No type - so None.validate() fails
        self.raises(s_exc.NoSuchName, s_persist.validate, (None, {}))
        # Bad name in conf
        self.raises(s_exc.BadConfValu, s_persist.validate, (None, {'type': 'cryotank'}))
        # cryotank checks default implementation first which requires a name.
        self.raises(s_exc.BadConfValu, s_persist.validate, ('newp', {'type': 'cryotank'}))

    def test_add_get(self):
        s_persist.add('test', TstQ)
        ret = s_persist.getQueues()
        queues = {name: path for name, path in ret}
        self.isin('cryotank', queues)
        self.isin('test', queues)
        self.eq(queues.get('test'), 'synapse.tests.test_lib_persist.TstQ')
        self.raises(s_exc.NoSuchImpl, s_persist.queue, ('tst', {'type': 'test'}), [])

    def test_queue_cryotank(self):
        with self.getTestDmon(mirror='cryodmon') as dmon:
            host, port = dmon.addr
            url = f'tcp://{host}:{port}/cryo00/queue:t1'
            conf = ('qt1', {'url': url,
                            'type': 'cryotank',
                            'desc': 'A test queue backed by a CryoTank.'})
            rec = {'hehe': 1}
            self.true(s_persist.validate(conf))
            s_persist.queue(conf, [rec])
            with dmon._getTestProxy('cryo00') as prox:
                d = {k: v for k, v in prox.list()}
                self.eq(d.get('queue:t1').get('indx'), 1)
                self.eq(list(prox.slice('queue:t1', 0, 10)), [(0, rec)])

            # Sad path test - fail on a telepath error.
            # That is easier to setup than breaking on a cryotank error.
            conf[1]['url'] = f'tcp://{host}:{port}/cryo01'
            self.raises(s_exc.NoSuchName, s_persist.queue, conf, [rec])
            conf[1]['type'] = 'newp'
            self.raises(s_exc.NoSuchName, s_persist.queue, conf, [rec])

        burl = 'tcp://1.2.3.4:8000/someCryo'
        self.raises(s_exc.BadConfValu, s_persist.validate, ('qt2,', {'type': 'cryotank',
                                                                     'name': 'qt2',
                                                                     'url': burl}))
        burl = 'tcp://1.2.3.4:8000/someCryo/'
        self.raises(s_exc.BadConfValu, s_persist.validate, ('qt2,', {'type': 'cryotank',
                                                                     'name': 'qt2',
                                                                     'url': burl}))
        burl = 'tcp://1.2.3.4:8000/someCryo/tank1/wut'
        self.raises(s_exc.BadConfValu, s_persist.validate, ('qt2,', {'type': 'cryotank',
                                                                     'name': 'qt2',
                                                                     'url': burl}))

    def test_storm_queue_cryotank(self):
        with self.getTestDmon(mirror='cryodmon') as dmon:
            host, port = dmon.addr
            url = f'tcp://{host}:{port}/cryo00/qt1'
            conf = ('qt1', {'type': 'cryotank',
                            'desc': 'A test tank.',
                            'url': url})

            with self.getTestCore() as core:
                q = 'queue -l'
                mesgs = list(core.storm(q))
                self.eq(mesgs[1][1].get('mesg'), 'No queues are configured for the current Cortex.')

                # Add a queue and show that it is present.
                core.addQueue(conf)
                self.eq(core.getQueueDescs(), [('qt1', {'type': 'cryotank', 'desc': 'A test tank.'})])

                q = 'queue -l'
                mesgs = list(core.storm(q))
                mesg = mesgs[2][1].get('mesg')
                self.isin('qt1', mesg)

                q = '[teststr=foobar teststr=haha] | queue qt1'
                mesgs = list(core.storm(q))
                with dmon._getTestProxy('cryo00') as cryo:
                    tanks = cryo.list()
                    tanks = {k: v for k, v in tanks}
                    self.len(1, tanks)
                    self.eq(tanks.get('qt1').get('indx'), 2)
                    recs = list(cryo.slice('qt1', 0, 10))
                    self.len(2, recs)
                    for rec in recs:
                        offset, data = rec
                        self.isnode(data)

                # A non-configured queue throws an error
                q = 'tststr | queue qt2'
                mesgs = list(core.storm(q))
                self.len(3, mesgs)
                err = ('err', ('NoSuchConf', {
                    'mesg': 'Cortex is not configured for queuing to the specified endpoint.',
                    'name': 'qt2'}))
                self.eq(mesgs[1], err)
