import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.modelrev as s_modelrev
import synapse.lib.remotelayer as s_remotelayer

import synapse.lib.health as s_healthcheck

import synapse.tests.utils as s_t_utils
import synapse.tests.test_cortex as t_cortex


class HealthcheckTest(s_t_utils.SynTest):

    async def test_healthcheck(self):

        # .healthy property setter behavior
        hcheck = s_healthcheck.HealthCheck('test')
        self.true(hcheck.healthy)
        hcheck.healthy = True
        self.true(hcheck.healthy)
        hcheck.healthy = False
        self.false(hcheck.healthy)
        hcheck.healthy = True
        self.false(hcheck.healthy)

        # Show a passing / failing healthcheck on a cell
        async with self.getTestCoreAndProxy() as (core, prox):
            snfo1 = await prox.getHealthCheck()
            self.true(snfo1.get('health'))
            self.eq(snfo1.get('iden'), core.getCellIden())
            data = snfo1.get('components')
            testdata = data.get('testmodule')
            self.eq(testdata,
                    {'status': True,
                     'mesg': 'Test module is healthy',
                     'data': {'beep': 0}})

            # The TestModule registers a syn:health event handler on the Cortex
            mod = core.modules.get('synapse.tests.utils.TestModule')  # type: s_t_utils.TestModule
            # Now force the module into a degraded state.
            mod.healthy = False

            snfo2 = await prox.getHealthCheck()
            self.false(snfo2.get('health'))
            data = snfo2.get('components')
            testdata = data.get('testmodule')
            self.eq(testdata,
                    {'status': False,
                     'mesg': 'Test module is unhealthy',
                     'data': {'beep': 1}})
