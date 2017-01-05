import unittest

import synapse.lib.tufo as s_tufo

# Unittests for synapse/lib/tufo.py


class TufoEqualityTest(unittest.TestCase):
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
        self.assertTrue(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t6)
        self.assertTrue(r)

    def test_not_equals(self):
        '''
        Ensure that tufo equality works where expected.
        '''
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t3)
        self.assertFalse(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t4)
        self.assertFalse(r)
        r = s_tufo.equal(tuf0=self.t1, tuf1=self.t5)
        self.assertFalse(r)


class TufoCreateTests(unittest.TestCase):
    def setUp(self):
        self.tuf0 = ('bar', {'baz': 'faz', 'derp': 20})

    def test_simple_tufo_creation(self):
        '''
        Ensure that tufos can be created with explicit arguments.
        '''
        tuf0 = s_tufo.tufo('bar', baz='faz', derp=20)
        r = s_tufo.equal(tuf0, self.tuf0)
        self.assertTrue(r)

    def test_kwargs_tufo_creation(self):
        '''
        Ensure that tufos' can be created via **kwargs.
        '''
        tuf0 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20,})
        r = s_tufo.equal(tuf0, self.tuf0)
        self.assertTrue(r)


class TestTufoProps(unittest.TestCase):
    def setUp(self):
        self.t1 = s_tufo.tufo('bar', baz='faz', derp=20)
        self.t2 = s_tufo.tufo('bar', **{'baz': 'faz', 'derp': 20, 'namespace:sound': 'quack'})
        self.t3 = ('duck', {'tufo:form': 'animal', 'animal:stype': 'duck', 'animal:sound': 'quack'})

    def test_default_props(self):
        '''
        Ensure that when no prefix is provided, the properties are taken from the form.
        '''
        r = s_tufo.props(self.t1)
        self.assertEqual(r, {})
        r = s_tufo.props(self.t2)
        self.assertEqual(r, {})
        r = s_tufo.props(self.t3)
        self.assertEqual(r, {'sound': 'quack', 'stype': 'duck'})

    def test_named_props(self):
        '''
        Ensure that provided prefixes are used.
        '''
        r = s_tufo.props(self.t2, pref='namespace')
        self.assertEqual(r, {'sound': 'quack'})
        r = s_tufo.props(self.t3, pref='animal')
        self.assertEqual(r, {'sound': 'quack', 'stype': 'duck'})
        r = s_tufo.props(self.t3, pref='geo')
        self.assertEqual(r, {})

