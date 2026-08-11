import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.tools.utils.mdstorm as s_t_mdstorm

import synapse.tests.utils as s_test

class MdStormCliTest(s_test.SynTest):

    async def test_mdstorm_cli_help_lists_directives(self):
        outp = s_output.OutPutStr()
        with self.raises(s_exc.ParserExit):
            await s_t_mdstorm.main(('--help',), outp=outp)

        text = str(outp)
        self.isin('## Available mdstorm directives', text)
        self.isin('### ```mdstorm\n', text)
        self.isin('### ```mdstorm-setup\n', text)
        self.isin('### ```mdshell\n', text)
        self.isin('### ```mdautodoc\n', text)
        self.isin('- `--hide-query`:', text)
        self.isin('- `--cortex CTOR`:', text)
        self.isin('- `--fail-ok`:', text)
        self.isin('- `--conf CTOR`:', text)
        self.notin('usage: ```', text)

    async def test_mdstorm_cli_stdout(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'in.md')
            with open(path, 'w') as fd:
                fd.write('# Hello\n')

            outp = s_output.OutPutStr()
            retn = await s_t_mdstorm.main((path,), outp=outp)
            self.eq(0, retn)
            self.isin('# Hello', str(outp))

    async def test_mdstorm_cli_save(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'in.md')
            outpath = s_common.genpath(dirn, 'out.md')
            with open(path, 'w') as fd:
                fd.write('# Hello\n')

            retn = await s_t_mdstorm.main((path, '--save', outpath))
            self.eq(0, retn)
            with open(outpath) as fd:
                self.isin('# Hello', fd.read())
