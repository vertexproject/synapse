import io
import json

import msgpack

import unittest.mock as mock

import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils
import synapse.tools.aha.list as s_a_list
import synapse.tools.aha.easycert as s_a_easycert


import synapse.tools.infra.gendc as s_t_gendc

basic_cells = {
    'version': '0.1.0',
    'aha': {
        'aha:network': 'mytest.loop.vertex.link',
    },
    'svcs': [
        {
            'name': 'axon',
            'docker': {
                'image': 'vertexproject/synapse-axon:v2.x.x'
            }
        },
        {
            'name': 'cortex',
            'docker': {
                'image': 'vertexproject/synapse-cortex:v2.x.x'
            },
            'cellconf': {
                'storm:log': True,
                'provenance:en': False,
                'axon': 'GENAHAURL_axon'
            }
        }
    ]
}

import synapse.common as s_common

class InfraGendcTest(s_t_utils.SynTest):

    async def test_basic_gen(self):
        with self.getTestDir() as dirn:
            yamlfp = s_common.genpath(dirn, 'input.yaml')
            s_common.yamlsave(basic_cells, yamlfp)
            outdir = s_common.genpath(dirn, 'output')
            argv = [yamlfp, outdir]
            ret = await s_t_gendc.main(argv=argv, outp=None)
            self.eq(0, ret)
