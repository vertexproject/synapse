import synapse.tests.utils as s_tests

class DocModelTest(s_tests.SynTest):

    async def test_model_doc(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ doc:policy=*
                    :id=V-41
                    :title="Rule 41"
                    :text="If you can AAAAAAAA..."
                    :file=*
                    :created=20241018
                    :updated=20241018
                    :author={[ entity:contact=* :name=visi ]}
                    :contributors={[ entity:contact=* :name=shuka ]}
                    :version=1.2.3
                    :supersedes={[ doc:policy=* doc:policy=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq('V-41', nodes[0].get('id'))
            self.eq('Rule 41', nodes[0].get('title'))
            self.eq('If you can AAAAAAAA...', nodes[0].get('text'))
            self.eq(1729209600000000, nodes[0].get('created'))
            self.eq(1729209600000000, nodes[0].get('updated'))
            self.eq(1099513724931, nodes[0].get('version'))

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('author'))

            self.len(2, nodes[0].get('supersedes'))
            self.len(1, nodes[0].get('contributors'))

            self.len(1, await core.nodes('doc:policy:id=V-41 :file -> file:bytes'))
            self.len(2, await core.nodes('doc:policy:id=V-41 :supersedes -> doc:policy'))
            self.len(1, await core.nodes('doc:policy:id=V-41 :author -> entity:contact +:name=visi'))
            self.len(1, await core.nodes('doc:policy:id=V-41 :contributors -> entity:contact +:name=shuka'))

            nodes = await core.nodes('''
                [ doc:standard=*
                    :id=V-99
                    :policy={ doc:policy:id=V-41 }
                ]
            ''')
            self.len(1, nodes)
            self.eq('V-99', nodes[0].get('id'))
            self.nn(nodes[0].get('policy'))
            self.len(1, await core.nodes('doc:standard -> doc:policy'))

            nodes = await core.nodes('''
                [ doc:requirement=*
                    :id=V-99
                    :priority=low
                    :optional=(false)
                    :desc="Some requirement text."
                    :standard={doc:standard}
                ]
            ''')
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Some requirement text.', nodes[0].get('desc'))
            self.eq(20, nodes[0].get('priority'))
            self.false(nodes[0].get('optional'))
            self.nn(nodes[0].get('standard'))
            self.len(1, await core.nodes('doc:requirement -> doc:standard'))

            nodes = await core.nodes('''
                [ doc:resume=*
                    :id=V-99
                    :contact={[ entity:contact=* :name=visi ]}
                    :desc="Thought leader seeks..."
                    :workhist={[ ps:workhist=* ]}
                    :education={[ ps:education=* ]}
                    :achievements={[ ps:achievement=* ]}
                ]
            ''')
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Thought leader seeks...', nodes[0].get('desc'))
            self.nn(nodes[0].get('contact'))
            self.len(1, nodes[0].get('workhist'))
            self.len(1, nodes[0].get('education'))
            self.len(1, nodes[0].get('achievements'))

            self.len(1, await core.nodes('doc:resume :contact -> entity:contact'))
            self.len(1, await core.nodes('doc:resume :workhist -> ps:workhist'))
            self.len(1, await core.nodes('doc:resume :education -> ps:education'))
            self.len(1, await core.nodes('doc:resume :achievements -> ps:achievement'))

            nodes = await core.nodes('''
            [ doc:contract=*
                :title="Fullbright Scholarship"
                :type=foo.bar
                :sponsor={[ ou:org=({"name": "vertex"}) ]}
                :currency=USD
                :award:price=20.00
                :budget:price=21.50
                :parties={[ entity:contact=* entity:contact=* ]}
                :document={[ file:bytes=* ]}
                :signed=202001
                :begins=202002
                :expires=202003
                :completed=202004
                :terminated=202005
                :requirements={
                    [( ou:goal=* :name="world peace" )]
                    [( ou:goal=* :name="whirled peas" )]
                }
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('sponsor'))
            self.eq('Fullbright Scholarship', nodes[0].get('title'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('20', nodes[0].get('award:price'))
            self.eq('21.5', nodes[0].get('budget:price'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq(1577836800000000, nodes[0].get('signed'))
            self.eq(1580515200000000, nodes[0].get('begins'))
            self.eq(1583020800000000, nodes[0].get('expires'))
            self.eq(1585699200000000, nodes[0].get('completed'))
            self.eq(1588291200000000, nodes[0].get('terminated'))
            self.len(2, nodes[0].get('parties'))
            self.len(2, nodes[0].get('requirements'))

            nodes = await core.nodes('doc:contract -> doc:contract:type:taxonomy')
            self.len(1, nodes)
            self.eq(1, nodes[0].get('depth'))
            self.eq('bar', nodes[0].get('base'))
            self.eq('foo.', nodes[0].get('parent'))

            nodes = await core.nodes('doc:contract:type:taxonomy')
            self.len(2, nodes)
            self.eq(0, nodes[0].get('depth'))
            self.eq('foo', nodes[0].get('base'))
            self.none(nodes[0].get('parent'))
