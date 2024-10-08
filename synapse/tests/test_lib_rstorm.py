import os
import textwrap

import vcr

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
.. storm-pre:: [ inet:ip='::ffff:0.0.0.0' ]
.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml
.. storm:: --hide-props testpkgcmd foo
.. storm-pre:: inet:ip='::ffff:0.0.0.0' [ +#foo ]
.. storm:: --hide-props --hide-tags testpkgcmd foo
.. storm:: --hide-query $lib.print(secret) $lib.print($lib.globals.get(testpkg))
.. storm:: --hide-query file:bytes
.. storm:: --hide-query for $m in ([]) { break } for $m in ([]) { continue }
.. storm-svc:: synapse.tests.files.rstorm.testsvc.Testsvc test {"secret": "jupiter"}
.. storm-cli:: testsvc.test
'''

rst_out = '''
HI
##
::

    storm> $lib.print($bar) $lib.warn(omgomgomg)
    baz
    WARNING: omgomgomg

::

    storm> testpkgcmd foo
    inet:ip=::ffff:0.0.0.0

::

    storm> testpkgcmd foo
    inet:ip=::ffff:0.0.0.0

::

    secret
    testpkg-done

::


::


::

    storm> testsvc.test
    jupiter
    testsvc-done

'''

rst_in_props = '''
HI
##
.. storm-cortex:: default
.. storm:: [ inet:ip=([4, 0]) ]
'''

rst_out_props = '''
HI
##
::

    storm> [ inet:ip=([4, 0]) ]
    inet:ip=0.0.0.0
            :type = private
            :version = 4

'''

rst_in_http = '''
HI
##
.. storm-cortex:: default
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp1.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ip=$d.data ]
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp2.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.json() [ inet:ip=$d.data ]
.. storm-mock-http:: synapse/tests/files/rstorm/httpresp3.json
.. storm:: $resp=$lib.inet.http.get("http://foo.com") $d=$resp.body.decode() [ it:dev:str=$d ]
'''

multi_rst_in_http = '''
.. storm-cortex:: default
.. storm-mock-http:: synapse/tests/files/rstorm/httprespmulti.yaml
.. storm:: $r_addr=$lib.inet.http.get("http://example.com") $r_bin=$lib.inet.http.get("http://foo.com") $lib.print($r_addr.body) $lib.print($r_bin.body.decode())
'''

multi_rst_in_http_opts = '''
.. storm-cortex:: default
.. storm-vcr-opts:: {"record_mode": "none"}
.. storm-vcr-callback:: synapse.tests.test_lib_rstorm.vcrcallbacktst
.. storm-mock-http:: /this/path/does/not/exist.yaml
.. storm:: $resp = $lib.inet.http.get("http://example.com") if $resp.body { $lib.print('unexpected results') } else { $lib.print('this test passed') }
'''

storm_http_sadpath_callback = '''
.. storm-cortex:: default
.. storm-vcr-callback:: synapse.tests.test_lib_rstorm.newp
'''


clear_storm_opts = '''
.. storm-cortex:: default
.. storm-opts:: {"vars": {"foobar": "bar"}}
.. storm-clear-http:: true
.. storm:: $lib.print($lib.str.concat($foobar, "bizboz"))
'''

stormenv = '''
.. storm-cortex:: default
.. storm-envvar:: RST_TEST_FQDN=wootwoot.com
.. storm-pre:: [ inet:fqdn?=$RST_TEST_FQDN ]
.. storm:: inet:fqdn
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

.. storm-newp:: newp

