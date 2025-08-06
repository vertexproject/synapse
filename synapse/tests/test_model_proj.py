import synapse.exc as s_exc
import synapse.tests.utils as s_test

class ProjModelTest(s_test.SynTest):

    async def test_model_proj(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ proj:project=*
                    :name=woot
                    :desc=Woot
                    :type=dfir.case
                    :creator=root
                    :created=20250716
                ]
            ''')
            self.eq(nodes[0].get('name'), 'woot')
            self.eq(nodes[0].get('desc'), 'Woot')
            self.eq(nodes[0].get('type'), 'dfir.case.')
            self.eq(nodes[0].get('creator'), core.auth.rootuser.iden)
            self.eq(nodes[0].get('created'), 1752624000000000)

            nodes = await core.nodes('''
                [ proj:sprint=*
                    :name=Foobar
                    :desc=FooBar
                    :project={ proj:project:name=woot }
                    :status=planned
                    :period=(20250714, 20250719)
                    :creator=root
                    :created=20250716
                ]
            ''')
            self.eq(nodes[0].get('name'), 'Foobar')
            self.eq(nodes[0].get('desc'), 'FooBar')
            self.eq(nodes[0].get('status'), 'planned')
            self.eq(nodes[0].get('creator'), core.auth.rootuser.iden)
            self.eq(nodes[0].get('created'), 1752624000000000)
            self.eq(nodes[0].get('period'), (1752451200000000, 1752883200000000, 432000000000))

            self.len(1, await core.nodes('proj:sprint :project -> proj:project'))

            nodes = await core.nodes('''
                [ proj:task=*

                    :name=syn3.0
                    :desc=FooBar
                    :type=hehe.haha

                    :sprint={ proj:sprint }
                    :project={ proj:project }

                    :creator=root
                    :assignee=root
                    :created=20250716
                    :completed=20250716

                    +(has)> {[ file:attachment=* ]}
                    <(about)+ {[ meta:note=* ]}
                ]
            ''')
            self.eq(nodes[0].get('name'), 'syn3.0')
            self.eq(nodes[0].get('desc'), 'FooBar')
            self.eq(nodes[0].get('type'), 'hehe.haha.')
            self.eq(nodes[0].get('creator'), core.auth.rootuser.iden)
            self.eq(nodes[0].get('assignee'), core.auth.rootuser.iden)
            self.eq(nodes[0].get('created'), 1752624000000000)
            self.eq(nodes[0].get('completed'), 1752624000000000)

            self.len(1, await core.nodes('proj:task :sprint -> proj:sprint'))
            self.len(1, await core.nodes('proj:task :project -> proj:project'))
            self.len(1, await core.nodes('proj:task -(has)> file:attachment'))
            self.len(1, await core.nodes('proj:task <(about)- meta:note'))
