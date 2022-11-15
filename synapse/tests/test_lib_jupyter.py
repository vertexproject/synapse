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
            'synapse_minversion': (2, 8, 0),
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

    async def test_tempcorecmdr(self):
        outp = self.getTestOutp()
        cmdrcore = await s_jupyter.getTempCoreCmdr(self.testmods, outp)
        self.false(cmdrcore.isfini)
        nodes = await cmdrcore.eval('[test:str=beep]', cmdr=True)
        self.len(1, nodes)
        self.eq(nodes[0][0], ('test:str', 'beep'))
        self.true(outp.expect('cli> storm [test:str=beep]'))
        await cmdrcore.fini()
        self.true(cmdrcore.isfini)

    async def test_tempcoreprox(self):
        prox = await s_jupyter.getTempCoreProx(self.testmods)
        self.false(prox.isfini)
        msgs = await prox.storm('[test:str=beep]').list()
        nodes = [m[1] for m in msgs if m[0] == 'node']
        self.len(1, nodes)
        self.eq(nodes[0][0], ('test:str', 'beep'))
        await prox.fini()
        self.true(prox.isfini)

    async def test_tempcorecmdrstormsvc(self):
        cmdrcore, svcprox = await s_jupyter.getTempCoreCmdrStormsvc('testsvc', Tstsvc.anit)

        self.false(cmdrcore.isfini)
        self.false(svcprox.isfini)

        mesgs = await cmdrcore.storm('service.list')
        self.true(any(['True (testsvc)' in str(mesg) for mesg in mesgs]))

        nodes = await cmdrcore.eval('testsvc.magic')
        self.len(1, nodes)

        self.eq('shazam', await svcprox.testmeth())

        await cmdrcore.fini()
        self.true(cmdrcore.isfini)

        await svcprox.fini()
        self.true(svcprox.isfini)

    async def test_cmdrcore(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            outp = self.getTestOutp()
            async with await s_jupyter.CmdrCore.anit(core, outp=outp) as cmdrcore:
                podes = await cmdrcore.eval('[test:str=beep]',
                                            num=1, cmdr=False)
                self.len(1, podes)
                self.false(outp.expect('[test:str=beep]', throw=False))

                mesgs = await cmdrcore.storm('[test:str=boop]',
                                             num=1, cmdr=True)
                self.true(outp.expect('[test:str=boop]', throw=False))
                podes = [m[1] for m in mesgs if m[0] == 'node']
                self.gt(len(mesgs), len(podes))
                self.len(1, podes)
                self.eq(podes[0][0], ('test:str', 'boop'))

                # Opts works for cmdr=False
                podes = await cmdrcore.eval('[test:str=$foo]',
                                            {'vars': {'foo': 'duck'}},
                                            num=1, cmdr=False)
                self.len(1, podes)
                self.eq(podes[0][0], ('test:str', 'duck'))

                # Opts does not work with cmdr=True - we have no way to plumb it through.
                with self.getAsyncLoggerStream('synapse.lib.view',
                                               'Error during storm execution') as stream:
                    with self.raises(AssertionError):
                        await cmdrcore.eval('[test:str=$foo]',
                                              opts={'vars': {'foo': 'fowl'}},
                                              cmdr=True)
                    self.true(await stream.wait(6))

                # Assertion based tests
                podes = await cmdrcore.eval('test:int', num=0)
                self.len(0, podes)
                podes = await cmdrcore.eval('test:str', num=3)
                self.len(3, podes)
                await self.asyncraises(AssertionError, cmdrcore.eval('test:str', num=1))

                # Feed function for data loading
                data = [
                    (('test:int', 137), {}),
                ]

                await cmdrcore.addFeedData('syn.nodes', data)
                podes = await cmdrcore.eval('test:int=137',
                                            num=1, cmdr=False)
                self.len(1, podes)

        # Raw cmdline test
        async with self.getTestCoreAndProxy() as (realcore, core):

            outp = self.getTestOutp()
            async with await s_jupyter.CmdrCore.anit(core, outp=outp) as cmdrcore:
                await cmdrcore.runCmdLine('help')
                self.true(outp.expect('cli> help'))
                self.true(outp.expect('List commands and display help output.'))

    async def test_log_supression(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            outp = self.getTestOutp()
            async with await s_jupyter.CmdrCore.anit(core, outp=outp) as cmdrcore:
                with self.getAsyncLoggerStream('synapse.lib.view') as stream:
                    mesgs = await cmdrcore.storm('[test:int=beep]',
                                                 num=0, cmdr=False,
                                                 suppress_logging=True)
                    self.stormIsInErr('invalid literal for int', mesgs)
                stream.seek(0)
                self.notin('Error during storm execution', stream.read())

                with self.getAsyncLoggerStream('synapse.lib.view',
                                                     'Error during storm execution') as stream:
                    mesgs = await cmdrcore.storm('[test:int=beep]',
                                                 num=0, cmdr=False,
                                                 suppress_logging=False)
                    self.true(await stream.wait(6))
                    self.stormIsInErr('invalid literal for int', mesgs)

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
