# -*- coding: utf-8 -*-
"""
synapse - test_lib_iq.py.py
Created on 10/21/17.

Test for synapse.lib.iq classes
"""
import synapse.glob as s_glob

import synapse.lib.iq as s_iq

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

        # Cortex helpers

        with self.getRamCore() as core:
            self.isinstance(core, s_cores_common.Cortex)
            self.nn(core.getTufoByProp('syn:form', 'guidform'))
            waiter = self.getTestWait(core, 1, 'node:add')
            core.formTufoByProp('strform', 'oh hai')
            self.len(1, waiter.wait())

        with self.getDmonCore() as core:
            self.isinstance(core, s_telepath.Proxy)
            self.nn(core.getTufoByProp('syn:form', 'guidform'))

        with self.getDirCore() as core:
            self.isinstance(core, s_cores_common.Cortex)
            opt = core.getConfOpt('dir')
            self.true(os.path.isdir(opt))

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

    def test_iq_syntest_envars(self):
        os.environ['foo'] = '1'
        os.environ['bar'] = '2'

        with self.setTstEnvars(foo=1, bar='joke', baz=1234) as cm:
            self.none(cm)
            self.eq(os.environ.get('foo'), '1')
            self.eq(os.environ.get('bar'), 'joke')
            self.eq(os.environ.get('baz'), '1234')

        self.eq(os.environ.get('foo'), '1')
        self.eq(os.environ.get('bar'), '2')
        self.none(os.environ.get('baz'))

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

    def test_common_hierarchy(self):
        blob = (10, 'hehe')
        e = (type(10), type('hehe'))
        r = s_iq.objhierarchy(blob)
        self.eq(r, e)

        tufo = (None, {'woah': 'dude', 'hehe': 1, 'haha': set(['1', '2']), 'foo': ['bar', 'baz']})

        e = (type(None), {'woah': type(''), 'hehe': type(0),
                          'haha': set([type('')]), 'foo': [type(''), type('')]},)
        r = s_iq.objhierarchy(tufo)
        self.eq(r, e)

        tufo = (None, {'gen': (i for i in range(1))})
        e = (type(None), {'gen': types.GeneratorType})
        r = s_iq.objhierarchy(tufo)
        self.eq(r, e)

    def test_cmdg_simple_sequence(self):
        cmdg = CmdGenerator(['foo', 'bar'])
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'quit')
        self.eq(cmdg(), 'quit')

    def test_cmdg_evnt(self):
        cmdg = CmdGenerator(['foo', 'bar'], on_end='spam')
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'spam')
        cmdg.fire('syn:cmdg:add', cmd='hehe')
        self.eq(cmdg(), 'hehe')
        self.eq(cmdg(), 'spam')

    def test_cmdg_end_actions(self):
        cmdg = CmdGenerator(['foo', 'bar'], on_end='spam')
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'spam')
        self.eq(cmdg(), 'spam')

    def test_cmdg_end_exception(self):
        cmdg = CmdGenerator(['foo', 'bar'], on_end=EOFError)
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        with self.raises(EOFError) as cm:
            cmdg()
        self.assertIn('No further actions', str(cm.exception))

    def test_cmdg_end_exception_unknown(self):
        cmdg = CmdGenerator(['foo', 'bar'], on_end=1)
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        with self.raises(Exception) as cm:
            cmdg()
        self.assertIn('Unhandled end action', str(cm.exception))

    def test_teststeps(self):
        # Helper function - he is used a few times
        def setStep(w, stepper, step):
            time.sleep(w)
            stepper.done(step)

        names = ['hehe', 'haha', 'ohmy']
        tsteps = self.getTestSteps(names)
        self.isinstance(tsteps, s_iq.TestSteps)

        tsteps.done('hehe')
        self.true(tsteps.wait('hehe', 1))

        s_glob.pool.call(setStep, 0.1, tsteps, 'haha')
        self.true(tsteps.wait('haha', 1))

        s_glob.pool.call(setStep, 0.2, tsteps, 'ohmy')
        self.raises(StepTimeout, tsteps.wait, 'ohmy', 0.01)
        self.true(tsteps.wait('ohmy', 1))

        # use the waitall api
        tsteps = self.getTestSteps(names)

        s_glob.pool.call(setStep, 0.01, tsteps, 'hehe')
        s_glob.pool.call(setStep, 0.10, tsteps, 'haha')
        s_glob.pool.call(setStep, 0.05, tsteps, 'ohmy')
        self.true(tsteps.waitall(1))

        tsteps = self.getTestSteps(names)
        self.raises(StepTimeout, tsteps.waitall, 0.1)

        # Use the step() api
        tsteps = self.getTestSteps(names)
        s_glob.pool.call(setStep, 0.1, tsteps, 'haha')
        self.true(tsteps.step('hehe', 'haha', 1))

        tsteps = self.getTestSteps(names)
        self.raises(StepTimeout, tsteps.step, 'hehe', 'haha', 0.01)
