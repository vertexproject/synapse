import os
import json

import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.jupyter as s_jupyter
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormsvc as s_stormsvc

import synapse.tests.utils as s_t_utils

class TstsvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = 'testsvc'
    _storm_svc_pkgs = (
        {
            'name': 'testsvc',
            'version': (0, 0, 1),
            'synapse_version': '>=2.8.0,<3.0.0',
            'commands': (
                {
                    'name': 'testsvc.magic',
                    'storm': '[inet:ipv4=0]',
                },
            )
        },
    )

    async def testmeth(self):
        return 'shazam'

class Tstsvc(s_cell.Cell):
    cellapi = TstsvcApi

class JupyterTest(s_t_utils.SynTest):
    testmods = ['synapse.tests.utils.TestModule']

    async def test_tempcoreprox(self):
        prox = await s_jupyter.getTempCoreProx(self.testmods)
        self.false(prox.isfini)
        msgs = await prox.storm('[test:str=beep]').list()
        nodes = [m[1] for m in msgs if m[0] == 'node']
        self.len(1, nodes)
        self.eq(nodes[0][0], ('test:str', 'beep'))
        await prox.fini()
        self.true(prox.isfini)

    def test_doc_data(self):
        with self.getTestDir() as dirn:
            s_common.gendir(dirn, 'docdata', 'stuff')

            docdata = s_common.genpath(dirn, 'docdata')

            root = s_common.genpath(dirn, 'synapse', 'userguides')

            d = {'key': 'value'}

            s_common.jssave(d, docdata, 'data.json')
            s_common.yamlsave(d, docdata, 'data.yaml')
            s_msgpack.dumpfile(d, os.path.join(docdata, 'data.mpk'))
            with s_common.genfile(docdata, 'stuff', 'data.txt') as fd:
                fd.write('beep'.encode())
            with s_common.genfile(docdata, 'data.jsonl') as fd:
                fd.write(json.dumps(d).encode() + b'\n')
                fd.write(json.dumps(d).encode() + b'\n')
                fd.write(json.dumps(d).encode() + b'\n')

            data = s_jupyter.getDocData('data.json', root)
            self.eq(data, d)
            data = s_jupyter.getDocData('data.yaml', root)
            self.eq(data, d)
            data = s_jupyter.getDocData('data.mpk', root)
            self.eq(data, d)
            data = s_jupyter.getDocData('stuff/data.txt', root)
            self.eq(data, b'beep')
            data = s_jupyter.getDocData('data.jsonl', root)
            self.eq(data, [d, d, d])

            self.raises(ValueError, s_jupyter.getDocData, 'newp.bin', root)
            self.raises(ValueError, s_jupyter.getDocData,
                        '../../../../../../etc/passwd', root)

    async def test_stormcore(self):
        outp = self.getTestOutp()
        stormcore, svcprox = await s_jupyter.getTempCoreStormStormsvc('testsvc', Tstsvc.anit, outp=outp)

        self.false(stormcore.isfini)
        self.false(svcprox.isfini)

        msgs = await stormcore.storm('service.list')
        self.stormIsInPrint('true (testsvc)', msgs)

        await stormcore.storm('testsvc.magic', num=1)

        with self.raises(AssertionError):
            await stormcore.storm('testsvc.magic', num=999)

        outp.clear()
        msgs = await stormcore.storm('$lib.print(hello)', cli=True)
        self.stormIsInPrint('hello', msgs)
        outp.expect('storm> $lib.print(hello)')
        outp.expect('storm> $lib.print(hello)\nhello')

        self.eq('shazam', await svcprox.testmeth())

        await stormcore.fini()
        self.true(stormcore.isfini)

        await svcprox.fini()
        self.true(svcprox.isfini)
