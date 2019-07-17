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

    def test_healthcheck(self):

        # .healthy property setter behavior
        hcheck = s_healthcheck.HealthCheck('test')
        self.true(hcheck.healthy)
        hcheck.healthy = True
        self.true(hcheck.healthy)
        hcheck.healthy = False
        self.false(hcheck.healthy)
        hcheck.healthy = True
        self.false(hcheck.healthy)

        # Data updating and packing for serialization
        hcheck = s_healthcheck.HealthCheck()
