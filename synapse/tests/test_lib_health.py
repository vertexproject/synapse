import synapse.lib.health as s_healthcheck

import synapse.tests.utils as s_t_utils


class HealthcheckTest(s_t_utils.SynTest):

    async def test_healthcheck(self):

        # .healthy property setter behavior
        hcheck = s_healthcheck.HealthCheck('test')
        with self.raises(AttributeError):
            hcheck.setStatus(True)
        with self.raises(ValueError):
            hcheck.setStatus('okay')

        # Ensure that we can only degrade status
        self.eq(hcheck.getStatus(), 'nominal')
        hcheck.setStatus('nominal')
        self.eq(hcheck.getStatus(), 'nominal')
        hcheck.setStatus('degraded')
        self.eq(hcheck.getStatus(), 'degraded')
        hcheck.setStatus('failed')
        self.eq(hcheck.getStatus(), 'failed')
        hcheck.setStatus('degraded')
        self.eq(hcheck.getStatus(), 'failed')
        hcheck.setStatus('nominal')
        self.eq(hcheck.getStatus(), 'failed')

        # Show a passing / failing healthcheck on a cell
        async with self.getTestCoreAndProxy() as (core, prox):
            snfo1 = await prox.getHealthCheck()
            self.eq(snfo1.get('status'), 'nominal')
            self.eq(snfo1.get('iden'), core.getCellIden())
            comps = snfo1.get('components')
            testdata = [comp for comp in comps if comp.get('name') == 'testmodule'][0]
            self.eq(testdata,
                    {'status': 'nominal',
                     'name': 'testmodule',
                     'mesg': 'Test module is healthy',
                     'data': {'beep': 0}})

            # The TestModule registers a syn:health event handler on the Cortex
            mod = core.modules.get('synapse.tests.utils.TestModule')  # type: s_t_utils.TestModule
            # Now force the module into a degraded state.
            mod.healthy = False

            snfo2 = await prox.getHealthCheck()
            self.eq(snfo2.get('status'), 'failed')
            comps = snfo2.get('components')
            testdata = [comp for comp in comps if comp.get('name') == 'testmodule'][0]
            self.eq(testdata,
                    {'status': 'failed',
                     'name': 'testmodule',
                     'mesg': 'Test module is unhealthy',
                     'data': {'beep': 1}})
