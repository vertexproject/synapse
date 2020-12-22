import synapse.exc as s_exc
import synapse.tests.utils as s_test

import synapse.common as s_common
import synapse.tools.rstorm as s_rstorm

rst_in = '''
HI
##
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm-opts:: {"vars": {"foo": 10, "bar": "baz"}}
.. storm-pre:: [ inet:asn=$foo ]
.. storm:: $lib.print($bar) $lib.warn(omgomgomg)
.. storm-expect:: baz
'''

rst_out = '''
HI
##
::

    > $lib.print($bar) $lib.warn(omgomgomg)
    baz
    WARNING: omgomgomg

'''

boom1 = '''

.. storm:: $lib.print(newp)

'''

boom2 = '''

.. storm-pre:: $lib.print(newp)

'''

boom3 = '''

.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm:: $x = (10 + "foo")

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

            # boom1 test
            path = s_common.genpath(dirn, 'boom1.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom1.encode())

            with self.raises(s_exc.NoSuchVar):
                await s_rstorm.main(('--save', outpath, path))

            # boom2 test
            path = s_common.genpath(dirn, 'boom2.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom2.encode())

            with self.raises(s_exc.NoSuchVar):
                await s_rstorm.main(('--save', outpath, path))

            # boom3 test
            path = s_common.genpath(dirn, 'boom3.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom3.encode())

            with self.raises(s_exc.StormRuntimeError):
                await s_rstorm.main(('--save', outpath, path))
