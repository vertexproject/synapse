import os

import synapse.common as s_common
import synapse.tests.utils as s_test

import synapse.tools.genpkg as s_genpkg

dirname = os.path.dirname(__file__)

class GenPkgTest(s_test.SynTest):

    async def test_tools_genpkg(self):

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yml')
        async with self.getTestCore() as core:

            savepath = s_common.genpath(core.dirn, 'testpkg.json')

            url = core.getLocalUrl()
            argv = ('--push', url, '--save', savepath, ymlpath)

            await s_genpkg.main(argv)

            await core.callStorm('testcmd')
            await core.callStorm('$lib.import(testmod)')

            pdef = s_common.yamlload(savepath)

            self.eq(pdef['name'], 'testpkg')
            self.eq(pdef['version'], (0, 0, 1))
            self.eq(pdef['modules'][0]['name'], 'testmod')
            self.eq(pdef['modules'][0]['storm'], 'inet:ipv4\n')
            self.eq(pdef['commands'][0]['name'], 'testcmd')
            self.eq(pdef['commands'][0]['storm'], 'inet:ipv6\n')

            self.eq(pdef['optic']['files']['index.html']['file'], 'aGkK')
