import os
import synapse.tests.utils as s_test

import synapse.common as s_common
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.tools.storm as s_t_storm

class StormCliTest(s_test.SynTest):

    async def test_tools_storm(self):

        async with self.getTestCore() as core:

            await core.addTagProp('foo', ('int', {}), {})

            pars = s_t_storm.getArgParser()
            opts = pars.parse_args(('woot',))
            self.eq('woot', opts.cortex)

            q = '$lib.model.ext.addFormProp(inet:ipv4, "_test:score", (int, $lib.dict()), $lib.dict())'
            await core.callStorm(q)

            async with core.getLocalProxy() as proxy:

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('[inet:ipv4=1.2.3.4 +#foo=2012 +#bar +#baz:foo=10 :_test:score=7]')
                    text = str(outp)
                    self.isin('.....', text)
                    self.isin('inet:ipv4=1.2.3.4', text)
                    self.isin(':type = unicast', text)
                    self.isin(':_test:score = 7', text)
                    self.isin('.created = ', text)
                    self.isin('#bar', text)
                    self.isin('#baz:foo = 10', text)
                    self.isin('#foo = (2012/01/01 00:00:00.000, 2012/01/01 00:00:00.001)', text)
                    self.isin('complete. 1 nodes in', text)

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('!quit')
                    self.isin('o/', str(outp))
                    self.true(scli.isfini)

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('!help')
                    self.isin('!quit', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('$lib.print(woot)')
                    self.isin('woot', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('$lib.warn(woot)')
                    self.isin('WARNING: woot', str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('---')
                    self.isin("---\n ^\nSyntax Error: Unexpected token '-' at line 1, column 2", str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('spin |' + ' ' * 80 + '---')
                    self.isin("...                             ---\n                                 ^", str(outp))

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('---' + ' ' * 80 + 'spin')
                    self.isin("---                            ...\n ^", str(outp))

            lurl = core.getLocalUrl()

            outp = s_output.OutPutStr()
            await s_t_storm.main((lurl, '$lib.print(woot)'), outp=outp)
            self.isin('woot', str(outp))

            outp = s_output.OutPutStr()
            await s_t_storm.main((lurl, f'!runfile --help'), outp=outp)
            self.isin('Run a local storm file', str(outp))

            with self.getTestDir() as dirn:

                path = os.path.join(dirn, 'foo.storm')
                with open(path, 'wb') as fd:
                    fd.write(b'$lib.print(woot)')

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!runfile {path}'), outp=outp)
                self.isin(f'running storm file: {path}', str(outp))
                self.isin('woot', str(outp))

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!runfile /newp.storm'), outp=outp)
                self.isin(f'no such file: /newp.storm', str(outp))

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!pushfile /newp'), outp=outp)
                self.isin(f'no such file: /newp', str(outp))

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!pushfile {path}'), outp=outp)
                text = str(outp)
                self.isin(f'uploading file: {path}', text)
                self.isin(':name = foo.storm', text)
                self.isin(':sha256 = c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)

                outp = s_output.OutPutStr()
                path = os.path.join(dirn, 'bar.storm')
                await s_t_storm.main((lurl, f'!pullfile c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)

                text = str(outp)
                self.isin('downloading sha256: c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3', text)
                self.isin(f'saved to: {path}', text)

                with s_common.genfile(path) as fd:
                    self.isin('woot', fd.read().decode())

                outp = s_output.OutPutStr()
                await s_t_storm.main((lurl, f'!pullfile c11adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 {path}'), outp=outp)
                text = str(outp)
                self.isin('Axon does not contain the requested file.', text)

                await scli.runCmdLine('[test:str=foo +#foo +#bar +#baz]')
                await scli.runCmdLine('[test:str=bar +#foo +#bar +#baz]')

                path = os.path.join(dirn, 'export1.nodes')
                await s_t_storm.main((lurl, f'!export {path} {{ test:str }}'), outp=outp)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.sorteq(('bar', 'baz', 'foo'), pode[1]['tags'])

                path = os.path.join(dirn, 'export2.nodes')
                q = f'!export {path} {{ test:str }} --include-tags foo bar'
                await s_t_storm.main((lurl, q), outp=outp)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.sorteq(('bar', 'foo'), pode[1]['tags'])

                path = os.path.join(dirn, 'export3.nodes')
                q = f'!export {path} {{ test:str }} --no-tags'
                await s_t_storm.main((lurl, q), outp=outp)
                text = str(outp)
                self.isin(f'saved 2 nodes to: {path}', text)

                with open(path, 'rb') as fd:
                    byts = fd.read()
                    podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                    self.sorteq(('bar', 'foo'), [p[0][1] for p in podes])
                    for pode in podes:
                        self.eq({}, pode[1]['tags'])

                await s_t_storm.main((lurl, f'!export {path} {{ test:newp }}'), outp=outp)
                text = str(outp)
                self.isin('No property named test:newp.', text)
