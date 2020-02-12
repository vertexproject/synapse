import json
import asyncio
import logging

import synapse.tests.utils as s_t_utils

import synapse.tools.healthcheck as s_t_healthcheck

logger = logging.getLogger(__name__)

class HealthcheckTest(s_t_utils.SynTest):

    async def test_healthcheck(self):

        # Show a passing / failing healthcheck on a cell
        async with self.getTestCoreAndProxy() as (core, prox):
            curl = core.getLocalUrl()
            outp = self.getTestOutp()

            argv = ['-c', curl]

            retn = await s_t_healthcheck.main(argv, outp)
            self.eq(retn, 0)
            resp = json.loads(str(outp))
            self.isinstance(resp, dict)

            mod = core.modules.get('synapse.tests.utils.TestModule')  # type: s_t_utils.TestModule
            mod.healthy = False

            outp.clear()
            retn = await s_t_healthcheck.main(argv, outp)
            self.eq(retn, 1)
            resp = json.loads(str(outp))
            self.isinstance(resp, dict)

            # Sad paths

            # timeout during check
            logger.info('Checking with a timeout')
            async def sleep(*args, **kwargs):
                await asyncio.sleep(0.6)
            core.addHealthFunc(sleep)
            outp.clear()
            retn = await s_t_healthcheck.main(['-c', curl, '-t', '0.2'], outp)
            self.eq(retn, 1)
            resp = json.loads(str(outp))
            self.eq(resp.get('components')[0].get('name'), 'error')
            m = 'Timeout getting health information from cell.'
            self.eq(resp.get('components')[0].get('mesg'), m)
            core._health_funcs.remove(sleep)

            logger.info('Checking with the incorrect password')
            outp.clear()
            _, port = await core.dmon.listen('tcp://127.0.0.1:0')
            root = await core.auth.getUserByName('root')
            await root.setPasswd('secret')
            retn = await s_t_healthcheck.main(['-c', f'tcp://root:newp@127.0.0.1:{port}/cortex', '-t', '0.2'], outp)
            self.eq(retn, 1)
            resp = json.loads(str(outp))
            self.eq(resp.get('components')[0].get('name'), 'error')
            m = 'Synapse error encountered.'
            self.eq(resp.get('components')[0].get('mesg'), m)

            # dont do this in prod...
            logger.info('Checking without perms')
            await root.setAdmin(False)
            outp.clear()
            retn = await s_t_healthcheck.main(['-c', curl, '-t', '0.2'], outp)
            self.eq(retn, 1)
            resp = json.loads(str(outp))
            self.eq(resp.get('components')[0].get('name'), 'error')
            m = 'Synapse error encountered.'
            self.eq(resp.get('components')[0].get('mesg'), m)

            # do this sad test last ...
            logger.info('Checking a finid cortex')
            await prox.fini()
            await core.fini()
            await asyncio.sleep(0)
            outp.clear()
            retn = await s_t_healthcheck.main(['-c', curl, '-t', '0.2'], outp)
            self.eq(retn, 1)
            resp = json.loads(str(outp))
            self.eq(resp.get('components')[0].get('name'), 'error')
            m = 'Unable to connect to cell.'
            self.eq(resp.get('components')[0].get('mesg'), m)