'''

multiline_storm_input = '''
.. storm-cortex:: default
Hello
.. storm-multiline:: QUERY="[inet:ip=1.4.2.3]\\n[+#test.tag]"
.. storm:: MULTILINE=QUERY
Bye!
'''

multiline_storm_output = '''
Hello
::

    storm> [inet:ip=1.4.2.3]
    [+#test.tag]
    inet:ip=1.4.2.3
            :type = unicast
            :version = 4
            #test.tag

Bye!
'''


multiline00_input = '''
A multiline secondary property.
.. storm-cortex:: default
.. storm-opts:: {"vars": {"name": "Node\\nWith a\\nweird name"}}
.. storm:: [meta:note=(n1,) :text=$name]
Bye!
'''

multiline00_output = '''
A multiline secondary property.
::

    storm> [meta:note=(n1,) :text=$name]
    meta:note=85d3511b97098d7fd9e07be21f6390de
            :text = Node
                    With a
                    weird name

Bye!
'''

fail00 = '''

.. storm-cortex:: default

A fail test

.. storm-pre:: [inet:ip=1.2.3.4]
.. storm-fail:: true
.. storm:: inet:ip=woot.com

# Fail state is cleared

.. storm:: inet:ip=1.2.3.4

'''

fail01 = fail00 + '''
Since the fail state was cleared, now we'll fail on the next error.

.. storm:: inet:ip=woot.com
'''

fail02 = '''
.. storm-cortex:: default

A fail test that expects to fail but does not.

.. storm-pre:: [inet:ip=1.2.3.4]
.. storm-fail:: true
.. storm:: inet:ip=1.2.3.4
'''

ctor_fail = '''
HI
##
.. storm-cortex:: path.to.NewpCell
'''

pkg_onload_timeout = '''
.. storm-cortex:: default
.. storm-pre:: $lib.globals.set(onload_sleep, 2)
.. storm-pkg:: synapse/tests/files/stormpkg/testpkg.yaml
'''

svc_onload_timeout = '''
.. storm-cortex:: default
.. storm-pre:: $lib.globals.set(onload_sleep, 2)
.. storm-svc:: synapse.tests.files.rstorm.testsvc.Testsvc test {"secret": "jupiter"}
'''

async def get_rst_text(rstfile):
    async with await s_rstorm.StormRst.anit(rstfile) as rstorm:
        lines = await rstorm.run()
        return ''.join(lines)

callback_dict = {}
def vcrcallbacktst(recorder: vcr.VCR):
    assert isinstance(recorder, vcr.VCR), f'Wrong callback type, got a {type(recorder)}'
    callback_dict['called'] = True

class RStormLibTest(s_test.SynTest):

    async def test_lib_rstorm(self):

        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'test.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in.encode())

            text = await get_rst_text(path)
            self.eq(text, rst_out)

            # props output
            path = s_common.genpath(dirn, 'test3.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_props.encode())

            text = await get_rst_text(path)
            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)
            self.eq(text_nocrt, rst_out_props)

            # Multiline secondary properties
            path = s_common.genpath(dirn, 'multiline00.rst')
            with s_common.genfile(path) as fd:
                fd.write(multiline00_input.encode())
            text = await get_rst_text(path)
            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)
            self.eq(text_nocrt, multiline00_output)

            path = s_common.genpath(dirn, 'multiline_input.rst')
            with s_common.genfile(path) as fd:
                fd.write(multiline_storm_input.encode())
            text = await get_rst_text(path)
            text_nocrt = '\n'.join(line for line in text.split('\n') if '.created =' not in line)
            self.eq(text_nocrt, multiline_storm_output)

            # http
            path = s_common.genpath(dirn, 'http.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_in_http.encode())

            text = await get_rst_text(path)
            self.isin('inet:ip=1.2.3.4', text)  # first mock
            self.isin('inet:ip=5.6.7.8', text)  # one mock at a time
            self.isin('it:dev:str=notjson', text)  # one mock at a time

            # multi request in 1 rstorm command
            path = s_common.genpath(dirn, 'http_multi.rst')
            with s_common.genfile(path) as fd:
                fd.write(multi_rst_in_http.encode())
            text = await get_rst_text(path)
            self.isin("<ANSI STANDARD PIZZA>", text)
            self.isin("<This is (not) a test>", text)

            # Pass some vcr opts through
            callback_dict.clear()
            self.notin('called', callback_dict)
            path = s_common.genpath(dirn, 'http_multi_opts.rst')
            with s_common.genfile(path) as fd:
                fd.write(multi_rst_in_http_opts.encode())
            text = await get_rst_text(path)
            self.isin('this test passed', text)
            self.true(callback_dict.get('called'))

            # Sad path test on a callback
            path = s_common.genpath(dirn, 'http_sadpath_callback.rst')
            with s_common.genfile(path) as fd:
                fd.write(storm_http_sadpath_callback.encode())
            with self.raises(s_exc.NoSuchCtor):
                await get_rst_text(path)

            # clear the current set of things
            path = s_common.genpath(dirn, 'clear_storm_opts.rst')
            with s_common.genfile(path) as fd:
                fd.write(clear_storm_opts.encode())
            with self.raises(s_exc.StormRuntimeError):
                text = await get_rst_text(path)

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

            # storm-envvar
            path = s_common.genpath(dirn, 'stormenv.rst')
            with s_common.genfile(path) as fd:
                fd.write(stormenv.encode())
            text = await get_rst_text(path)
            self.notin("vertex.link", text)
            self.isin("wootwoot.com", text)

            with self.setTstEnvars(RST_TEST_FQDN='vertex.link'):
                path = s_common.genpath(dirn, 'stormenv.rst')
                with s_common.genfile(path) as fd:
                    fd.write(stormenv.encode())
                text = await get_rst_text(path)
                self.isin("vertex.link", text)
                self.notin("wootwoot.com", text)

            # storm-fail tests
            path = s_common.genpath(dirn, 'fail00.rst')
            with s_common.genfile(path) as fd:
                fd.write(fail00.encode())
            text = await get_rst_text(path)
            self.isin('ERROR: Invalid IP address', text)
            self.isin('storm> inet:ip=1.2.3.4', text)
            self.isin(':type = unicast', text)

            path = s_common.genpath(dirn, 'fail01.rst')
            with s_common.genfile(path) as fd:
                fd.write(fail01.encode())
            with self.raises(s_exc.StormRuntimeError):
                await get_rst_text(path)

            path = s_common.genpath(dirn, 'fail02.rst')
            with s_common.genfile(path) as fd:
                fd.write(fail02.encode())
            with self.raises(s_exc.StormRuntimeError):
                await get_rst_text(path)

            path = s_common.genpath(dirn, 'ctor_fail.rst')
            with s_common.genfile(path) as fd:
                fd.write(ctor_fail.encode())
            with self.raises(s_exc.NoSuchCtor):
                await get_rst_text(path)

            # onload failures

            try:
                oldv = s_rstorm.ONLOAD_TIMEOUT
                s_rstorm.ONLOAD_TIMEOUT = 0.1

                path = s_common.genpath(dirn, 'pkg_onload_timeout.rst')
                with s_common.genfile(path) as fd:
                    fd.write(pkg_onload_timeout.encode())
                with self.raises(s_exc.SynErr) as ectx:
                    await get_rst_text(path)
                self.eq('Package onload failed to run for testpkg', ectx.exception.errinfo['mesg'])

                path = s_common.genpath(dirn, 'svc_onload_timeout.rst')
                with s_common.genfile(path) as fd:
                    fd.write(svc_onload_timeout.encode())
                with self.raises(s_exc.SynErr) as ectx:
                    await get_rst_text(path)
                self.eq('Package onload failed to run for service test', ectx.exception.errinfo['mesg'])

            finally:
                s_rstorm.ONLOAD_TIMEOUT = oldv

    async def test_lib_rstorm_cmdargs(self):
        rst_cmdargs = textwrap.dedent('''
        HI
        ##
        .. storm-cortex:: default
        .. storm:: --hide-query [ps:person=(p0,) :name='1.2.3.4'] | scrape --refs | -(refs)> *
        ''')

        with self.getTestDir() as dirn:

            path = s_common.genpath(dirn, 'test.rst')
            with s_common.genfile(path) as fd:
                fd.write(rst_cmdargs.encode())

            text = await get_rst_text(path)
            self.notin('[ps:person=(p0,)', text)
            self.isin('inet:ip=1.2.3.4', text)
