# -*- coding: utf-8 -*-
"""
synapse - test_lib_iq.py.py
Created on 10/21/17.

Test for synapse.lib.iq classes
"""
import logging
import synapse.lib.output as s_output

from synapse.tests.common import *

logger = logging.getLogger(__name__)

class IqTest(SynTest):
    def test_iq_syntest_helpers(self):
        # Execute all of the test helpers here
        self.len(2, (1, 2))

        self.le(1, 2)
        self.le(1, 1)
        self.lt(1, 2)
        self.ge(2, 1)
        self.ge(1, 1)
        self.gt(2, 1)

        self.isin('foo', ('foo', 'bar'))
        self.isin('foo', 'fooobarr')
        self.isin('foo', {'foo': 'bar'})
        self.isin('foo', {'foo', 'bar'})
        self.isin('foo', ['foo', 'bar'])

        self.notin('baz', ('foo', 'bar'))
        self.notin('baz', 'fooobarr')
        self.notin('baz', {'foo': 'bar'})
        self.notin('baz', {'foo', 'bar'})
        self.notin('baz', ['foo', 'bar'])

        self.isinstance('str', str)
        self.isinstance('str', (str, dict))

        self.sorteq((1, 2, 3), [2, 3, 1])

        def div0():
            return 1 / 0
        self.raises(ZeroDivisionError, div0)

        self.none(None)
        self.none({'foo': 'bar'}.get('baz'))

        self.nn(1)
        self.nn({'foo': 'bar'}.get('baz', 'woah'))

        self.true(True)
        self.true(1)
        self.true(-1)
        self.true('str')

        self.false(False)
        self.false(0)
        self.false('')
        self.false(())
        self.false([])
        self.false({})
        self.false(set())

        self.eq(True, 1)
        self.eq(False, 0)
        self.eq('foo', 'foo')
        self.eq({'1', '2'}, {'2', '1', '2'})
        self.eq({'key': 'val'}, {'key': 'val'})

        self.ne(True, 0)
        self.ne(False, 1)
        self.ne('foo', 'foobar')
        self.ne({'1', '2'}, {'2', '1', '2', '3'})
        self.ne({'key': 'val'}, {'key2': 'val2'})

        self.noprop({'key': 'valu'}, 'foo')

        with self.getTestDir() as fdir:
            self.true(os.path.isdir(fdir))
        self.false(os.path.isdir(fdir))

        outp = self.getTestOutp()
        self.isinstance(outp, s_output.OutPut)

        with self.getRamCore() as core:
            self.isinstance(core, s_cores_common.Cortex)
            self.nn(core.getTufoByProp('syn:form', 'guidform'))
            waiter = self.getTestWait(core, 1, 'node:add')
            core.formTufoByProp('strform', 'oh hai')
            self.len(1, waiter.wait())

        with self.getDmonCore() as core:
            self.isinstance(core, s_telepath.Proxy)
            self.nn(core.getTufoByProp('syn:form', 'guidform'))

    def test_iq_syntest_psql(self):
        core = self.getPgCore()
        self.isinstance(core, s_cores_common.Cortex)
        self.nn(core.getTufoByProp('syn:form', 'syn:core'))
        core.fini()

        conn = self.getPgConn()
        self.eq(conn.closed, 0)

    def test_iq_syntest_logstream(self):
        with self.getLoggerStream('synapse.tests.test_lib_iq') as stream:
            logger.error('ruh roh i am a error message')
        stream.seek(0)
        mesgs = stream.read()
        self.isin('ruh roh', mesgs)

    def test_iq_outp(self):
        outp = TstOutPut()
        outp.printf('Test message #1!')
        outp.expect('#1')
        self.raises(Exception, outp.expect, 'oh my')

    def test_iq_testenv(self):
        core = s_cortex.openurl('ram://')
        with TstEnv() as env:
            foo = 'foo'
            env.add('core', core, True)
            env.add('foo', foo)

            self.true(env.core is core)
            self.true(env.foo is foo)

            def blah():
                blah = env.blah

            self.raises(AttributeError, blah)

        self.true(core.isfini)
