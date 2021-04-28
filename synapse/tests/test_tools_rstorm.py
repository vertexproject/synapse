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
.. storm-pre:: [ inet:ipv6=0 ]
.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml
.. storm:: --hide-props testcmd foo
.. storm:: --hide-query $lib.print(secret)
.. storm:: --hide-query file:bytes
'''

rst_out = '''
HI
##
::

    > $lib.print($bar) $lib.warn(omgomgomg)
    baz
    WARNING: omgomgomg

::

    > testcmd foo
    inet:ipv6=::ffff:0

::

    secret

::



'''

rst_in_debug = '''
HI
##
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm:: --debug [ inet:ipv4=0 ]
'''

rst_in_props = '''
HI
##
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm:: [ inet:ipv4=0 ]
'''

rst_out_props = '''
HI
##
::

    > [ inet:ipv4=0 ]
    inet:ipv4=0.0.0.0
            :type = private

'''

rst_in_http = '''
HI
##
.. storm-cortex:: synapse.tools.rstorm.cortex
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() $lib.print($d)
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp1.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ipv4=$d.data ]
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp2.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ipv4=$d.data ]
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

boom4 = '''

.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml

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

            # debug output
            path = s_common.genpath(dirn, 'test2.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_debug.encode())

            outpath = s_common.genpath(dirn, 'out2.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            self.isin('node:edits', text)
            self.isin('inet:ipv4', text)

            # props output
            path = s_common.genpath(dirn, 'test3.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_props.encode())

            outpath = s_common.genpath(dirn, 'out3.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)

            self.eq(text_nocrt, rst_out_props)

            # http
            path = s_common.genpath(dirn, 'http.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_http.encode())

            outpath = s_common.genpath(dirn, 'http.rst')

            await s_rstorm.main(('--save', outpath, path))

            with s_common.genfile(outpath) as fd:
                text = fd.read().decode()

            self.isin('{}', text)  # no mock gives empty response
            self.isin('inet:ipv4=1.2.3.4', text)  # first mock
            self.isin('inet:ipv4=5.6.7.8', text)  # one mock at a time

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

            # boom4 test
            path = s_common.genpath(dirn, 'boom4.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom4.encode())

            with self.raises(s_exc.NoSuchVar):
                await s_rstorm.main(('--save', outpath, path))
