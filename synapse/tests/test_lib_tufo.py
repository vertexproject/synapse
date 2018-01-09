import unittest

import synapse.lib.tufo as s_tufo

from synapse.tests.common import *

# Unittests for synapse/lib/tufo.py

class TufoEqualityTest(SynTest):
    def setUp(self):
        self.t1 = s_tufo.tufo('bar', baz='faz', derp=20)
        self.t2 = s_tufo.tufo('bar', derp=20, baz='faz')
        self.t3 = s_tufo.tufo('foo', derp=20, baz='faz')
        self.t4 = s_tufo.tufo('bar', derp=20, baz='faz', prop='value')
        self.t5 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20, 'namespace:sound': 'quack'})
        self.t6 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20})

    def test_equals(self):
        '''
        Ensure that tufo equality works where expected.
        '''
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t2)
        self.true(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t6)
        self.true(r)

    def test_not_equals(self):
        '''
        Ensure that tufo equality works where expected.
        '''
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t3)
        self.false(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t4)
        self.false(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t5)
        self.false(r)


class TufoCreateTests(SynTest):
    def setUp(self):
        self.tuf0 = ('bar', {'baz': 'faz', 'derp': 20})

    def test_simple_tufo_creation(self):
        '''
        Ensure that tufos can be created with explicit arguments.
        '''
        tuf0 = s_tufo.tufo('bar', baz='faz', derp=20)
        r = s_tufo.equal(tuf0, self.tuf0)
        self.true(r)

    def test_kwargs_tufo_creation(self):
        '''
        Ensure that tufos' can be created via **kwargs.
        '''
        tuf0 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20, })
        r = s_tufo.equal(tuf0, self.tuf0)
        self.true(r)


class TestTufoProps(SynTest):
    def setUp(self):
        self.t1 = s_tufo.tufo('bar', baz='faz', derp=20)
        self.t2 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20, 'namespace:sound': 'quack'})
        self.t3 = ('duck', {'tufo:form': 'animal', 'animal:stype': 'duck', 'animal:sound': 'quack'})

    def test_default_props(self):
        '''
        Ensure that when no prefix is provided, the properties are taken from the form.
        '''
        r = s_tufo.props(self.t1)
        self.eq(r, {})
        r = s_tufo.props(self.t2)
        self.eq(r, {})
        r = s_tufo.props(self.t3)
        self.eq(r, {'sound': 'quack', 'stype': 'duck'})

    def test_named_props(self):
        '''
        Ensure that provided prefixes are used.
        '''
        r = s_tufo.props(self.t2, pref='namespace')
        self.eq(r, {'sound': 'quack'})
        r = s_tufo.props(self.t3, pref='animal')
        self.eq(r, {'sound': 'quack', 'stype': 'duck'})
        r = s_tufo.props(self.t3, pref='geo')
        self.eq(r, {})

    def test_lib_tufo_prop(self):

        node = ('asdf', {'tufo:form': 'foo:bar', 'foo:bar:baz': 10})

        self.eq(s_tufo.prop(node, ':baz'), 10)
        self.eq(s_tufo.prop(node, 'foo:bar:baz'), 10)

        self.none(s_tufo.prop(node, ':haha'))
        self.none(s_tufo.prop(node, 'hehe:haha'))

class TufoTests(SynTest):
    def test_tufo_tagged(self):
        tufo = ('1234', {'tufo:form': 'foo:bar',
                         'foo:bar': '1234',
                         '#hehe': 1234})

        self.true(s_tufo.tagged(tufo, 'hehe'))
        self.false(s_tufo.tagged(tufo, 'haha'))
        self.raises(TypeError, s_tufo.tagged, tufo, 1234)
