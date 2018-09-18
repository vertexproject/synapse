# -*- coding: utf-8 -*-
"""
synapse - test_utils.py.py
Created on 10/21/17.

Test for synapse.tests.utils classes
"""
import os
import time
import logging
import synapse.glob as s_glob

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.output as s_output

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class TestUtils(s_t_utils.SynTest):
    def test_syntest_helpers(self):
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

        # try mirroring an arbitrary direcotry
        with self.getTestDir() as fdir1:
            with s_common.genfile(fdir1, 'hehe.haha') as fd:
                fd.write('hehe'.encode())
            with self.getTestDir(fdir1) as fdir2:
                with s_common.genfile(fdir2, 'hehe.haha') as fd:
                    self.eq(fd.read(), 'hehe'.encode())

        outp = self.getTestOutp()
        self.isinstance(outp, s_output.OutPut)

        # FIXME - Test Fix Cortex helper tests
        # # Cortex helpers
        #
        # with self.getRamCore() as core:
        #     self.isinstance(core, s_cores_common.Cortex)
        #     self.nn(core.getTufoByProp('syn:form', 'guidform'))
        #     waiter = self.getTestWait(core, 1, 'node:add')
        #     core.formTufoByProp('strform', 'oh hai')
        #     self.len(1, waiter.wait())
        #
        # with self.getDmonCore() as core:
        #     self.isinstance(core, s_telepath.Proxy)
        #     self.nn(core.getTufoByProp('syn:form', 'guidform'))
        #
        # with self.getDirCore() as core:
        #     self.isinstance(core, s_cores_common.Cortex)
        #     opt = core.getConfOpt('dir')
        #     self.true(os.path.isdir(opt))

    def test_syntest_logstream(self):
        with self.getLoggerStream('synapse.tests.test_utils') as stream:
            logger.error('ruh roh i am a error message')
        stream.seek(0)
        mesgs = stream.read()
        self.isin('ruh roh', mesgs)

    def test_syntest_logstream_event(self):

        @s_common.firethread
        def logathing():
            time.sleep(0.01)
            logger.error('StreamEvent Test Message')

        logger.error('notthere')
        with self.getLoggerStream('synapse.tests.test_utils', 'Test Message') as stream:
            thr = logathing()
            self.true(stream.wait(10))
            thr.join()

        stream.seek(0)
        mesgs = stream.read()
        self.isin('StreamEvent Test Message', mesgs)
        self.notin('notthere', mesgs)

    def test_syntest_envars(self):
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

    def test_outp(self):
        outp = s_t_utils.TstOutPut()
        outp.printf('Test message #1!')
        outp.expect('#1')
        self.raises(Exception, outp.expect, 'oh my')

    def test_testenv(self):
        ebus = s_eventbus.EventBus()

        with s_t_utils.TstEnv() as env:
            foo = 'foo'
            env.add('ebus', ebus, True)
            env.add('foo', foo)

            self.true(env.ebus is ebus)
            self.true(env.foo is foo)

            def blah():
                blah = env.blah

            self.raises(AttributeError, blah)

        self.true(ebus.isfini)

    def test_cmdg_simple_sequence(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'])
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'quit')
        self.eq(cmdg(), 'quit')

    def test_cmdg_evnt(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'], on_end='spam')
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'spam')
        cmdg.fire('syn:cmdg:add', cmd='hehe')
        self.eq(cmdg(), 'hehe')
        self.eq(cmdg(), 'spam')

    def test_cmdg_end_actions(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'], on_end='spam')
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        self.eq(cmdg(), 'spam')
        self.eq(cmdg(), 'spam')

    def test_cmdg_end_exception(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'], on_end=EOFError)
        self.eq(cmdg(), 'foo')
        self.eq(cmdg(), 'bar')
        with self.raises(EOFError) as cm:
            cmdg()
        self.assertIn('No further actions', str(cm.exception))

    def test_cmdg_end_exception_unknown(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'], on_end=1)
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
        self.isinstance(tsteps, s_t_utils.TestSteps)

        tsteps.done('hehe')
        self.true(tsteps.wait('hehe', 1))

        s_glob.pool.call(setStep, 0.1, tsteps, 'haha')
        self.true(tsteps.wait('haha', 1))

        s_glob.pool.call(setStep, 0.2, tsteps, 'ohmy')
        self.raises(s_exc.StepTimeout, tsteps.wait, 'ohmy', 0.01)
        self.true(tsteps.wait('ohmy', 1))

        # use the waitall api
        tsteps = self.getTestSteps(names)

        s_glob.pool.call(setStep, 0.01, tsteps, 'hehe')
        s_glob.pool.call(setStep, 0.10, tsteps, 'haha')
        s_glob.pool.call(setStep, 0.05, tsteps, 'ohmy')
        self.true(tsteps.waitall(1))

        tsteps = self.getTestSteps(names)
        self.raises(s_exc.StepTimeout, tsteps.waitall, 0.1)

        # Use the step() api
        tsteps = self.getTestSteps(names)
        s_glob.pool.call(setStep, 0.1, tsteps, 'haha')
        self.true(tsteps.step('hehe', 'haha', 1))

        tsteps = self.getTestSteps(names)
        self.raises(s_exc.StepTimeout, tsteps.step, 'hehe', 'haha', 0.01)

    def test_istufo(self):
        node = (None, {})
        self.istufo(node)
        node = ('1234', {})
        self.istufo(node)

        self.raises(AssertionError, self.istufo, [None, {}])
        self.raises(AssertionError, self.istufo, (None, {}, {}))
        self.raises(AssertionError, self.istufo, (1234, set()))
        self.raises(AssertionError, self.istufo, (None, set()))

    def test_getTestCell(self):
        with self.getTestDir() as dirn:
            boot = {'auth:en': True}
            conf = {'test': 1}
            with self.getTestCell(dirn, 'cortex', boot, conf) as cortex:
                self.eq(os.path.join(dirn, 'cortex'), cortex.dirn)
                self.eq(cortex.conf.get('test'), 1)
                self.eq(cortex.boot.get('auth:en'), True)

    @s_glob.synchelp
    async def test_async(self):

        async def araiser():
            return 1 / 0

        await self.asyncraises(ZeroDivisionError, araiser())

    def test_dmoncoreaxon(self):
        with self.getTestDmonCortexAxon() as dmon:
            self.isin('core', dmon.cells)
            self.isin('axon00', dmon.cells)
            self.isin('blobstor00', dmon.cells)

            with self.getTestProxy(dmon, 'core', user='root', passwd='root') as core:
                node = core.addNode('teststr', 'hehe')
                self.nn(node)
