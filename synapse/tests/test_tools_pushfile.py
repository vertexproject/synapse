from synapse.tests.common import *

import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon

import synapse.tools.pushfile as s_pushfile

class TestPushFile(SynTest):

    def test_tools_pushfile(self):

        with self.getTestDir() as path:

            visipath = os.path.join(path,'visi.txt')

            with open(visipath,'wb') as fd:
                fd.write(b'visi')

            outp = self.getTestOutp()

            with s_daemon.Daemon() as dmon:

                link = dmon.listen('tcp://127.0.0.1:0/')

                port = link[1].get('port')

                core = s_cortex.openurl('ram:///')
                dmon.onfini( core.fini )

                axon = s_axon.Axon(os.path.join(path,'axon00'))
                dmon.onfini( axon.fini )

                dmon.share('axon00', axon)
                dmon.share('core00', core)

                core.setConfOpt('axon:url', 'tcp://127.0.0.1:%d/axon00' % port)

                s_pushfile.main(['--tags','foo.bar,baz.faz','tcp://127.0.0.1:%d/core00' % port, visipath], outp=outp)

                node = core.getTufoByProp('file:bytes')

                self.eq( node[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27' )
                self.eq( node[1].get('file:bytes:size'), 4 )

                self.nn( node[1].get('*|file:bytes|foo') )
                self.nn( node[1].get('*|file:bytes|foo.bar') )
                self.nn( node[1].get('*|file:bytes|baz') )
                self.nn( node[1].get('*|file:bytes|baz.faz') )
