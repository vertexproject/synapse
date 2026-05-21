import synapse.tests.utils as s_t_utils

import synapse.lib.thishost as s_thishost

class ThisTest(s_t_utils.SynTest):

    def test_thishost_hostname(self):
        self.nn(s_thishost.get('hostname'))

    def test_thishost_ptrsize(self):
        self.nn(s_thishost.get('ptrsize'))

    def test_thishost_platform(self):
        self.nn(s_thishost.get('platform'))
