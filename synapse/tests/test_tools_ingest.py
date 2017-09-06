import json

from synapse.tests.common import *

import synapse.daemon as s_daemon
import synapse.cortex as s_cortex
import synapse.tools.ingest as s_ingest

class TestIngest(SynTest):

    def test_tools_ingest(self):

        with s_daemon.Daemon() as dmon:

            link = dmon.listen('tcp://127.0.0.1:0/')

            with s_cortex.openurl('ram:///') as core:

                dmon.share('core', core)

                curl = 'tcp://127.0.0.1:%d/core' % link[1].get('port')

                with self.getTestDir() as dirn:

                    csvpath = os.path.join(dirn, 'woot.csv')
                    jsonpath = os.path.join(dirn, 'ingest.json')
                    syncpath = os.path.join(dirn, 'woot.sync')

                    gest = {
                        'sources': [
                            [csvpath, {'open': {'format': 'csv'},
                                       'ingest': {'forms': [['inet:ipv4', {'path': '1'}]]},
                                       'tags': ['haha']
                                       }
                             ],
                        ],
                    }

                    with genfile(csvpath) as fd:
                        fd.write(b'foo.com,1.2.3.4\n')
                        fd.write(b'bar.com,4.5.6.7\n')

                    with genfile(jsonpath) as fd:
                        fd.write(json.dumps(gest).encode('utf8'))

                    outp = self.getTestOutp()
                    argv = ['--sync', curl, '--save', syncpath, '--verbose', '--progress', jsonpath]
                    self.eq(s_ingest.main(argv, outp=outp), 0)

                    self.isin('add: inet:ipv4=', str(outp))
                    self.isin('add: syn:tag=haha', str(outp))

                    tufo = core.getTufoByProp('inet:ipv4', 0x01020304)
                    self.eq(tufo[1].get('inet:ipv4'), 0x01020304)

                    tag = core.getTufoByProp('syn:tag', 'haha')
                    self.nn(tag)

                    # Ensure we cannot ingest into the remote core directly
                    outp = self.getTestOutp()
                    argv = ['--core', curl, jsonpath]
                    self.raises(MustBeLocal, s_ingest.main, argv, outp=outp)
                    self.isin('Ingest requires a local cortex to deconflict against, not a Telepath proxy', str(outp))
