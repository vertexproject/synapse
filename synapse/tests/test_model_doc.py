import synapse.tests.utils as s_tests

class DocModelTest(s_tests.SynTest):

    async def test_model_doc(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ doc:policy=*
                    :id=V-41
                    :name="Rule 41"
                    :text="If you can AAAAAAAA..."
                    :file=*
                    :created=20241018
                    :updated=20241018
                    :author={[ ps:contact=* :name=visi ]}
                    :contributors={[ ps:contact=* :name=shuka ]}
                    :version=1.2.3
                    :supersedes={[ doc:policy=* doc:policy=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq('V-41', nodes[0].get('id'))
            self.eq('rule 41', nodes[0].get('name'))
            self.eq('If you can AAAAAAAA...', nodes[0].get('text'))
            self.eq(1729209600000, nodes[0].get('created'))
            self.eq(1729209600000, nodes[0].get('updated'))
            self.eq(1099513724931, nodes[0].get('version'))

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('author'))

            self.len(2, nodes[0].get('supersedes'))
            self.len(1, nodes[0].get('contributors'))

            self.len(1, await core.nodes('doc:policy:id=V-41 :file -> file:bytes'))
            self.len(2, await core.nodes('doc:policy:id=V-41 :supersedes -> doc:policy'))
            self.len(1, await core.nodes('doc:policy:id=V-41 :author -> ps:contact +:name=visi'))
            self.len(1, await core.nodes('doc:policy:id=V-41 :contributors -> ps:contact +:name=shuka'))

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
                    :summary="Some requirement text."
                    :standard={doc:standard}
                ]
            ''')
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Some requirement text.', nodes[0].get('summary'))
            self.eq(20, nodes[0].get('priority'))
            self.false(nodes[0].get('optional'))
            self.nn(nodes[0].get('standard'))
            self.len(1, await core.nodes('doc:requirement -> doc:standard'))

            nodes = await core.nodes('''
                [ doc:resume=*
                    :id=V-99
                    :contact={[ ps:contact=* :name=visi ]}
                    :summary="Thought leader seeks..."
                    :workhist={[ ps:workhist=* ]}
                    :education={[ ps:education=* ]}
                    :achievements={[ ps:achievement=* ]}
                ]
            ''')
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Thought leader seeks...', nodes[0].get('summary'))
            self.nn(nodes[0].get('contact'))
            self.len(1, nodes[0].get('workhist'))
            self.len(1, nodes[0].get('education'))
            self.len(1, nodes[0].get('achievements'))

            self.len(1, await core.nodes('doc:resume :contact -> ps:contact'))
            self.len(1, await core.nodes('doc:resume :workhist -> ps:workhist'))
            self.len(1, await core.nodes('doc:resume :education -> ps:education'))
            self.len(1, await core.nodes('doc:resume :achievements -> ps:achievement'))
