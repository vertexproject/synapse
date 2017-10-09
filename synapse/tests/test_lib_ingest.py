import io

from synapse.tests.common import *

import synapse.cortex as s_cortex
import synapse.lib.tufo as s_tufo
import synapse.lib.ingest as s_ingest

testxml = b'''<?xml version="1.0"?>
<data>

    <dnsa fqdn="foo.com" ipv4="1.2.3.4"/>
    <dnsa fqdn="bar.com" ipv4="5.6.7.8"/>

    <urls>
        <badurl>http://evil.com/</badurl>
        <badurl>http://badguy.com/</badurl>
    </urls>

</data>
'''
testlines = b'''
foo.com
bar.com
'''

class IngTest(SynTest):
    def test_ingest_iteriter(self):
        data = [['woot.com']]

        # test an iters directive within an iters directive for

        with self.getRamCore() as core:
            info = {'ingest': {
                'iters': [
                    ('*/*', {
                        'forms': [
                            ('inet:fqdn', {}),
                        ],
                    }),
                ],
            }}

            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))

    def test_ingest_basic(self):

        with self.getRamCore() as core:
            info = {
                'ingest': {
                    'iters': (
                        ('foo/*/fqdn', {
                            'forms': [
                                ('inet:fqdn', {
                                    'props': {
                                        'sfx': {'path': '../tld'},
                                    }
                                }),
                            ]
                        }),
                    ),
                },
            }

            data = {
                'foo': [
                    {'fqdn': 'com', 'tld': True},
                    {'fqdn': 'woot.com'},
                ],

                'bar': [
                    {'fqdn': 'vertex.link', 'tld': 0},
                ],

                'newp': [
                    {'fqdn': 'newp.com', 'tld': 0},
                ],

            }

            gest = s_ingest.Ingest(info)

            gest.ingest(core, data=data)

            self.eq(core.getTufoByProp('inet:fqdn', 'com')[1].get('inet:fqdn:sfx'), 1)
            self.eq(core.getTufoByProp('inet:fqdn', 'woot.com')[1].get('inet:fqdn:zone'), 1)

            self.none(core.getTufoByProp('inet:fqdn', 'newp.com'))

    def test_ingest_csv(self):

        with self.getRamCore() as core:
            with self.getTestDir() as path:
                csvp = os.path.join(path, 'woot.csv')

                with genfile(csvp) as fd:
                    fd.write(b'#THIS IS A COMMENT\n')
                    fd.write(b'foo.com,1.2.3.4\n')
                    fd.write(b'vertex.link,5.6.7.8\n')

                info = {
                    'sources': (
                        (csvp, {'open': {'format': 'csv', 'format:csv:comment': '#'}, 'ingest': {

                            'tags': ['hehe.haha'],

                            'forms': [
                                ('inet:fqdn', {'path': '0'}),
                                ('inet:ipv4', {'path': '1'}),
                            ]
                        }}),
                    )
                }

                gest = s_ingest.Ingest(info)

                gest.ingest(core)

            self.nn(core.getTufoByProp('inet:fqdn', 'foo.com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:ipv4', '1.2.3.4'))
            self.nn(core.getTufoByProp('inet:ipv4', '5.6.7.8'))

            self.len(2, core.eval('inet:ipv4*tag=hehe.haha'))
            self.len(2, core.eval('inet:fqdn*tag=hehe.haha'))

    def test_ingest_files(self):

        # s_encoding.encode('utf8,base64,-utf8','
        data = {'foo': ['dmlzaQ==']}

        info = {'ingest': {
            'iters': [["foo/*", {
                'tags': ['woo.woo'],
                'files': [{'mime': 'hehe/haha', 'decode': '+utf8,base64'}],
            }]]
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            tufo = core.getTufoByProp('file:bytes', '442f602ecf8230b2a59a44b4f845be27')

            self.true(s_tufo.tagged(tufo, 'woo.woo'))
            self.eq(tufo[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq(tufo[1].get('file:bytes:mime'), 'hehe/haha')

        # do it again with an outer iter and non-iter path
        data = {'foo': ['dmlzaQ==']}

        info = {'ingest': {
            'tags': ['woo.woo'],
            'iters': [
                ('foo/*', {
                    'files': [{'mime': 'hehe/haha', 'decode': '+utf8,base64'}],
                }),
            ]
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            tufo = core.getTufoByProp('file:bytes', '442f602ecf8230b2a59a44b4f845be27')

            self.eq(tufo[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq(tufo[1].get('file:bytes:mime'), 'hehe/haha')
            self.true(s_tufo.tagged(tufo, 'woo.woo'))

    def test_ingest_pivot(self):

        data = {'foo': ['dmlzaQ=='], 'bar': ['1b2e93225959e3722efed95e1731b764']}

        info = {'ingest': {
            'tags': ['woo.woo'],
            'iters': [

                ['foo/*', {
                    'files': [{'mime': 'hehe/haha', 'decode': '+utf8,base64'}],
                }],

                ['bar/*', {
                    'forms': [('hehe:haha', {'pivot': ('file:bytes:md5', 'file:bytes')})],
                }],

            ],
        }}

        with self.getRamCore() as core:
            core.addTufoForm('hehe:haha', ptype='file:bytes')

            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('hehe:haha', '442f602ecf8230b2a59a44b4f845be27'))

    def test_ingest_template(self):

        data = {'foo': [('1.2.3.4', 'vertex.link')]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [
                        ['ipv4', {'path': '0'}],
                        ['fqdn', {'path': '1'}]
                    ],
                    'forms': [('inet:dns:a', {'template': '{{fqdn}}/{{ipv4}}'})]
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:dns:a', 'vertex.link/1.2.3.4'))

    def test_ingest_json(self):
        testjson = b'''{
            "fqdn": "spooky.com",
            "ipv4": "192.168.1.1",
            "aliases": ["foo", "bar", "baz"]
        }'''
        with self.getRamCore() as core:
            with self.getTestDir() as path:
                xpth = os.path.join(path, 'woot.json')

                with genfile(xpth) as fd:
                    fd.write(testjson)

                info = {
                    'sources': [(xpth,
                                 {'open': {'format': 'json'},
                                  'ingest': {
                                      'tags': ['luljson'],
                                      'iters': [
                                          ['fqdn', {
                                              'forms': [('inet:fqdn', {})]
                                          }],
                                          ['ipv4', {
                                              'forms': [('inet:ipv4', {})]
                                          }],
                                          ['aliases/*', {
                                              'forms': [('strform', {})]
                                          }]
                                      ]}})]}
                gest = s_ingest.Ingest(info)
                gest.ingest(core)

                self.nn(core.getTufoByProp('inet:fqdn', 'spooky.com'))
                self.nn(core.getTufoByProp('inet:ipv4', '192.168.1.1'))
                self.nn(core.getTufoByProp('strform', 'foo'))
                self.nn(core.getTufoByProp('strform', 'bar'))
                self.nn(core.getTufoByProp('strform', 'baz'))

    def test_ingest_jsonl(self):
        testjsonl = b'''{"fqdn": "spooky.com", "ipv4": "192.168.1.1"}
{"fqdn":"spookier.com", "ipv4":"192.168.1.2"}'''

        with self.getRamCore() as core:
            with self.getTestDir() as path:
                xpth = os.path.join(path, 'woot.jsonl')

                with genfile(xpth) as fd:
                    fd.write(testjsonl)

                info = {
                    'sources': [(xpth,
                                 {'open': {'format': 'jsonl'},
                                  'ingest': {
                                      'tags': ['leljsonl'],
                                      'iters': [
                                          ['fqdn', {
                                              'forms': [('inet:fqdn', {})]
                                          }],
                                          ['ipv4', {
                                              'forms': [('inet:ipv4', {})]
                                          }]
                                      ]}})]}
                gest = s_ingest.Ingest(info)
                gest.ingest(core)

                self.nn(core.getTufoByProp('inet:fqdn', 'spooky.com'))
                self.nn(core.getTufoByProp('inet:ipv4', '192.168.1.1'))
                self.nn(core.getTufoByProp('inet:fqdn', 'spookier.com'))
                self.nn(core.getTufoByProp('inet:ipv4', '192.168.1.2'))

    def test_ingest_xml(self):
        with self.getRamCore() as core:
            with self.getTestDir() as path:
                xpth = os.path.join(path, 'woot.xml')

                with genfile(xpth) as fd:
                    fd.write(testxml)

                info = {

                    'sources': [

                        (xpth, {

                            'open': {'format': 'xml'},

                            'ingest': {

                                'tags': ['lolxml'],

                                'iters': [

                                    ['data/dnsa', {
                                        # explicitly opt fqdn into the optional attrib syntax
                                        'vars': [
                                            ['fqdn', {'path': '$fqdn'}],
                                            ['ipv4', {'path': 'ipv4'}],
                                        ],
                                        'forms': [
                                            ('inet:dns:a', {'template': '{{fqdn}}/{{ipv4}}'}),
                                        ]
                                    }],

                                    ['data/urls/*', {
                                        'forms': [
                                            ('inet:url', {}),
                                        ],
                                    }],

                                ]
                            }
                        })
                    ]
                }

                gest = s_ingest.Ingest(info)

                gest.ingest(core)

                self.nn(core.getTufoByProp('inet:dns:a', 'foo.com/1.2.3.4'))
                self.nn(core.getTufoByProp('inet:dns:a', 'bar.com/5.6.7.8'))
                self.nn(core.getTufoByProp('inet:url', 'http://evil.com/'))
                self.nn(core.getTufoByProp('inet:url', 'http://badguy.com/'))

                self.len(2, core.eval('inet:dns:a*tag=lolxml'))
                self.len(2, core.eval('inet:url*tag=lolxml'))

    def test_ingest_xml_search(self):

        with self.getRamCore() as core:
            with self.getTestDir() as path:
                xpth = os.path.join(path, 'woot.xml')

                with genfile(xpth) as fd:
                    fd.write(testxml)

                info = {

                    'sources': [

                        (xpth, {

                            'open': {'format': 'xml'},

                            'ingest': {

                                'iters': [

                                    ['~badurl', {'forms': [('inet:url', {}), ], }],

                                ]
                            }
                        })
                    ]
                }

                gest = s_ingest.Ingest(info)

                gest.ingest(core)

                self.nn(core.getTufoByProp('inet:url', 'http://evil.com/'))
                self.nn(core.getTufoByProp('inet:url', 'http://badguy.com/'))

    def test_ingest_taginfo(self):

        with self.getRamCore() as core:
            info = {
                'ingest': {
                    'iters': [
                        ('foo/*', {
                            'vars': [
                                ['baz', {'path': '1'}]
                            ],
                            'tags': [{'template': 'foo.bar.{{baz}}'}],
                            'forms': [('inet:fqdn', {'path': '0'})]
                        }),
                    ]
                }
            }

            data = {'foo': [('vertex.link', 'LULZ')]}

            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.len(1, core.eval('inet:fqdn*tag="foo.bar.lulz"'))

    def test_ingest_cast(self):

        with self.getRamCore() as core:
            info = {
                'ingest': {
                    'iters': [
                        ('foo/*', {
                            'forms': [('strform', {'path': '1', 'cast': 'str:lwr'})]
                        }),
                    ]
                }
            }

            data = {'foo': [('vertex.link', 'LULZ')]}

            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('strform', 'lulz'))

    def test_ingest_lines(self):
        with self.getRamCore() as core:
            with self.getTestDir() as path:
                path = os.path.join(path, 'woot.txt')

                with genfile(path) as fd:
                    fd.write(testlines)

                info = {
                    'sources': [
                        (path, {
                            'open': {'format': 'lines'},
                            'ingest': {
                                'forms': [['inet:fqdn', {}]]
                            }
                        })
                    ]
                }

                gest = s_ingest.Ingest(info)

                gest.ingest(core)

                self.nn(core.getTufoByProp('inet:fqdn', 'foo.com'))
                self.nn(core.getTufoByProp('inet:fqdn', 'bar.com'))

    def test_ingest_condform(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'hehe': 3}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['hehe', {'path': 'hehe'}]],
                    'forms': [('inet:fqdn', {'path': 'fqdn', 'cond': 'hehe != 3'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.none(core.getTufoByProp('inet:fqdn', 'vertex.link'))

            data['foo'][0]['hehe'] = 9

            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_ingest_condform_with_missing_var(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'hehe': 3}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['hehe', {'path': 'heho'}]],
                    'forms': [('inet:fqdn', {'path': 'fqdn', 'cond': 'hehe != 3'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.none(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_ingest_condtag(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'hehe': 3}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['hehe', {'path': 'hehe'}]],
                    'tags': [{'value': 'hehe.haha', 'cond': 'hehe != 3'}],
                    'forms': [('inet:fqdn', {'path': 'fqdn'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.false(s_tufo.tagged(node, 'hehe.haha'))

            data['foo'][0]['hehe'] = 9

            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'hehe.haha'))

    def test_ingest_varprop(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'hehe': 3}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['zoom', {'path': 'fqdn'}]],
                    'forms': [('inet:fqdn', {'var': 'zoom'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_ingest_tagiter(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'haha': ['foo', 'bar']}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['zoom', {'path': 'fqdn'}]],
                    'tags': [
                        {'iter': 'haha/*',
                         'vars': [['zoomtag', {}]],
                         'template': 'zoom.{{zoomtag}}'}
                    ],
                    'forms': [('inet:fqdn', {'path': 'fqdn'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'zoom.foo'))
            self.true(s_tufo.tagged(node, 'zoom.bar'))

    def test_ingest_tag_template_whif(self):

        data = {'foo': [{'fqdn': 'vertex.link', 'haha': ['barbar', 'foofoo']}]}

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['zoom', {'path': 'fqdn'}]],
                    'tags': [
                        {'iter': 'haha/*',
                         'vars': [
                             ['tag', {'regex': '^foo'}],
                         ],
                         'template': 'zoom.{{tag}}'}
                    ],
                    'forms': [('inet:fqdn', {'path': 'fqdn'})],
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'zoom.foofoo'))
            self.false(s_tufo.tagged(node, 'zoom.barbar'))

    def test_ingest_addFormat(self):

        def _fmt_woot_old(fd, info):
            yield 'old.bad'

        def _fmt_woot(fd, info):
            yield 'woot'

        opts = {'mode': 'r', 'encoding': 'utf8'}

        s_ingest.addFormat('woot', _fmt_woot_old, opts)
        self.nn(s_ingest.fmtyielders.get('woot'))
        s_ingest.addFormat('woot', _fmt_woot, opts)  # last write wins

        with self.getRamCore() as core:
            with self.getTestDir() as path:
                wootpath = os.path.join(path, 'woot.woot')
                with genfile(wootpath) as fd:
                    fd.write(b'this is irrelevant, we always yield woot :-)')

                info = {
                    'sources': (
                        (wootpath, {'open': {'format': 'woot'}, 'ingest': {
                            'tags': ['hehe.haha'],
                            'forms': [
                                ('inet:fqdn', {}),
                            ]
                        }}),
                    )
                }

                gest = s_ingest.Ingest(info)
                gest.ingest(core)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot'))

    def test_ingest_embed_nodes(self):

        with self.getRamCore() as core:
            info = {
                "embed": [
                    {
                        "nodes": [

                            ["inet:fqdn", [
                                "woot.com",
                                "vertex.link"
                            ]],

                            ["inet:ipv4", [
                                "1.2.3.4",
                                0x05060708,
                            ]],
                        ]
                    }
                ]
            }

            gest = s_ingest.Ingest(info)
            gest.ingest(core)

            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            self.nn(core.getTufoByProp('inet:ipv4', 0x05060708))
            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_ingest_embed_tags(self):

        with self.getRamCore() as core:
            info = {
                "embed": [
                    {
                        "tags": [
                            "hehe.haha.hoho"
                        ],

                        "nodes": [

                            ["inet:fqdn", [
                                "rofl.com",
                                "laughitup.edu"
                            ]],

                            ["inet:email", [
                                "pennywise@weallfloat.com"
                            ]]
                        ]
                    }
                ]
            }

            gest = s_ingest.Ingest(info)
            gest.ingest(core)

            self.nn(core.getTufoByProp('inet:fqdn', 'rofl.com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'laughitup.edu'))
            self.nn(core.getTufoByProp('inet:email', 'pennywise@weallfloat.com'))

            self.len(2, core.eval('inet:fqdn*tag=hehe.haha.hoho'))
            self.len(1, core.eval('inet:email*tag=hehe.haha.hoho'))

    def test_ingest_embed_props(self):
        with self.getRamCore() as core:
            info = {
                "embed": [
                    {
                        "props": {"sfx": 1},
                        "nodes": [
                            ["inet:fqdn", [
                                "com",
                                "net",
                                "org"
                            ]],
                        ],
                    }
                ]
            }

            gest = s_ingest.Ingest(info)
            gest.ingest(core)

            self.nn(core.getTufoByProp('inet:fqdn', 'com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'net'))
            self.nn(core.getTufoByProp('inet:fqdn', 'org'))

            self.len(3, core.eval('inet:fqdn:sfx=1'))

    def test_ingest_embed_pernode_tagsprops(self):
        with self.getRamCore() as core:
            info = {
                "embed": [
                    {
                        "nodes": [

                            ["inet:fqdn", [
                                ["link", {"props": {"tld": 1}}],
                            ]],

                            ["inet:web:acct", [
                                ["rootkit.com/metr0", {"props": {"email": "metr0@kenshoto.com"}}],
                                ["twitter.com/invisig0th", {"props": {"email": "visi@vertex.link"}}]
                            ]],

                            ["inet:email", [
                                ["visi@vertex.link", {"tags": ["foo.bar", "baz.faz"]}]
                            ]]
                        ]
                    }
                ]
            }

            gest = s_ingest.Ingest(info)
            gest.ingest(core)

            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/metr0'))
            self.nn(core.getTufoByProp('inet:web:acct', 'twitter.com/invisig0th'))

            self.len(1, core.eval('inet:web:acct:email="visi@vertex.link"'))
            self.len(1, core.eval('inet:web:acct:email="metr0@kenshoto.com"'))

            node = core.eval('inet:email*tag=foo.bar')[0]
            self.eq(node[1].get('inet:email'), 'visi@vertex.link')

    def test_ingest_iter_object(self):
        data = {
            'foo': {
                'boosh': {
                    'fqdn': 'vertex.link'
                },
                'woot': {
                    'fqdn': 'foo.bario'
                }
            }
        }
        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [
                        ['bar', {'path': '0'}],
                        ['fqdn', {'path': '1/fqdn'}]
                    ],
                    'forms': [('inet:fqdn', {'template': '{{bar}}.{{fqdn}}'})]
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'boosh.vertex.link')
            self.nn(node)

            node = core.getTufoByProp('inet:fqdn', 'woot.foo.bario')
            self.nn(node)

    def test_ingest_iter_objectish_array(self):
        data = {
            'foo': [
                {0: 'boosh',
                  1: {
                    'fqdn': 'vertex.link'
                  },
                },
                {0: 'woot',
                  1: {
                    'fqdn': 'foo.bario'
                  }
                }
            ]
        }
        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [
                        ['bar', {'path': '0'}],
                        ['fqdn', {'path': '1/fqdn'}]
                    ],
                    'forms': [('inet:fqdn', {'template': '{{bar}}.{{fqdn}}'})]
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            node = core.getTufoByProp('inet:fqdn', 'boosh.vertex.link')
            self.nn(node)

            node = core.getTufoByProp('inet:fqdn', 'woot.foo.bario')
            self.nn(node)

    def test_ingest_savevar(self):
        data = {'foo': [{'md5': '9e107d9d372bb6826bd81d3542a419d6',
                         'sha1': '2fd4e1c67a2d28fced849ee1bb76e7391b93eb12',
                         'sha256': 'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592',
                         'signame': 'Meme32.LazyDog',
                         'vendor': 'memeSec'},
                        {'md5': 'e4d909c290d0fb1ca068ffaddf22cbd0',
                         'sha1': '408d94384216f890ff7a0c3528e8bed1e0b01621',
                         'sha256': 'ef537f25c895bfa782526529a9b63d97aa631564d5d789c2b765448c8635fb6c',
                         'signame': 'Meme32.LazyDog.Puntuation',
                         'vendor': 'memeSec'}
                        ]
                }

        info = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [
                        ['md5', {'path': 'md5'}],
                        ['sha1', {'path': 'sha1'}],
                        ['sha256', {'path': 'sha256'}],
                        ['sig_name', {'path': 'signame'}],
                        ['vendor', {'path': 'vendor'}]
                    ],
                    'forms': [
                        ['file:bytes:sha256',
                         {'props': {'md5': {'var': 'md5'}, 'sha1': {'var': 'sha1'}, 'sha256': {'var': 'sha256'}},
                          'var': 'sha256',
                          'savevar': 'file_guid'}],
                        ['it:av:filehit', {'template': '{{file_guid}}/{{vendor}}/{{sig_name}}'}]
                    ]
                }],
            ],
        }}

        with self.getRamCore() as core:
            gest = s_ingest.Ingest(info)
            gest.ingest(core, data=data)

            self.nn(core.getTufoByProp('file:bytes:sha256',
                                       'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592'))
            self.nn(core.getTufoByProp('it:av:filehit:sig', 'memesec/meme32.lazydog'))
            self.nn(core.getTufoByProp('it:av:sig:sig', 'meme32.lazydog'))
            self.nn(core.getTufoByProp('file:bytes:sha256',
                                       'ef537f25c895bfa782526529a9b63d97aa631564d5d789c2b765448c8635fb6c'))
            self.nn(core.getTufoByProp('it:av:filehit:sig', 'memesec/meme32.lazydog.puntuation'))
            self.nn(core.getTufoByProp('it:av:sig:sig', 'meme32.lazydog.puntuation'))
            self.len(2, core.getTufosByProp('it:av:sig:org', 'memesec'))

    def test_ingest_cortex_registration(self):

        data1 = {'foo': [{'fqdn': 'vertex.link', 'haha': ['barbar', 'foofoo']}]}
        data2 = {'foo': [{'fqdn': 'weallfloat.com', 'haha': ['fooboat', 'sewer']}]}
        data3 = {'foo': [{'fqdn': 'woot.com', 'haha': ['fooboat', 'sewer']}]}

        ingest_def = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['zoom', {'path': 'fqdn'}]],
                    'tags': [
                        {'iter': 'haha/*',
                         'vars': [
                             ['tag', {'regex': '^foo'}],
                         ],
                         'template': 'zoom.{{tag}}'}
                    ],
                    'forms': [('inet:fqdn', {'path': 'fqdn'})],
                }],
            ],
        }}

        ingest_def2 = {'ingest': {
            'iters': [
                ["foo/*", {
                    'vars': [['zoom', {'path': 'fqdn'}]],
                    'forms': [('inet:fqdn', {'path': 'fqdn'})],
                }],
            ],
        }}

        gest = s_ingest.Ingest(ingest_def)
        gest2 = s_ingest.Ingest(ingest_def2)

        with self.getRamCore() as core:
            ret1 = s_ingest.register_ingest(core=core, gest=gest, evtname='ingest:test')
            ret2 = s_ingest.register_ingest(core=core, gest=gest2, evtname='ingest:test2', ret_func=True)
            self.none(ret1)
            self.true(callable(ret2))

            # Dump data into the core an event at a time.
            core.fire('ingest:test', data=data1)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(isinstance(node, tuple))
            self.true(s_tufo.tagged(node, 'zoom.foofoo'))
            self.false(s_tufo.tagged(node, 'zoom.barbar'))

            core.fire('ingest:test', data=data2)
            node = core.getTufoByProp('inet:fqdn', 'weallfloat.com')
            self.true(isinstance(node, tuple))
            self.true(s_tufo.tagged(node, 'zoom.fooboat'))
            self.false(s_tufo.tagged(node, 'zoom.sewer'))

            # Try another ingest attached to the core.  This won't have any tags applied.
            core.fire('ingest:test2', data=data3)
            node = core.getTufoByProp('inet:fqdn', 'woot.com')
            self.true(isinstance(node, tuple))
            self.false(s_tufo.tagged(node, 'zoom.fooboat'))
            self.false(s_tufo.tagged(node, 'zoom.sewer'))

    def test_ingest_basic_bufio(self):

        with self.getRamCore() as core:
            info = {
                'ingest': {
                    'iters': (
                        ('foo/*/fqdn', {
                            'forms': [
                                ('inet:fqdn', {
                                    'props': {
                                        'sfx': {'path': '../tld'},
                                    }
                                }),
                            ]
                        }),
                    ),
                },
                'open': {
                    'format': 'json'
                }
            }

            data = {
                'foo': [
                    {'fqdn': 'com', 'tld': True},
                    {'fqdn': 'woot.com'},
                ],

                'bar': [
                    {'fqdn': 'vertex.link', 'tld': 0},
                ],

                'newp': [
                    {'fqdn': 'newp.com', 'tld': 0},
                ],

            }

            buf = io.BytesIO(json.dumps(data).encode())

            ingdata = s_ingest.iterdata(fd=buf, **info.get('open'))

            gest = s_ingest.Ingest(info)

            for _data in ingdata:
                gest.ingest(core, data=_data)

            self.eq(core.getTufoByProp('inet:fqdn', 'com')[1].get('inet:fqdn:sfx'), 1)
            self.eq(core.getTufoByProp('inet:fqdn', 'woot.com')[1].get('inet:fqdn:zone'), 1)

            self.none(core.getTufoByProp('inet:fqdn', 'newp.com'))

    def test_ingest_iterdata(self):
        data = {
            'foo': [
                {'fqdn': 'com', 'tld': True},
                {'fqdn': 'woot.com'},
            ],

            'bar': [
                {'fqdn': 'vertex.link', 'tld': 0},
            ],

            'newp': [
                {'fqdn': 'newp.com', 'tld': 0},
            ],

        }

        buf = io.BytesIO(json.dumps(data).encode())

        ingdata = s_ingest.iterdata(fd=buf, **{'format': 'json'})

        for _data in ingdata:
            self.nn(_data)
        self.true(buf.closed)

        buf2 = io.BytesIO(json.dumps(data).encode())

        # Leave the file descriptor open.
        ingdata = s_ingest.iterdata(buf2,
                                    close_fd=False,
                                    **{'format': 'json'})

        for _data in ingdata:
            self.nn(_data)
        self.false(buf2.closed)
        buf2.close()

    def test_ingest_xref(self):
        data = {
            "fhash": "e844031e309ce19520f563c38239190f59e7e1a67d4302eaea563c3ad36a8d81",
            "ip": "8.8.8.8"
        }

        ingdef = {
            'ingest': {
                'vars': [
                    [
                        "fhash",
                        {
                            "path": "fhash"
                        }
                    ],
                    [
                        "ip",
                        {
                            "path": "ip"
                        }
                    ]
                ],
                'forms': [
                    [
                        "file:bytes:sha256",
                        {
                            "var": "fhash",
                            "savevar": "file_guid"
                        }
                    ],
                    [
                        "inet:ipv4",
                        {
                            "var": "ip",
                            "savevar": "ip_guid"
                        }
                    ],
                    [
                        "file:txtref",
                        {
                            "template": "({{file_guid}},inet:ipv4={{ip_guid}})"
                        }
                    ]
                ]
            }
        }

        with self.getRamCore() as core:
            ingest = s_ingest.Ingest(info=ingdef)
            ingest.ingest(core=core, data=data)

            nodes1 = core.eval('file:bytes')
            self.len(1, nodes1)
            nodes2 = core.eval('inet:ipv4')
            self.len(1, nodes2)
            nodes3 = core.eval('file:txtref')
            self.len(1, nodes3)
            xrefnode = nodes3[0]
            self.eq(xrefnode[1].get('file:txtref:file'), nodes1[0][1].get('file:bytes'))
            self.eq(xrefnode[1].get('file:txtref:xref'), 'inet:ipv4=8.8.8.8')
            self.eq(xrefnode[1].get('file:txtref:xref:prop'), 'inet:ipv4')
            self.eq(xrefnode[1].get('file:txtref:xref:intval'), nodes2[0][1].get('inet:ipv4'))

    def test_ingest_reqprops(self):

        tick = now()

        ingdef = {
            "ingest": {
                "forms": [
                    [
                        "inet:dns:look",
                        {
                            "props": {
                                "time": {
                                    "var": "time"
                                },
                                "a": {
                                    "template": "{{fqdn}}/{{ipv4}}"
                                }
                            },
                            "value": "*"
                        }
                    ]
                ],
                "vars": [
                    [
                        "time",
                        {
                            "path": "time"
                        }
                    ],
                    [
                        "fqdn",
                        {
                            "path": "fqdn"
                        }
                    ],
                    [
                        "ipv4",
                        {
                            "path": "ipv4"
                        }
                    ]
                ]
            }
        }

        data = {"time": tick, "ipv4": "1.2.3.4", "fqdn": "vertex.link"}

        with self.getRamCore() as core:
            ingest = s_ingest.Ingest(info=ingdef)
            ingest.ingest(core=core, data=data)

            nodes = core.eval('inet:dns:look')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node[1].get('inet:dns:look:time'), tick)
            self.eq(node[1].get('inet:dns:look:a'), 'vertex.link/1.2.3.4')
