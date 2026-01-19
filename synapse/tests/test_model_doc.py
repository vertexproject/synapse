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
            self.eq('V-41', nodes[0].get('id'))
            self.eq('Rule 41', nodes[0].get('title'))
            self.eq('If you can AAAAAAAA...', nodes[0].get('body'))
            self.eq(1729209600000000, nodes[0].get('created'))
            self.eq(1729209600000000, nodes[0].get('updated'))
            self.eq('1.2.3', nodes[0].get('version'))

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

                    <(meets)+ {[ meta:technique=* ]}
                ]
            ''')
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Some requirement text.', nodes[0].get('desc'))
            self.eq(20, nodes[0].get('priority'))
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
            self.eq('V-99', nodes[0].get('id'))
            self.eq('Thought leader seeks...', nodes[0].get('desc'))
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
            self.eq('Fullbright Scholarship', nodes[0].get('title'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq(1577836800000000, nodes[0].get('signed'))
            self.eq(nodes[0].get('period'), (1580515200000000, 1583020800000000, 2505600000000))
            self.eq(1585699200000000, nodes[0].get('completed'))
            self.eq(1588291200000000, nodes[0].get('terminated'))
            self.len(2, nodes[0].get('parties'))

            self.len(1, await core.nodes('doc:contract :issuer -> ou:org'))
            self.len(2, await core.nodes('doc:contract :parties -> *'))
            self.len(2, await core.nodes('doc:contract :signers -> *'))

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

            nodes = await core.nodes('[ doc:report=* :topics=(foo, Bar) ]')
            self.len(1, nodes)
            self.eq(('bar', 'foo'), nodes[0].get('topics'))

            nodes = await core.nodes('''[
                doc:reference=*
                    :referrer={[ doc:report=* :title="an article about mars" ]}
                    :text="(Lee, 2020, para. 15)"
                    :doc={[ doc:report=* :title="nasa mars report" :author={[ ps:person=* :name="bruce lee" ]} ]}
                    :url=https://nasa.gov/2020-mars
                    +#test00
            ]''')
            self.len(1, nodes)
            self.eq('(Lee, 2020, para. 15)', nodes[0].get('text'))
            self.eq('https://nasa.gov/2020-mars', nodes[0].get('url'))
            self.len(1, await core.nodes('doc:reference#test00 :referrer -> doc:report'))
            self.len(1, await core.nodes('doc:reference#test00 :doc -> doc:report'))

            nodes = await core.nodes('''[
                doc:reference=*
                    :referrer={[ risk:vuln=* :cve=cve-2025-12345 ]}
                    :text="an exploit example"
                    :url=https://github.com/foo/bar/exploit.py
                    +#test01
            ]''')
            self.len(1, nodes)
            self.eq('an exploit example', nodes[0].get('text'))
            self.eq('https://github.com/foo/bar/exploit.py', nodes[0].get('url'))
            self.len(1, await core.nodes('doc:reference#test01 :referrer -> risk:vuln'))
