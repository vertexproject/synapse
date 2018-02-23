from synapse.tests.common import *

import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.neuron as s_neuron

import synapse.tools.pushfile as s_pushfile

nullhash = hashlib.sha256(b'').digest()
visihash = hashlib.sha256(b'visi').digest()

class TestPushFile(SynTest):

    def test_tools_pushfile(self):
        self.skipLongTest()
        with self.getAxonCore() as env:

            nullpath = os.path.join(env.dirn, 'null.txt')
            visipath = os.path.join(env.dirn, 'visi.txt')
            with open(visipath, 'wb') as fd:
                fd.write(b'visi')

            with s_daemon.Daemon() as dmon:

                dmonlink = dmon.listen('tcp://127.0.0.1:0/')
                dmonport = dmonlink[1].get('port')
                dmon.share('core', env.core)

                coreurl = 'tcp://127.0.0.1:%d/core' % dmonport

                outp = self.getTestOutp()
                s_pushfile.main(['--tags', 'foo.bar,baz.faz', coreurl, visipath], outp=outp)

                node = env.core.getTufoByProp('file:bytes')
                self.eq(node[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
                self.eq(node[1].get('file:bytes:size'), 4)
                self.nn(node[1].get('#foo'))
                self.nn(node[1].get('#foo.bar'))
                self.nn(node[1].get('#baz'))
                self.nn(node[1].get('#baz.faz'))

                # Ensure the axon got the bytes
                self.eq(env.axon_client.wants((visihash,)), ())
                self.eq(list(env.axon_client.bytes(visihash))[0], b'visi')

                # Ensure user can't push a non-existant file and that it won't exist
                self.raises(FileNotFoundError, s_pushfile.main, ['--tags', 'foo.bar,baz.faz', coreurl, nullpath], outp=outp)
                self.eq(env.axon_client.wants((nullhash,)), (nullhash,))

                # Ensure user can push an empty file
                with open(nullpath, 'wb') as fd:
                    fd.write(b'')
                outp = self.getTestOutp()
                s_pushfile.main(['--tags', 'foo.bar,baz.faz', coreurl, nullpath], outp=outp)
                node = env.core.getTufoByProp('file:bytes:sha256', ehex(nullhash))
                self.istufo(node)
                self.eq(env.axon_client.wants((nullhash,)), ())
                self.eq(list(env.axon_client.bytes(nullhash)), [b''])
