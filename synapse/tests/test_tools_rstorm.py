import synapse.tests.utils as s_test

import synapse.common as s_common
import synapse.tools.rstorm as s_rstorm

rst_in = '''
HI
##
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm-opts:: {"vars": {"foo": 10, "bar": "baz"}}
.. storm-pre:: [ inet:asn=$foo ]
.. storm:: $lib.print($bar)
.. storm-expect:: baz
'''

rst_out = '''
HI
##
::

    > $lib.print($bar)
    baz

'''

class RStormTest(s_test.SynTest):

    async def test_rstorm(self):

        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'test.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in.encode())

            outpath = s_common.genpath(dirn, 'out.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            self.eq(text, rst_out)
