import synapse.tests.utils as s_tests

class DocModelTest(s_tests.SynTest):

    async def test_model_doc(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ doc:policy=*
                    :id=V-41
                    :title="Rule 41"
                    :body="If you can AAAAAAAA..."
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
            self.propeq(nodes[0], 'id', 'V-41')
            self.propeq(nodes[0], 'title', 'Rule 41')
            self.propeq(nodes[0], 'body', 'If you can AAAAAAAA...')
            self.propeq(nodes[0], 'created', 1729209600000000)
            self.propeq(nodes[0], 'updated', 1729209600000000)
            self.propeq(nodes[0], 'version', '1.2.3')

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
            self.propeq(nodes[0], 'id', 'V-99')
            self.nn(nodes[0].get('policy'))
            self.len(1, await core.nodes('doc:standard -> doc:policy'))

            nodes = await core.nodes('''
                [ doc:requirement=*
                    :id=V-99
                    :priority=low
                    :optional=(false)
                    :desc="Some requirement text."
                    :standard={doc:standard}

                    <(meets)+ {[ meta:technique=* ]}
                ]
            ''')
            self.propeq(nodes[0], 'id', 'V-99')
            self.propeq(nodes[0], 'desc', 'Some requirement text.')
            self.propeq(nodes[0], 'priority', 20)
            self.false(nodes[0].get('optional'))
            self.nn(nodes[0].get('standard'))
            self.len(1, await core.nodes('doc:requirement <(meets)- meta:technique'))
            self.len(1, await core.nodes('doc:requirement -> doc:standard'))

            nodes = await core.nodes('''
                [ doc:resume=*
                    :id=V-99
                    :contact={[ entity:contact=* :name=visi ]}
                    :desc="Thought leader seeks..."
                    :skills={[ ps:skill=* ]}
                    :workhist={[ ps:workhist=* ]}
                    :education={[ ps:education=* ]}
                    :achievements={[ ps:achievement=* ]}
                ]
            ''')
            self.propeq(nodes[0], 'id', 'V-99')
            self.propeq(nodes[0], 'desc', 'Thought leader seeks...')
            self.nn(nodes[0].get('contact'))
            self.len(1, nodes[0].get('skills'))
            self.len(1, nodes[0].get('workhist'))
            self.len(1, nodes[0].get('education'))
            self.len(1, nodes[0].get('achievements'))

            self.len(1, await core.nodes('doc:resume :skills -> ps:skill'))
            self.len(1, await core.nodes('doc:resume :contact -> entity:contact'))
            self.len(1, await core.nodes('doc:resume :workhist -> ps:workhist'))
            self.len(1, await core.nodes('doc:resume :education -> ps:education'))
            self.len(1, await core.nodes('doc:resume :achievements -> ps:achievement'))

            nodes = await core.nodes('''
            [ doc:contract=*
                :title="Fullbright Scholarship"
                :type=foo.bar
                :issuer={[ ou:org=({"name": "vertex"}) ]}
                :parties={[ entity:contact=* entity:contact=* ]}
                :signers={[ entity:contact=* entity:contact=* ]}
                :file={[ file:bytes=* ]}
                :signed=202001
                :period=(202002, 202003)
                :completed=202004
                :terminated=202005
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'title', 'Fullbright Scholarship')
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'signed', 1577836800000000)
            self.propeq(nodes[0], 'period', (1580515200000000, 1583020800000000, 2505600000000))
            self.propeq(nodes[0], 'completed', 1585699200000000)
            self.propeq(nodes[0], 'terminated', 1588291200000000)
            self.len(2, nodes[0].get('parties'))

            self.len(1, await core.nodes('doc:contract :issuer -> ou:org'))
            self.len(2, await core.nodes('doc:contract :parties -> *'))
            self.len(2, await core.nodes('doc:contract :signers -> *'))

            nodes = await core.nodes('doc:contract -> doc:contract:type:taxonomy')
            self.len(1, nodes)
            self.propeq(nodes[0], 'depth', 1)
            self.propeq(nodes[0], 'base', 'bar')
            self.propeq(nodes[0], 'parent', 'foo.')

            nodes = await core.nodes('doc:contract:type:taxonomy')
            self.len(2, nodes)
            self.propeq(nodes[0], 'depth', 0)
            self.propeq(nodes[0], 'base', 'foo')
            self.none(nodes[0].get('parent'))

            nodes = await core.nodes('[ doc:report=* :topics=(foo, Bar) ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'topics', ('bar', 'foo'))

            nodes = await core.nodes('''[
                doc:reference=*
                    :source={[ doc:report=* :title="an article about mars" ]}
                    :text="(Lee, 2020, para. 15)"
                    :doc={[ doc:report=* :title="nasa mars report" :author={[ ps:person=* :name="bruce lee" ]} ]}
                    :doc:url=https://nasa.gov/2020-mars
                    +#test00
            ]''')
            self.len(1, nodes)
            self.eq('(Lee, 2020, para. 15)', nodes[0].get('text'))
            self.propeq(nodes[0], 'doc:url', 'https://nasa.gov/2020-mars')
            self.len(1, await core.nodes('doc:reference#test00 :source -> doc:report'))
            self.len(1, await core.nodes('doc:reference#test00 :doc -> doc:report'))

            nodes = await core.nodes('''[
                doc:reference=*
                    :source={[ risk:vuln=* :cve=cve-2025-12345 ]}
                    :text="an exploit example"
                    :doc:url=https://github.com/foo/bar/exploit.py
                    +#test01
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'text', 'an exploit example')
            self.propeq(nodes[0], 'doc:url', 'https://github.com/foo/bar/exploit.py')
            self.len(1, await core.nodes('doc:reference#test01 :source -> risk:vuln'))
