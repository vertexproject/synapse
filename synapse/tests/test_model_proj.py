import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_test

class ProjModelTest(s_test.SynTest):

    async def test_model_proj(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ proj:project=*
                    :name=woot
                    :desc=Woot
                    :type=dfir.case
                    :creator={[ syn:user=root ]}
                    :created=20250716
                    :platform={[ inet:service:platform=* ]}
                ]
            ''')
            self.propeq(nodes[0], 'name', 'woot')
            self.propeq(nodes[0], 'desc', 'Woot')
            self.propeq(nodes[0], 'type', 'dfir.case.')
            self.propeq(nodes[0], 'creator', ('syn:user', core.auth.rootuser.iden))
            self.propeq(nodes[0], 'created', 1752624000000000)
            self.nn(nodes[0].get('platform'))

            nodes = await core.nodes('''
                [ proj:sprint=*
                    :name=Foobar
                    :desc=FooBar
                    :project={ proj:project:name=woot }
                    :status=planned
                    :period=(20250714, 20250719)
                    :creator={[ syn:user=root ]}
                    :created=20250716
                ]
            ''')
            self.propeq(nodes[0], 'name', 'Foobar')
            self.propeq(nodes[0], 'desc', 'FooBar')
            self.propeq(nodes[0], 'status', 'planned')
            self.propeq(nodes[0], 'creator', ('syn:user', core.auth.rootuser.iden))
            self.propeq(nodes[0], 'created', 1752624000000000)
            self.propeq(nodes[0], 'period', (1752451200000000, 1752883200000000, 432000000000))

            self.len(1, await core.nodes('proj:sprint :project -> proj:project'))

            nodes = await core.nodes('''
                [ proj:task=*

                    :name=syn3.0
                    :desc=FooBar
                    :type=hehe.haha

                    :sprint={ proj:sprint }
                    :project={ proj:project }

                    :creator={[ syn:user=root ]}
                    :assignee={[ syn:user=root ]}

                    :created=20250716
                    :completed=20250716

                    +(has)> {[ file:attachment=* ]}
                    <(about)+ {[ meta:note=* ]}
                ]
            ''')
            self.propeq(nodes[0], 'name', 'syn3.0')
            self.propeq(nodes[0], 'desc', 'FooBar')
            self.propeq(nodes[0], 'type', 'hehe.haha.')
            self.propeq(nodes[0], 'creator', ('syn:user', core.auth.rootuser.iden))
            self.propeq(nodes[0], 'assignee', ('syn:user', core.auth.rootuser.iden))
            self.propeq(nodes[0], 'created', 1752624000000000)
            self.propeq(nodes[0], 'completed', 1752624000000000)

            self.len(1, await core.nodes('proj:task :sprint -> proj:sprint'))
            self.len(1, await core.nodes('proj:task :project -> proj:project'))
            self.len(1, await core.nodes('proj:task -(has)> file:attachment'))
            self.len(1, await core.nodes('proj:task <(about)- meta:note'))
