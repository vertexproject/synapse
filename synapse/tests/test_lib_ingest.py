from synapse.tests.common import *

import synapse.cortex as s_cortex
import synapse.lib.ingest as s_ingest

class IngTest(SynTest):

    def test_ingester_basic(self):
        core = s_cortex.openurl('ram://')

        info = {
            'name':'IngTest Ingest',

            'ingest':(
                ( ['foo'], {
                    'forms':(
                        ('inet:fqdn', {
                            'path':['fqdn'],
                            'props':(
                                ('sfx', {'path':['tld']}),
                            ),
                        }),
                    ),
                }),
            ),

            'data':{
                'foo':[
                    {'fqdn':'com','tld':True},
                    {'fqdn':'woot.com'},
                ],

                'bar':[
                    {'fqdn':'vertex.link','tld':0},
                ],

                'newp':[
                    {'fqdn':'newp.com','tld':0},
                ],

            },
        }

        gest= s_ingest.init(info)
        gest.ingest(core)

        self.eq( core.getTufoByProp('inet:fqdn','com')[1].get('inet:fqdn:sfx'), 1 )
        self.eq( core.getTufoByProp('inet:fqdn','woot.com')[1].get('inet:fqdn:zone'), 1 )

        self.assertIsNone( core.getTufoByProp('inet:fqdn','newp.com') )

    def test_ingest_csv(self):

        with s_cortex.openurl('ram://') as core:

            with self.getTestDir() as path:

                csvp = os.path.join(path,'woot.csv')

                with genfile(csvp) as fd:
                    fd.write(b'foo.com,1.2.3.4\n')
                    fd.write(b'vertex.link,5.6.7.8\n')

                info = {
                    'format':'csv',
                    'csv:filepath':csvp,

                    'ingest':(
                        ( (), {
                            'forms':(
                                ('inet:fqdn',{'path':[0]}),
                                ('inet:ipv4',{'path':[1]}),
                            ),
                        }),
                    ),
                }

                gest = s_ingest.init(info)
                gest.ingest(core)

            self.assertIsNotNone( core.getTufoByProp('inet:fqdn','foo.com') )
            self.assertIsNotNone( core.getTufoByProp('inet:fqdn','vertex.link') )
            self.assertIsNotNone( core.getTufoByFrob('inet:ipv4','1.2.3.4') )
            self.assertIsNotNone( core.getTufoByFrob('inet:ipv4','5.6.7.8') )
