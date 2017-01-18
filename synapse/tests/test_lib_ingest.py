from synapse.tests.common import *

import synapse.cortex as s_cortex
import synapse.lib.tufo as s_tufo
import synapse.lib.ingest as s_ingest

class IngTest(SynTest):

    def test_ingest_iteriter(self):
        data = [ ['woot.com'] ]

        # test an iters directive within an iters directive for

        with s_cortex.openurl('ram://') as core:

            info =  {'ingest':{
                        'iters':[
                            ('*/*', {
                                'forms':[
                                    ('inet:fqdn',{}),
                                 ],
                            }),
                        ],
                    }}

            gest = s_ingest.Ingest(info)
            gest.ingest(core,data)

            self.assertIsNotNone( core.getTufoByProp('inet:fqdn','woot.com') )

    def test_ingest_basic(self):

        core = s_cortex.openurl('ram://')

        info = {
            'ingest':{
                'iters':(
                    ('foo/*/fqdn',{
                        'forms':[
                            ('inet:fqdn', {
                                'props':{
                                    'sfx':{'path':'../tld'},
                                }
                            }),
                        ]
                    }),
                ),
            }
        }

        data = {
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

        }

        gest = s_ingest.Ingest(info)

        gest.ingest(core,data)

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

                    'ingest':{

                        'tags':['hehe.haha'],

                        'iters':[
                            ('*', {
                                'forms':[
                                    ('inet:fqdn',{'path':'0'}),
                                    ('inet:ipv4',{'path':'1'}),
                                ]
                            }),
                        ],
                    },
                }

                data = s_ingest.opendata(csvp,**info)

                gest = s_ingest.Ingest(info)

                gest.ingest(core,data=data)

            self.assertIsNotNone( core.getTufoByProp('inet:fqdn','foo.com') )
            self.assertIsNotNone( core.getTufoByProp('inet:fqdn','vertex.link') )
            self.assertIsNotNone( core.getTufoByFrob('inet:ipv4','1.2.3.4') )
            self.assertIsNotNone( core.getTufoByFrob('inet:ipv4','5.6.7.8') )

            self.eq( len( core.eval('inet:ipv4*tag=hehe.haha') ), 2 )
            self.eq( len( core.eval('inet:fqdn*tag=hehe.haha') ), 2 )

    def test_ingest_files(self):

        #s_encoding.encode('utf8,base64,-utf8','
        data = {'foo':['dmlzaQ==']}

        info = {'ingest':{
            'tags':['woo.woo'],
            'files':[ ('foo/*',{'mime':'hehe/haha','decode':'+utf8,base64'}) ],
        }}

        with s_cortex.openurl('ram://') as core:

            gest = s_ingest.Ingest(info)
            gest.ingest(core,data)

            tufo = core.getTufoByProp('file:bytes','442f602ecf8230b2a59a44b4f845be27')

            self.assertTrue( s_tufo.tagged(tufo,'woo.woo') )
            self.eq( tufo[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq( tufo[1].get('file:bytes:mime'), 'hehe/haha' )

        # do it again with an outer iter and non-iter path
        data = {'foo':['dmlzaQ==']}

        info = {'ingest':{
            'tags':['woo.woo'],
            'iters':[
                ('foo/*',{
                    'files':[ ('.',{'mime':'hehe/haha','decode':'+utf8,base64'}) ],
                }),
            ]
        }}

        with s_cortex.openurl('ram://') as core:

            gest = s_ingest.Ingest(info)
            gest.ingest(core,data)

            tufo = core.getTufoByProp('file:bytes','442f602ecf8230b2a59a44b4f845be27')

            self.eq( tufo[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq( tufo[1].get('file:bytes:mime'), 'hehe/haha' )
            self.assertTrue( s_tufo.tagged(tufo,'woo.woo') )

    def test_ingest_pivot(self):

        data = {'foo':['dmlzaQ=='],'bar':[ '1b2e93225959e3722efed95e1731b764'] }

        info = {'ingest':{
            'tags':['woo.woo'],
            'files':[ ('foo/*',{'mime':'hehe/haha','decode':'+utf8,base64'}) ],
            'forms':[ ('hehe:haha',{'path':'bar/*','pivot':('file:bytes:md5','file:bytes')}) ],
        }}

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('hehe:haha', ptype='file:guid')

            gest = s_ingest.Ingest(info)
            gest.ingest(core,data)

            self.assertIsNotNone( core.getTufoByProp('hehe:haha','442f602ecf8230b2a59a44b4f845be27') )

    def test_ingest_template(self):

        data = {'foo':[ ('1.2.3.4','vertex.link') ] }

        info = {'ingest':{
            'forms':[ ('dns:a',{'path':'foo/*','template':('{{fqdn}}/{{ipv4}}', {'ipv4':{'path':'0'},'fqdn':{'path':'1'}}) } ) ],
        }}

        with s_cortex.openurl('ram://') as core:

            gest = s_ingest.Ingest(info)
            gest.ingest(core,data)

            self.assertIsNotNone( core.getTufoByProp('inet:ipv4', 0x01020304 ) )
            self.assertIsNotNone( core.getTufoByProp('inet:fqdn', 'vertex.link') )
            self.assertIsNotNone( core.getTufoByProp('dns:a','vertex.link/1.2.3.4') )
