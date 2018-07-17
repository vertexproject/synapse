import unittest.mock as mock

import synapse.common as s_common

import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest

import synapse.tools.ingest as s_t_ingest

import synapse.tests.common as s_test

class IngTest(s_test.SynTest):

    def getGestDef(self, guid, seen):
        gestdef = {
            'comment': 'ingest_test',
            'source': guid,
            'seen': '20180102',
            'forms': {
                'teststr': [
                    '1234',
                    'duck',
                    'knight',
                ],
                'testint': [
                    '1234'
                ],
                'pivcomp': [
                    ('hehe', 'haha')
                ]
            },
            'tags': {
                'test.foo': (None, None),
                'test.baz': ('2014', '2015'),
                'test.woah': (seen - 1, seen + 1),
            },
            'nodes': [
                [
                    ['teststr',
                     'ohmy'
                    ],
                    {
                        'props': {
                            'bar': ('testint', 137),
                            'tick': '2001',
                        },
                        'tags': {
                            'beep.beep': (None, None),
                            'beep.boop': (10, 20),
                        }
                    }
                ],
                [
                    [
                        'testint',
                        '8675309'
                    ],
                    {
                        'tags': {
                            'beep.morp': (None, None)
                        }
                    }
                ]
            ],
            'edges': [
                [
                    [
                        'teststr',
                        '1234'
                    ],
                    'refs',
                    [
                        [
                            'testint',
                            1234
                        ]
                    ]
                ]
            ],
            'time:edges': [
                [
                    [
                        'teststr',
                        '1234'
                    ],
                    'wentto',
                    [
                        [
                            [
                            'testint',
                            8675309
                            ],
                            '20170102'
                        ]
                    ]
                ]
            ]
        }
        return gestdef

    def test_ingest_remote(self):
        guid = s_common.guid()
        seen = s_common.now()
        gestdef = self.getGestDef(guid, seen)

        gest = s_ingest.Ingest(gestdef)

        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            with dmon._getTestProxy('core', **pconf) as core:

                # Setup user permissions
                core.addAuthRole('creator')
                core.addAuthRule('creator', (True, ('node:add',)))
                core.addAuthRule('creator', (True, ('prop:set',)))
                core.addAuthRule('creator', (True, ('tag:add',)))
                core.addUserRole('root', 'creator')

                # use the gestdef to make nodes in the core
                nodes = gest.ingest(core)
                from pprint import pprint
                for node in nodes:
                    pprint(node, width=120)
                    self.nn(node)

                # Nodes are made from the forms directive
                q = 'teststr=1234 teststr=duck teststr=knight'
                self.len(3, core.eval(q))
                q = 'testint=1234'
                self.len(1, core.eval(q))
                q = 'pivcomp=(hehe,haha)'
                self.len(1, core.eval(q))

                # packed nodes are made from the nodes directive
                nodes = list(core.eval('teststr=ohmy'))
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node[1]['props'].get('bar'), ('testint', 137))
                self.eq(node[1]['props'].get('tick'), 978307200000)
                self.isin('beep.beep', node[1]['tags'])
                self.isin('beep.boop', node[1]['tags'])
                self.isin('test.foo', node[1]['tags'])

                nodes = list(core.eval('testint=8675309'))
                self.len(1, nodes)
                node = nodes[0]
                self.isin('beep.morp', node[1]['tags'])
                self.isin('test.foo', node[1]['tags'])

                # Sources are made, as are seen nodes.
                q = f'source={guid} -> seen:source'
                nodes = list(core.eval(q))
                self.len(9, nodes)
                for node in nodes:
                    self.isin('.seen', node[1].get('props', {}))

                # Included tags are made
                self.len(9, core.eval(f'#test'))

                # As are tag times
                nodes = list(core.eval('#test.baz'))
                self.eq(nodes[0][1].get('tags', {}).get('test.baz', ()),
                        (1388534400000, 1420070400000))

                # Edges are made
                self.len(1, core.eval('refs'))
                self.len(1, core.eval('wentto'))

    def test_tool_local(self):
        with self.getTestDir() as dirn:
            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getGestDef(guid, seen)
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--test', '--verbose', '--debug',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            cmdg = s_test.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                self.eq(s_t_ingest.main(argv, outp=outp), 0)
            self.true(outp.expect('Made 19 nodes', throw=False))
            self.true(outp.expect('teststr = haha', throw=False))
            self.true(outp.expect('pivtarg = hehe', throw=False))

    def test_tool_local_fail(self):
        with self.getTestDir() as dirn:
            gestdef = {'forms': {'teststr': ['yes', ],
                                 'newp': ['haha', ],
                                 }
                       }
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--test', '--verbose',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            print(outp)
            self.eq(s_t_ingest.main(argv, outp=outp), 1)
            self.true(outp.expect('Error encountered during data loading.', throw=False))

    def test_tool_remote(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            with dmon._getTestProxy('core', **pconf) as core:
                # Setup user permissions
                core.addAuthRole('creator')
                core.addAuthRule('creator', (True, ('node:add',)))
                core.addAuthRule('creator', (True, ('prop:set',)))
                core.addAuthRule('creator', (True, ('tag:add',)))
                core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getGestDef(guid, seen)
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--cortex', curl,
                    '--verbose',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            self.eq(s_t_ingest.main(argv, outp=outp), 0)
            self.true(outp.expect('Made 19 nodes', throw=False))
