import synapse.tests.utils as s_test

import synapse.lib.output as s_output

import synapse.tools.storm as s_t_storm

class StormCliTest(s_test.SynTest):

    async def test_tools_storm(self):

        async with self.getTestCore() as core:

            async with core.getLocalProxy() as proxy:

                outp = s_output.OutPutStr()
                async with await s_t_storm.StormCli.anit(proxy, outp=outp) as scli:
                    await scli.runCmdLine('[inet:ipv4=1.2.3.4 +#foo=2012 ]')
                    text = str(outp)
                    self.isin('.....', text)
                    self.isin('inet:ipv4=1.2.3.4', text)
                    self.isin(':type = unicast', text)
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
