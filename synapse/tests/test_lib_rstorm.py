import os

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.rstorm as s_rstorm

import synapse.tests.utils as s_test

rst_in = '''
HI
##
.. storm-cortex:: default
.. storm-cortex:: default
.. storm-opts:: {"vars": {"foo": 10, "bar": "baz"}}
.. storm-pre:: [ inet:asn=$foo ]
.. storm:: $lib.print($bar) $lib.warn(omgomgomg)
.. storm-expect:: baz
.. storm-pre:: [ inet:ipv6=0 ]
.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml
.. storm:: --hide-props testpkgcmd foo
.. storm:: --hide-query $lib.print(secret)
.. storm:: --hide-query file:bytes
.. storm-svc:: synapse.tests.files.rstorm.testsvc.Testsvc test {"secret": "jupiter"}
.. storm:: testsvc.test
'''

rst_out = '''
HI
##
::

    > $lib.print($bar) $lib.warn(omgomgomg)
    baz
    WARNING: omgomgomg

::

    > testpkgcmd foo
    inet:ipv6=::ffff:0

::

    secret

::



::

    > testsvc.test
    jupiter

'''

rst_in_debug = '''
HI
##
.. storm-cortex:: default
.. storm:: --debug [ inet:ipv4=0 ]
'''

rst_in_props = '''
HI
##
.. storm-cortex:: default
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
.. storm-cortex:: default
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() $lib.print($d)
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp1.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ipv4=$d.data ]
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp2.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ipv4=$d.data ]
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp3.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.body.decode() [ it:dev:str=$d ]
'''

boom1 = '''

.. storm:: $lib.print(newp)

'''

boom2 = '''

.. storm-pre:: $lib.print(newp)

'''

boom3 = '''

.. storm-cortex:: default
.. storm:: $x = (10 + "foo")

'''

boom4 = '''

.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml

'''

boom5 = '''

.. storm-svc:: synapse.tests.files.rstorm.testsvc.Testsvc test {"secret": "jupiter"}

'''

boom6 = '''

.. storm-cortex:: default
.. storm-svc:: synapse.tests.files.rstorm.testsvc.Testsvc test

'''

boom7 = '''

.. storm-cortex:: default
.. storm-pkg:: synapse/tests/files/stormpkg/newp.newp

'''

boom8 = '''

.. storm-cortex:: default
.. storm-mock-http:: synapse/tests/files/rstorm/newp.newp

'''

boom9 = '''

.. storm-newp:: newp

'''

async def get_rst_text(rstfile):
    async with await s_rstorm.StormRst.anit(rstfile) as rstorm:
        lines = await rstorm.run()
        return ''.join(lines)

class RStormLibTest(s_test.SynTest):

    async def test_lib_rstorm(self):

        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'test.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in.encode())

            text = await get_rst_text(path)
            self.eq(text, rst_out)

            # debug output
            path = s_common.genpath(dirn, 'test2.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_debug.encode())

            text = await get_rst_text(path)
            self.isin('node:edits', text)
            self.isin('inet:ipv4', text)

            # props output
            path = s_common.genpath(dirn, 'test3.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_props.encode())

            text = await get_rst_text(path)
            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)
            self.eq(text_nocrt, rst_out_props)

            # http
            path = s_common.genpath(dirn, 'http.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_http.encode())

            text = await get_rst_text(path)
            self.isin('{}', text)  # no mock gives empty response
            self.isin('inet:ipv4=1.2.3.4', text)  # first mock
            self.isin('inet:ipv4=5.6.7.8', text)  # one mock at a time
            self.isin('it:dev:str=notjson', text)  # one mock at a time

            # boom1 test
            path = s_common.genpath(dirn, 'boom1.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom1.encode())

            with self.raises(s_exc.NoSuchVar):
                await get_rst_text(path)

            # boom2 test
            path = s_common.genpath(dirn, 'boom2.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom2.encode())

            with self.raises(s_exc.NoSuchVar):
                await get_rst_text(path)

            # boom3 test
            path_boom3 = s_common.genpath(dirn, 'boom3.rst')
            with s_common.genfile(path_boom3) as fd:
                fd.write(boom3.encode())

            with self.raises(s_exc.StormRuntimeError):
                await get_rst_text(path_boom3)

            # boom4 test
            path = s_common.genpath(dirn, 'boom4.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom4.encode())

            with self.raises(s_exc.NoSuchVar):
                await get_rst_text(path)

            # boom5 test
            path = s_common.genpath(dirn, 'boom5.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom5.encode())

            with self.raises(s_exc.NoSuchVar):
                await get_rst_text(path)

            # boom6 test
            path = s_common.genpath(dirn, 'boom6.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom6.encode())

            with self.raises(s_exc.NeedConfValu):
                await get_rst_text(path)

            # boom7 test
            path = s_common.genpath(dirn, 'boom7.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom7.encode())

            with self.raises(s_exc.NoSuchFile):
                await get_rst_text(path)

            # boom8 test
            path = s_common.genpath(dirn, 'boom8.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom8.encode())

            with self.raises(s_exc.NoSuchFile):
                await get_rst_text(path)

            # boom9 test
            path = s_common.genpath(dirn, 'boom9.rst')
            with s_common.genfile(path) as fd:
                fd.write(boom9.encode())

            with self.raises(s_exc.NoSuchName):
                await get_rst_text(path)

            # make sure things get cleaned up
            async with await s_rstorm.StormRst.anit(path_boom3) as rstorm:
                try:
                    await rstorm.run()
                    self.fail('This must raise')
                except s_exc.StormRuntimeError:
                    pass

            self.true(rstorm.core.isfini)
            self.true(rstorm.isfini)
            self.false(os.path.exists(rstorm.core.dirn))

            # bad path
            path = s_common.genpath(dirn, 'newp.newp')
            with self.raises(s_exc.BadConfValu):
                await get_rst_text(path)
