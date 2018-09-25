import synapse.lib.threads as s_threads

import synapse.tests.common as s_t_common
import synapse.tests.utils as s_t_utils

class ThreadsTest(s_t_utils.SynTest):

    def test_threads_pool(self):

        func = s_t_common.CallBack()
        with s_threads.Pool() as pool:

            pool.call(func, 20, 30)

            self.true(func.wait(timeout=1))
            func.args = (20, 30)

    def test_threads_pool_wrap(self):

        func = s_t_common.CallBack()
        with s_threads.Pool() as pool:

            pool.wrap(func)(20, 30)

            self.true(func.wait(timeout=1))
            func.args = (20, 30)
