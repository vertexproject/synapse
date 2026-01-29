import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class PlanModelTest(s_t_utils.SynTest):

    async def test_model_planning(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ plan:system=*
                    :name="Woot CNO Planner"
                    :author={[ ps:contact=* :name=visi ]}
                    :created=20240202
                    :updated=20240203
                    :version=1.0.0
                    :url=https://vertex.link
                ]
            ''')
            self.len(1, nodes)
            self.eq('woot cno planner', nodes[0].get('name'))
            self.eq(1706832000000, nodes[0].get('created'))
            self.eq(1706918400000, nodes[0].get('updated'))
            self.eq(1099511627776, nodes[0].get('version'))
            self.eq('https://vertex.link', nodes[0].get('url'))

            self.len(1, await core.nodes('plan:system :author -> ps:contact +:name=visi'))

            nodes = await core.nodes('''
                [ plan:phase=*
                    :system={ plan:system:name="Woot CNO Planner"}
                    :title="Recon"
                    :summary="Do some recon."
                    :index=17
                    :url=https://vertex.link/recon
                ]
            ''')

            self.len(1, nodes)
            self.eq('Recon', nodes[0].get('title'))
            self.eq('Do some recon.', nodes[0].get('summary'))
            self.eq(17, nodes[0].get('index'))
            self.eq('https://vertex.link/recon', nodes[0].get('url'))

            self.len(1, await core.nodes('plan:phase :system -> plan:system +:name="Woot CNO Planner"'))

            nodes = await core.nodes('''
                [ plan:procedure=*
                    :system={ plan:system:name="Woot CNO Planner"}
                    :title="Pwn Some Boxes"
                    :summary="Yoink."
                    :author={ ps:contact:name=visi }
                    :created=20240202
                    :updated=20240203
                    :version=1.0.0
                    :type=cno.offense
                    :system={ plan:system:name="Woot CNO Planner" }
                ]

                $guid = $node.value()

                [
                    :inputs={[ plan:procedure:variable=*
                        :name=network
                        :type=cidr
                        :default=127.0.0.0/24
                        :procedure=$guid
                    ]}

                    :firststep={[ plan:procedure:step=*
                        :title="Are there vulnerable services?"
                        :summary="Scan the target network and identify available services."
                        :procedure=$guid
                        :phase={ plan:phase:title=Recon }
                        :outputs={[ plan:procedure:variable=* :name=services ]}
                        :techniques={[ ou:technique=* :name=netscan ]}

                        :links={[ plan:procedure:link=*
                            :condition=(true)
                            :procedure=$guid
                            :next={[ plan:procedure:step=*
                                :title="Exploit Services"
                                :summary="Gank that stuff."
                                :procedure=$guid
                                :outputs={[ plan:procedure:variable=* :name=shellz ]}
                            ]}

                        ]}
                    ]}
                ]
            ''')

            self.len(1, nodes)
            self.eq('Pwn Some Boxes', nodes[0].get('title'))
            self.eq('Yoink.', nodes[0].get('summary'))
            self.nn(nodes[0].get('author'))
            self.eq(1706832000000, nodes[0].get('created'))
            self.eq(1706918400000, nodes[0].get('updated'))
            self.eq(1099511627776, nodes[0].get('version'))

            self.len(1, await core.nodes('plan:procedure :type -> plan:procedure:type:taxonomy'))
            self.len(1, await core.nodes('plan:procedure :system -> plan:system +:name="Woot CNO Planner"'))
            self.len(1, await core.nodes('plan:procedure :firststep -> plan:procedure:step -> plan:procedure:link'))

            nodes = await core.nodes('plan:procedure :inputs -> plan:procedure:variable')
            self.len(1, nodes)
            self.eq('network', nodes[0].get('name'))
            self.eq('cidr', nodes[0].get('type'))
            self.eq('127.0.0.0/24', nodes[0].get('default'))
            self.nn(nodes[0].get('procedure'))

            nodes = await core.nodes('plan:procedure :firststep -> plan:procedure:step')
            self.len(1, nodes)
            self.eq('Are there vulnerable services?', nodes[0].get('title'))
            self.eq('Scan the target network and identify available services.', nodes[0].get('summary'))
            self.nn(nodes[0].get('procedure'))

            self.len(1, await core.nodes('plan:procedure :firststep -> plan:procedure:step -> plan:phase'))
            self.len(1, await core.nodes('plan:procedure :firststep -> plan:procedure:step :techniques -> ou:technique'))
            self.len(1, await core.nodes('plan:procedure :firststep -> plan:procedure:step :outputs -> plan:procedure:variable'))

            nodes = await core.nodes('plan:procedure :firststep -> plan:procedure:step -> plan:procedure:link')
            self.len(1, nodes)
            self.eq(True, nodes[0].get('condition'))
            self.nn(nodes[0].get('next'))
            self.nn(nodes[0].get('procedure'))
