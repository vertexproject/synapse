import copy

import synapse.exc as s_exc
import synapse.lib.autodoc as s_autodoc
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_t_utils

class AutodocTest(s_t_utils.SynTest):

    def test_autodoc_rsthelp(self):

        page = s_autodoc.RstHelp()

        page.addHead('test', lvl=0, link='fakeLink')
        page.addLines('test', 'words\n go', 'here')
        page.addHead('burma', lvl=1)
        page.addLines('burma', 'shave')
        text = page.getRstText()
        expected = '''

fakeLink

####
test
####

test
words\n go
here

*****
burma
*****

burma
shave'''
        self.eq(text, expected)

    def test_autodoc_helpers(self):

        # callsig
        rtype = {
            'args': (
                {'name': 'foo',
                 'type': 'str',
                 'desc': 'The foos!'},
                {'name': 'bar',
                 'type': ['str', 'int'],
                 'desc': 'The bar.',
                 'default': None},
                {'name': '**kwargs',
                 'type': 'any',
                 'desc': 'Extra foobars.',
                 },
            )
        }
        callsig = s_autodoc.genCallsig(rtype)
        self.eq(callsig, '(foo, bar=(null), **kwargs)')
        self.eq(s_autodoc.genCallsig({}), '()')
        self.eq(s_autodoc.genCallsig({'args': ({'name': 'beep'},)}), '(beep)')

        # get arg lines
        self.eq(s_autodoc.getArgLines({}), [])
        lines = s_autodoc.getArgLines(rtype)
        self.eq(lines, ['\n', 'Args:', '    foo (str): The foos!', '\n',
                        '    bar: The bar. The input type may be one of the following: ``str``, ``int``.',
                        '\n', '    \\*\\*kwargs (any): Extra foobars.', '\n'])

        lines = s_autodoc.getArgLines({'args': [{'name': 'cmplx', 'type': {}, 'desc': 'unsupported'}]})
        self.eq(lines, ['\n', 'Args:',
                        '    cmplx: unsupported The input type is derived from the declarative type ``{}``.',
                        '\n'])

        with self.raises(AssertionError):
            s_autodoc.getArgLines({'args': [{'name': 'newp', 'type': 1234, 'desc': 'newp'}]})

        # return lines
        lines = s_autodoc.getReturnLines('str')
        self.eq(lines, ('', 'Returns:', '    The type is ``str``.'))
        lines = s_autodoc.getReturnLines(('str', 'int'))
        self.eq(lines, ('', 'Returns:', '    The type may be one of the following: ``str``, ``int``.'))

        lines = s_autodoc.getReturnLines({'returns': {'type': 'str', 'desc': 'The str!'}})
        self.eq(lines, ('', 'Returns:', '    The str! The return type is ``str``.'))

        lines = s_autodoc.getReturnLines({'returns': {'type': ['str', 'boolean']}})
        self.eq(lines, ('', 'Returns:', '    The return type may be one of the following: ``str``, ``boolean``.'))

        lines = s_autodoc.getReturnLines({'returns': {'type': ['str', 'boolean']}}, isstor=True)
        self.eq(lines, ('', 'Returns:', '    The return type may be one of the following: ``str``, ``boolean``.',
                        '    When this is used to set the value, it does not have a return type.'))

        lines = s_autodoc.getReturnLines({'returns': {'type': 'str', 'name': 'Yields'}})
        self.eq(lines, ('', 'Yields:', '    The return type is ``str``.'))

        lines = s_autodoc.getReturnLines({'returns': {'type': {}}})
        self.eq(lines, ('', 'Returns:', '    The return type is derived from the declarative type ``{}``.'))

        with self.raises(AssertionError):
            s_autodoc.getReturnLines({'returns': {'type': 1234}})

        # prepare lines
        text = '''
        Hello

        Notes:
            Beep beep goes the docs

        Examples:
            Words!::

                example stuff
        '''
        lines = s_autodoc.prepareRstLines(text)
        self.eq(lines, ['Hello', '', 'Notes:', '    Beep beep goes the docs', '', 'Examples:',
                        '    Words!::', '', '        example stuff', ''])

        # Whole thing
        libtst = s_t_utils.LibTst

        locls = copy.deepcopy(libtst._storm_locals)
        # Strip _funcname out. This is normally done in the registry code.
        [obj.get('type', {}).pop('_funcname', None) for obj in locls]
        doc = {
            'desc': s_stormtypes.getDoc(libtst, "err"),
            'path': ('lib',) + libtst._storm_lib_path,
            'locals': locls,
        }
        page = s_autodoc.RstHelp()
        page.addHead('Test')
        page.addLines('I am a line.')
        s_autodoc.docStormTypes(page, (doc,), linkprefix='test')
        text = page.getRstText()
        expected = '''
####
Test
####

I am a line.


.. _test-lib-test:

********
lib.test
********

LibTst for testing!



.. _test-lib-test-beep:

beep(valu)
==========

.. warning::
   ``$lib.test.beep`` has been deprecated and will be removed on or after 8080-08-08.


Example storm func.

Notes:
    It beeps strings!


Args:
    valu (str): The value to beep.



Returns:
    The beeped string. The return type is ``str``.


.. _test-lib-test-someargs:

someargs(valu, bar=(true), faz=(null))
======================================

.. warning::
   ``$lib.test.someargs`` has been deprecated and will be removed in version v3.0.0.
   This is a test library was deprecated from the day it was made.


Example storm func with args.


Args:
    valu (str): The value to beep.


    bar (bool): The value to beep.


    faz (str): The value to beep.



Returns:
    The beeped string. The return type is ``str``.'''
        self.eq(text, expected)

        # Now as a library
        page = s_autodoc.RstHelp()
        page.addHead('Test')
        page.addLines('I am a line.')
        s_autodoc.docStormTypes(page, (doc,), linkprefix='test', islib=True)
        text = page.getRstText()
        expected = '''
####
Test
####

I am a line.


.. _test-lib-test:

*********
$lib.test
*********

LibTst for testing!



.. _test-lib-test-beep:

$lib.test.beep(valu)
====================

.. warning::
   ``$lib.test.beep`` has been deprecated and will be removed on or after 8080-08-08.


Example storm func.

Notes:
    It beeps strings!


Args:
    valu (str): The value to beep.



Returns:
    The beeped string. The return type is ``str``.


.. _test-lib-test-someargs:

$lib.test.someargs(valu, bar=(true), faz=(null))
================================================

.. warning::
   ``$lib.test.someargs`` has been deprecated and will be removed in version v3.0.0.
   This is a test library was deprecated from the day it was made.


Example storm func with args.


Args:
    valu (str): The value to beep.


    bar (bool): The value to beep.


    faz (str): The value to beep.



Returns:
    The beeped string. The return type is ``str``.'''
        self.eq(text, expected)

        badlocls = copy.deepcopy(libtst._storm_locals)
        badlocls[0]['deprecated']['eolvers'] = 'v4.4.4'
        page = s_autodoc.RstHelp()
        doc = {
            'desc': s_stormtypes.getDoc(libtst, "err"),
            'path': ('lib',) + libtst._storm_lib_path,
            'locals': badlocls,
        }
        with self.raises(s_exc.SchemaViolation):
            s_autodoc.docStormTypes(page, (doc,), linkprefix='test')

        libdepr = s_t_utils.LibDepr
        locls = copy.deepcopy(libdepr._storm_locals)
        [obj.get('type', {}).pop('_funcname', None) for obj in locls]
        doc = {
            'desc': s_stormtypes.getDoc(libdepr, "err"),
            'path': ('lib',) + libdepr._storm_lib_path,
            'locals': locls,
            'deprecated': libdepr._storm_lib_deprecation
        }
        page = s_autodoc.RstHelp()
        page.addHead('Test')
        page.addLines('I am a line.')
        s_autodoc.docStormTypes(page, (doc,), linkprefix='test', islib=True)
        text = page.getRstText()
        expected = '''
####
Test
####

I am a line.


.. _test-lib-depr:

*********
$lib.depr
*********

Deprecate me!



.. _test-lib-depr-boop:

$lib.depr.boop(valu)
====================

.. warning::
   ``$lib.depr.boop`` has been deprecated and will be removed in version v3.0.0.


An example storm function that's not deprecated on its own, but the entire library is.



Args:
    valu (str): What to boop.



Returns:
    The booped. The return type is ``str``.'''
        self.eq(text, expected)
