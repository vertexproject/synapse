import synapse.exc as s_exc

import synapse.common as s_common

import synapse.tools.rstorm as s_rstorm

import synapse.tests.utils as s_test
import synapse.tests.test_lib_rstorm as s_test_rstorm

class RStormToolTest(s_test.SynTest):

    async def test_tool_rstorm(self):

        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'test.rst')
            with s_common.genfile(path) as fd:
                fd.write(s_test_rstorm.rst_in.encode())

            outpath = s_common.genpath(dirn, 'out.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            self.eq(text, s_test_rstorm.rst_out)

            # debug output
            path = s_common.genpath(dirn, 'test2.rst')
            with s_common.genfile(path) as fd:
                fd.write(s_test_rstorm.rst_in_debug.encode())

            outpath = s_common.genpath(dirn, 'out2.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            self.isin('node:edits', text)
            self.isin('inet:ipv4', text)

            # props output
            path = s_common.genpath(dirn, 'test3.rst')
            with s_common.genfile(path) as fd:
                fd.write(s_test_rstorm.rst_in_props.encode())

            outpath = s_common.genpath(dirn, 'out3.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)

            self.eq(text_nocrt, s_test_rstorm.rst_out_props)

            # boom1 test
            path = s_common.genpath(dirn, 'boom1.rst')
            with s_common.genfile(path) as fd:
                fd.write(s_test_rstorm.boom1.encode())

            with self.raises(s_exc.NoSuchVar):
                await s_rstorm.main(('--save', outpath, path))
