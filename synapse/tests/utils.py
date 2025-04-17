'''
This contains the core test helper code used in Synapse.

This gives the opportunity for third-party users of Synapse to test their
code using some of the same helpers used to test Synapse.

The core class, synapse.tests.utils.SynTest is a subclass of unittest.TestCase,
with several wrapper functions to allow for easier calls to assert* functions,
with less typing.  There are also Synapse specific helpers, to load Cortexes and
whole both multi-component environments into memory.

Since SynTest is built from unittest.TestCase, the use of SynTest is
compatible with the unittest, nose and pytest frameworks.  This does not lock
users into a particular test framework; while at the same time allowing base
use to be invoked via the built-in Unittest library, with one important exception:
due to an unfortunate design approach, you cannot use the unittest module command
line to run a *single* async unit test.  pytest works fine though.

'''
import io
import os
import sys
import copy
import math
import types
import shutil
import typing
import asyncio
import inspect
import logging
import tempfile
import unittest
import threading
import contextlib
import collections

import unittest.mock as mock

import vcr
import regex
import aiohttp

from prompt_toolkit.formatted_text import FormattedText

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.cryotank as s_cryotank
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha
import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.cmdr as s_cmdr
import synapse.lib.hive as s_hive
import synapse.lib.json as s_json
import synapse.lib.task as s_task
import synapse.lib.const as s_const
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.modelrev as s_modelrev
import synapse.lib.thishost as s_thishost
import synapse.lib.structlog as s_structlog
import synapse.lib.stormtypes as s_stormtypes

import synapse.tools.genpkg as s_genpkg

logger = logging.getLogger(__name__)

logging.getLogger('vcr').setLevel(logging.ERROR)

# Default LMDB map size for tests
TEST_MAP_SIZE = s_const.gibibyte

async def alist(coro):
    return [x async for x in coro]

def norm(z):
    if isinstance(z, (list, tuple)):
        return tuple([norm(n) for n in z])
    if isinstance(z, dict):
        return {norm(k): norm(v) for (k, v) in z.items()}
    return z

def deguidify(x):
    return regex.sub('[0-9a-f]{32}', '*' * 32, x)

def jsonlines(text: str):
    lines = [k for k in text.split('\n') if k]
    return [s_json.loads(line) for line in lines]

async def waitForBehold(core, events):
    async for mesg in core.behold():
        for event in list(events):
            for key, valu in event.items():
                if mesg.get(key) != valu:
                    break
            else:
                events.remove(event)

        if len(events) == 0:
            break

@contextlib.asynccontextmanager
async def matchContexts(testself):
    origenter = s_base.Base.__aenter__
    origexit = s_base.Base.__aexit__
    origstorm = s_cortex.Cortex.storm
    orignodes = s_cortex.Cortex.nodes

    contexts = collections.defaultdict(int)

    async def enter(self):
        contexts[type(self)] += 1
        return await origenter(self)

    async def exit(self, exc, cls, tb):
        contexts[type(self)] -= 1
        await origexit(self, exc, cls, tb)

    async def storm(self, text, opts=None):
        async for mesg in origstorm(self, text, opts=opts):
            yield mesg

        for cont, refs in contexts.items():
            testself.eq(0, refs)

    async def nodes(self, text, opts=None):
        nodes = await orignodes(self, text, opts=opts)

        for cont, refs in contexts.items():
            testself.eq(0, refs)

        return nodes

    with mock.patch('synapse.lib.base.Base.__aenter__', enter):
        with mock.patch('synapse.lib.base.Base.__aexit__', exit):
            with mock.patch('synapse.cortex.Cortex.nodes', nodes):
                with mock.patch('synapse.cortex.Cortex.storm', storm):
                    yield

class PickleableMagicMock(mock.MagicMock):
    def __reduce__(self):
        return mock.MagicMock, ()

class LibTst(s_stormtypes.Lib):
    '''
    LibTst for testing!
    '''
    _storm_locals = (
        {'name': 'beep',
         'deprecated': {'eoldate': '8080-08-08'},
         'desc': '''
        Example storm func.

        Notes:
            It beeps strings!''',
         'type': {'type': 'function', '_funcname': 'beep',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The value to beep.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The beeped string.', }}},
        {'name': 'someargs',
         'desc': '''Example storm func with args.''',
         'deprecated': {'eolvers': 'v3.0.0', 'mesg': 'This is a test library was deprecated from the day it was made.'},
         'type': {'type': 'function', '_funcname': 'someargs',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The value to beep.', },
                      {'name': 'bar', 'type': 'bool', 'desc': 'The value to beep.', 'default': True, },
                      {'name': 'faz', 'type': 'str', 'desc': 'The value to beep.', 'default': None, },
                  ),
                  'returns': {'type': 'str', 'desc': 'The beeped string.', }}},
    )
    _storm_lib_path = ('test',)

    def addLibFuncs(self):
        self.locls.update({
            'beep': self.beep,
            'someargs': self.someargs,
        })

    async def beep(self, valu):
        '''
        Example storm func
        '''
        ret = f'A {valu} beep!'
        return ret

    async def someargs(self, valu, bar=True, faz=None):
        '''
        Example storm func
        '''
        ret = f'A {valu} beep which {bar} the {faz}!'
        return ret

class LibDepr(s_stormtypes.Lib):
    '''
    Deprecate me!
    '''
    _storm_locals = (
        {'name': 'boop',
         'desc': '''
         An example storm function that's not deprecated on its own, but the entire library is.
         ''',
         'type': {'type': 'function', '_funcname': 'boop',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'What to boop.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The booped.', }}},
    )
    _storm_lib_path = ('depr',)
    _storm_lib_deprecation = {'eolvers': 'v3.0.0'}

    def addLibFuncs(self):  # pragma: no cover
        self.locls.update({
            'boop': self.boop,
        })

    async def boop(self, valu):  # pragma: no cover
        return f'You have been booped, {valu}!'

class TestType(s_types.Type):

    stortype = s_layer.STOR_TYPE_UTF8

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        return valu.lower(), {}

class ThreeType(s_types.Type):

    stortype = s_layer.STOR_TYPE_U8

    def norm(self, valu):
        return 3, {'subs': {'three': 3}}

    def repr(self, valu):
        return '3'

class TestSubType(s_types.Type):

    stortype = s_layer.STOR_TYPE_U32

    def norm(self, valu):
        valu = int(valu)
        return valu, {'subs': {'isbig': valu >= 1000}}

    def repr(self, norm):
        return str(norm)

class TestRunt:

    def __init__(self, name, **kwargs):
        self.name = name
        self.props = kwargs
        self.props.setdefault('.created', s_common.now())

    def getStorNode(self, form):

        ndef = (form.name, form.type.norm(self.name)[0])
        buid = s_common.buid(ndef)

        pnorms = {}
        for prop, valu in self.props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms,
        })

testmodel = {

    'ctors': (
        ('test:sub', 'synapse.tests.utils.TestSubType', {}, {}),
        ('test:type', 'synapse.tests.utils.TestType', {}, {}),
        ('test:threetype', 'synapse.tests.utils.ThreeType', {}, {}),
    ),
    'interfaces': (
        ('test:interface', {
            'doc': 'test interface',
            'props': (
                ('size', ('int', {}), {}),
                ('names', ('array', {'type': 'str'}), {}),
            ),
            'interfaces': ('inet:proto:request',)
        }),
    ),
    'types': (
        ('test:type10', ('test:type', {'foo': 10}), {
            'doc': 'A fake type.'}),

        ('test:lower', ('str', {'lower': True}), {}),

        ('test:time', ('time', {}), {}),

        ('test:ival', ('ival', {}), {}),

        ('test:ro', ('str', {}), {}),
        ('test:int', ('int', {}), {}),
        ('test:float', ('float', {}), {}),
        ('test:str', ('str', {}), {}),
        ('test:strregex', ('str', {'lower': True, 'strip': True, 'regex': r'^#[^\p{Z}#]+$'}), {}),
        ('test:migr', ('str', {}), {}),
        ('test:auto', ('str', {}), {}),
        ('test:edge', ('edge', {}), {}),
        ('test:guid', ('guid', {}), {}),
        ('test:data', ('data', {}), {}),
        ('test:taxonomy', ('taxonomy', {}), {'interfaces': ('meta:taxonomy',)}),
        ('test:hugenum', ('hugenum', {}), {}),

        ('test:arrayprop', ('guid', {}), {}),
        ('test:arrayform', ('array', {'type': 'int'}), {}),

        ('test:comp', ('comp', {'fields': (
            ('hehe', 'test:int'),
            ('haha', 'test:lower'))
        }), {'doc': 'A fake comp type.'}),
        ('test:compcomp', ('comp', {'fields': (
            ('comp1', 'test:comp'),
            ('comp2', 'test:comp'))
        }), {}),
        ('test:complexcomp', ('comp', {'fields': (
            ('foo', 'test:int'),
            ('bar', ('str', {'lower': True}),),
        )}), {'doc': 'A complex comp type.'}),
        ('test:hexa', ('hex', {}), {'doc': 'anysize test hex type.'}),
        ('test:hex4', ('hex', {'size': 4}), {'doc': 'size 4 test hex type.'}),
        ('test:hexpad', ('hex', {'size': 8, 'zeropad': True}), {'doc': 'size 8 test hex type, zero padded.'}),
        ('test:zeropad', ('hex', {'zeropad': 20}), {'doc': 'test hex type, zero padded to 40 bytes.'}),

        ('test:pivtarg', ('str', {}), {}),
        ('test:pivcomp', ('comp', {'fields': (('targ', 'test:pivtarg'), ('lulz', 'test:str'))}), {}),
        ('test:haspivcomp', ('int', {}), {}),

        ('test:cycle0', ('str', {}), {}),
        ('test:cycle1', ('str', {}), {}),

        ('test:ndef', ('ndef', {}), {}),
        ('test:ndef:formfilter1', ('ndef', {
            'forms': ('inet:ipv4', 'inet:ipv6')
        }), {}),
        ('test:ndef:formfilter2', ('ndef', {
            'interfaces': ('meta:taxonomy',)
        }), {}),
        ('test:ndef:formfilter3', ('ndef', {
            'forms': ('inet:ipv4',),
            'interfaces': ('file:mime:msoffice',)
        }), {}),

        ('test:runt', ('str', {'lower': True, 'strip': True}), {'doc': 'A Test runt node.'}),
        ('test:hasiface', ('str', {}), {'interfaces': ('test:interface',)}),
        ('test:hasiface2', ('str', {}), {'interfaces': ('test:interface',)}),
    ),

    'univs': (
        ('test:univ', ('int', {'min': -1, 'max': 10}), {'doc': 'A test universal property.'}),
        ('univarray', ('array', {'type': 'int'}), {'doc': 'A test array universal property.'}),
    ),

    'forms': (

        ('test:arrayprop', {}, (
            ('ints', ('array', {'type': 'test:int'}), {}),
            ('strs', ('array', {'type': 'test:str', 'split': ','}), {}),
            ('strsnosplit', ('array', {'type': 'test:str'}), {}),
            ('strregexs', ('array', {'type': 'test:strregex', 'uniq': True, 'sorted': True}), {}),
        )),
        ('test:arrayform', {}, (
        )),
        ('test:taxonomy', {}, ()),
        ('test:type10', {}, (

            ('intprop', ('int', {'min': 20, 'max': 30}), {}),
            ('int2', ('int', {}), {}),
            ('strprop', ('str', {'lower': 1}), {}),
            ('guidprop', ('guid', {'lower': 1}), {}),
            ('locprop', ('loc', {}), {}),
        )),

        ('test:cycle0', {}, (
            ('cycle1', ('test:cycle1', {}), {}),
        )),

        ('test:cycle1', {}, (
            ('cycle0', ('test:cycle0', {}), {}),
        )),

        ('test:type', {}, ()),

        ('test:comp', {}, (
            ('hehe', ('test:int', {}), {'ro': True}),
            ('haha', ('test:lower', {}), {'ro': True}),
        )),

        ('test:compcomp', {}, (
            ('comp1', ('test:comp', {}), {'ro': True}),
            ('comp2', ('test:comp', {}), {'ro': True}),
        )),

        ('test:complexcomp', {}, (
            ('foo', ('test:int', {}), {'ro': True}),
            ('bar', ('str', {'lower': 1}), {'ro': True})
        )),

        ('test:int', {}, (
            ('loc', ('loc', {}), {}),
            ('int2', ('int', {}), {}),
        )),

        ('test:float', {}, (
            ('closed', ('float', {'min': 0.0, 'max': 360.0}), {}),
            ('open', ('float', {'min': 0.0, 'max': 360.0, 'minisvalid': False, 'maxisvalid': False}), {}),
        )),

        ('test:edge', {}, (
            ('n1', ('ndef', {}), {'ro': True}),
            ('n1:form', ('str', {}), {'ro': True}),
            ('n2', ('ndef', {}), {'ro': True}),
            ('n2:form', ('str', {}), {'ro': True}),
        )),

        ('test:guid', {}, (
            ('size', ('test:int', {}), {}),
            ('tick', ('test:time', {}), {}),
            ('posneg', ('test:sub', {}), {}),
            ('posneg:isbig', ('bool', {}), {}),
        )),

        ('test:data', {}, (
            ('data', ('test:data', {}), {}),
        )),

        ('test:hugenum', {}, (
            ('huge', ('test:hugenum', {}), {}),
        )),

        ('test:str', {}, (
            ('bar', ('ndef', {}), {}),
            ('baz', ('nodeprop', {}), {}),
            ('tick', ('test:time', {}), {}),
            ('hehe', ('str', {}), {}),
            ('ndefs', ('array', {'type': 'ndef'}), {}),
            ('somestr', ('test:str', {}), {}),
        )),
        ('test:strregex', {}, ()),

        ('test:migr', {}, (
            ('bar', ('ndef', {}), {}),
            ('baz', ('nodeprop', {}), {}),
            ('tick', ('test:time', {}), {}),
        )),

        ('test:threetype', {}, (
            ('three', ('int', {}), {}),
        )),
        ('test:auto', {}, ()),
        ('test:hexa', {}, ()),
        ('test:hex4', {}, ()),
        ('test:zeropad', {}, ()),
        ('test:ival', {}, (
            ('interval', ('ival', {}), {}),
        )),

        ('test:pivtarg', {}, (
            ('name', ('str', {}), {}),
        )),

        ('test:pivcomp', {}, (
            ('targ', ('test:pivtarg', {}), {'ro': True}),
            ('lulz', ('test:str', {}), {'ro': True}),
            ('tick', ('time', {}), {}),
            ('size', ('test:int', {}), {}),
            ('width', ('test:int', {}), {}),
        )),

        ('test:haspivcomp', {}, (
            ('have', ('test:pivcomp', {}), {}),
        )),

        ('test:ndef', {}, (
            ('form', ('str', {}), {'ro': True}),
        )),

        ('test:runt', {'runt': True}, (
            ('tick', ('time', {}), {'ro': True}),
            ('lulz', ('str', {}), {}),
            ('newp', ('str', {}), {'doc': 'A stray property we never use in nodes.'}),
        )),

        ('test:ro', {}, (
            ('writeable', ('str', {}), {'doc': 'writeable property.'}),
            ('readable', ('str', {}), {'doc': 'ro property.', 'ro': True}),
        )),

        ('test:hasiface', {}, ()),
        ('test:hasiface2', {}, ()),

    ),
}

deprmodel = {
    'types': (
        ('test:deprprop', ('test:str', {}), {'deprecated': True}),
        ('test:deprarray', ('array', {'type': 'test:deprprop'}), {}),
        ('test:deprform', ('test:str', {}), {}),
        ('test:deprndef', ('ndef', {}), {}),
        ('test:deprsub', ('str', {}), {}),
        ('test:range', ('range', {}), {}),
        ('test:deprsub2', ('comp', {'fields': (
            ('name', 'test:str'),
            ('range', 'test:range'))
        }), {}),
    ),
    'forms': (
        ('test:deprprop', {}, ()),
        ('test:deprform', {}, (
            ('ndefprop', ('test:deprndef', {}), {}),
            ('deprprop', ('test:deprarray', {}), {}),
            ('okayprop', ('str', {}), {}),
        )),
        ('test:deprsub', {}, (
            ('range', ('test:range', {}), {}),
            ('range:min', ('int', {}), {'deprecated': True}),
            ('range:max', ('int', {}), {}),
        )),
        ('test:deprsub2', {}, (
            ('name', ('str', {}), {}),
            ('range', ('test:range', {}), {}),
            ('range:min', ('int', {}), {}),
            ('range:max', ('int', {}), {'deprecated': True}),
        )),
    ),

}

class TestCmd(s_storm.Cmd):
    '''
    A test command
    '''

    name = 'testcmd'
    forms = {
        'input': [
            'test:str',
            'inet:ipv6',
        ],
        'output': [
            'inet:fqdn',
        ],
        'nodedata': [
            ('foo', 'inet:ipv4'),
            ('bar', 'inet:fqdn'),
        ],
    }

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        return pars

    async def execStormCmd(self, runt, genr):
        async for node, path in genr:
            await runt.printf(f'{self.name}: {node.ndef}')
            yield node, path

class DeprModule(s_module.CoreModule):
    def getModelDefs(self):
        return (
            ('depr', deprmodel),
        )


class TestModule(s_module.CoreModule):
    testguid = '8f1401de15918358d5247e21ca29a814'

    async def initCoreModule(self):

        self.core.setFeedFunc('com.test.record', self.addTestRecords)

        await self.core.addNode(self.core.auth.rootuser, 'meta:source', self.testguid, {'name': 'test'})

        self.core.addStormLib(('test',), LibTst)

        self.healthy = True
        self.core.addHealthFunc(self._testModHealth)

        form = self.model.form('test:runt')
        self.core.addRuntLift(form.full, self._testRuntLift)

        for prop in form.props.values():
            self.core.addRuntLift(prop.full, self._testRuntLift)

        self.core.addRuntPropSet('test:runt:lulz', self._testRuntPropSetLulz)
        self.core.addRuntPropDel('test:runt:lulz', self._testRuntPropDelLulz)

    async def _testModHealth(self, health):
        if self.healthy:
            health.update(self.getModName(), 'nominal',
                          'Test module is healthy', data={'beep': 0})
        else:
            health.update(self.getModName(), 'failed',
                          'Test module is unhealthy', data={'beep': 1})

    async def addTestRecords(self, snap, items):
        for name in items:
            await snap.addNode('test:str', name)

    async def _testRuntLift(self, full, valu=None, cmpr=None, view=None):

        now = s_common.now()
        modl = self.core.model

        runtdefs = [
            (' BEEP ', {'tick': modl.type('time').norm('2001')[0], 'lulz': 'beep.sys', '.created': now}),
            ('boop', {'tick': modl.type('time').norm('2010')[0], '.created': now}),
            ('blah', {'tick': modl.type('time').norm('2010')[0], 'lulz': 'blah.sys'}),
            ('woah', {}),
        ]

        runts = {}
        for name, props in runtdefs:
            runts[name] = TestRunt(name, **props)

        genr = runts.values

        async for node in self._doRuntLift(genr, full, valu, cmpr):
            yield node

    async def _doRuntLift(self, genr, full, valu=None, cmpr=None):

        if cmpr is not None:
            filt = self.model.prop(full).type.getCmprCtor(cmpr)(valu)
            if filt is None:
                raise s_exc.BadCmprValu(cmpr=cmpr)

        fullprop = self.model.prop(full)
        if fullprop.isform:

            if cmpr is None:
                for obj in genr():
                    yield obj.getStorNode(fullprop)
                return

            for obj in genr():
                sode = obj.getStorNode(fullprop)
                if filt(sode[1]['ndef'][1]):
                    yield sode
        else:
            for obj in genr():
                sode = obj.getStorNode(fullprop.form)
                propval = sode[1]['props'].get(fullprop.name)

                if propval is not None and (cmpr is None or filt(propval)):
                    yield sode

    async def _testRuntPropSetLulz(self, node, prop, valu):
        curv = node.get(prop.name)
        valu, _ = prop.type.norm(valu)
        if curv == valu:
            return False
        if not valu.endswith('.sys'):
            raise s_exc.BadTypeValu(mesg='test:runt:lulz must end with ".sys"',
                                    valu=valu, name=prop.full)
        node.props[prop.name] = valu
        # In this test helper, we do NOT persist the change to our in-memory
        # storage of row data, so a re-lift of the node would not reflect the
        # change that a user made here.
        return True

    async def _testRuntPropDelLulz(self, node, prop,):
        curv = node.props.pop(prop.name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        # In this test helper, we do NOT persist the change to our in-memory
        # storage of row data, so a re-lift of the node would not reflect the
        # change that a user made here.
        return True

    def getModelDefs(self):
        return (
            ('test', testmodel),
        )

    def getStormCmds(self):
        return (TestCmd,
                )

class TstEnv:

    def __init__(self):
        self.items = {}
        self.tofini = []

    def __getattr__(self, prop):
        item = self.items.get(prop)
        if item is None:
            raise AttributeError(prop)
        return item

    async def __aenter__(self):
        return self

    async def __aexit__(self, cls, exc, tb):
        await self.fini()

    def add(self, name, item, fini=False):
        self.items[name] = item
        if fini:
            self.tofini.append(item)

    async def fini(self):
        for base in self.tofini:
            await base.fini()

class TstOutPut(s_output.OutPutStr):

    def expect(self, substr, throw=True, whitespace=True):
        '''
        Check if a string is present in the messages captured by the OutPutStr object.

        Args:
            substr (str): String to check for the existence of.
            throw (bool): If True, a missing substr results in a Exception being thrown.

        Returns:
            bool: True if the string is present; False if the string is not present and throw is False.
        '''
        outs = str(self)

        if not whitespace:
            outs = ' '.join(outs.split())
            substr = ' '.join(outs.split())

        if outs.find(substr) == -1:
            if throw:
                mesg = 'TestOutPut.expect(%s) not in %s' % (substr, outs)
                raise s_exc.SynErr(mesg=mesg)
            return False
        return True

    def clear(self):
        self.mesgs.clear()

class CmdGenerator:

    def __init__(self, cmds):
        self.cmds = collections.deque(cmds)

    def addCmd(self, cmd):
        '''
        Add a command to the end of the list of commands returned by the CmdGenerator.

        Args:
            cmd (str): Command to add to the list of commands to return.
        '''
        self.cmds.append(cmd)

    def __call__(self, *args, **kwargs):
        return self._corocall(*args, **kwargs)

    async def _corocall(self, *args, **kwargs):

        if not self.cmds:
            raise Exception('No further actions.')

        retn = self.cmds.popleft()

        if isinstance(retn, (Exception, KeyboardInterrupt)):
            raise retn

        return retn

class StreamEvent(io.StringIO, threading.Event):
    '''
    A combination of a io.StringIO object and a threading.Event object.
    '''
    def __init__(self, *args, **kwargs):
        io.StringIO.__init__(self, *args, **kwargs)
        threading.Event.__init__(self)
        self.mesg = ''

    def setMesg(self, mesg):
        '''
        Clear the internal event and set a new message that is used to set the event.

        Args:
            mesg (str): The string to monitor for.

        Returns:
            None
        '''
        self.mesg = mesg
        self.clear()

    def write(self, s):
        io.StringIO.write(self, s)
        if self.mesg and self.mesg in s:
            self.set()

    def jsonlines(self) -> typing.List[dict]:
        '''Get the messages as jsonlines. May throw Json errors if the captured stream is not jsonlines.'''
        return jsonlines(self.getvalue())

class AsyncStreamEvent(io.StringIO, asyncio.Event):
    '''
    A combination of a io.StringIO object and an asyncio.Event object.
    '''
    def __init__(self, *args, **kwargs):
        io.StringIO.__init__(self, *args, **kwargs)
        asyncio.Event.__init__(self)
        self.mesg = ''

    def setMesg(self, mesg):
        '''
        Clear the internal event and set a new message that is used to set the event.

        Args:
            mesg (str): The string to monitor for.

        Returns:
            None
        '''
        self.mesg = mesg
        self.clear()

    def write(self, s):
        io.StringIO.write(self, s)
        if self.mesg and self.mesg in s:
            self.set()

    async def wait(self, timeout=None):
        if timeout is None:
            return await asyncio.Event.wait(self)
        return await s_coro.event_wait(self, timeout=timeout)

    def jsonlines(self) -> typing.List[dict]:
        '''Get the messages as jsonlines. May throw Json errors if the captured stream is not jsonlines.'''
        return jsonlines(self.getvalue())

class HttpReflector(s_httpapi.Handler):
    '''Test handler which reflects get/post data back to the caller'''

    def _decode_params(self):
        d = collections.defaultdict(list)
        if self.request.arguments:
            for k, items in self.request.arguments.items():
                for v in items:
                    d[k].append(v.decode())
        return d

    async def get(self):
        resp = {}
        params = self._decode_params()
        if params:
            resp['params'] = params

        resp['headers'] = dict(self.request.headers)
        resp['path'] = self.request.path

        sleep = resp.get('params', {}).get('sleep')
        if sleep:
            sleep = int(sleep[0])
            await asyncio.sleep(sleep)

        redirect = params.get('redirect')
        if redirect:
            self.add_header('Redirected', '1')
            self.redirect(redirect[0])
            return

        self.sendRestRetn(resp)

    async def post(self):
        resp = {}
        params = self._decode_params()
        if params:
            resp['params'] = params

        resp['headers'] = dict(self.request.headers)
        resp['path'] = self.request.path

        if self.request.body:
            resp['body'] = s_common.enbase64(self.request.body)
        self.sendRestRetn(resp)

    async def head(self):
        params = self._decode_params()
        redirect = params.get('redirect')
        self.add_header('Head', '1')

        if redirect:
            self.add_header('Redirected', '1')
            self.redirect(redirect[0])
            return

        self.set_status(200)
        return

s_task.vardefault('applynest', lambda: None)

async def _doubleapply(self, indx, item):
    '''
    Just like NexusRoot._apply, but calls the function twice.  Patched in when global variable SYNDEV_NEXUS_REPLAY
    is set.
    '''
    try:
        nestitem = s_task.varget('applynest')
        assert nestitem is None, f'Failure: have nested nexus actions, inner item is {item},  outer item was {nestitem}'
        s_task.varset('applynest', item)

        nexsiden, event, args, kwargs, _ = item

        nexus = self._nexskids[nexsiden]
        func, passitem = nexus._nexshands[event]

        if passitem:
            retn = await func(nexus, *args, nexsitem=(indx, item), **kwargs)
            await func(nexus, *args, nexsitem=(indx, item), **kwargs)
            return retn

        retn = await func(nexus, *args, **kwargs)
        await func(nexus, *args, **kwargs)
        return retn

    finally:
        s_task.varset('applynest', None)

test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
        "properties": {
            'key:string': {
                'description': 'Key String. I have a defval!',
                'type': 'string',
                'default': 'Default string!'
            },
            'key:integer': {
                'description': 'Key Integer',
                'type': 'integer',
            },
            'key:number': {
                'description': 'Key Number',
                'type': 'number',
            },
            'key:object': {
                'description': 'Key Object',
                'type': 'object',
            },
            'key:array': {
                'description': 'Key Array',
                'type': 'array',
            },
            'key:bool:defvalfalse': {
                'description': 'Key Bool, defval false.',
                'type': 'boolean',
                'default': False,
            },
            'key:bool:defvaltrue': {
                'description': 'Key Bool, defval true.',
                'type': 'boolean',
                'default': True,
            },

            'key:bool:nodefval': {
                'description': 'Key Bool, no default.',
                'type': 'boolean',
            },
            'key:foo': {
                'description': 'Foo String',
                'type': 'string',
            },
        },
        'type': 'object',
    }

class ReloadCell(s_cell.Cell):
    async def postAnit(self):
        self._reloaded = False
        self._reloadevt = None

    async def getCellInfo(self):
        info = await s_cell.Cell.getCellInfo(self)
        info['cell']['reloaded'] = self._reloaded
        return info

    async def addTestReload(self):
        async def func():
            self._reloaded = True
            if self._reloadevt:
                self._reloadevt.set()
            return True

        self.addReloadableSystem('testreload', func)

    async def addTestBadReload(self):
        async def func():
            return 1 / 0

        self.addReloadableSystem('badreload', func)

class SynTest(unittest.TestCase):
    '''
    Mark all async test methods as s_glob.synchelp decorated.

    Note:
        This precludes running a single unit test via path using the unittest module.
    '''
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

        for s in dir(self):
            attr = getattr(self, s, None)
            # If s is an instance method and starts with 'test_', synchelp wrap it
            if inspect.iscoroutinefunction(attr) and s.startswith('test_') and inspect.ismethod(attr):
                setattr(self, s, s_glob.synchelp(attr))

    def checkNode(self, node, expected):
        ex_ndef, ex_props = expected
        self.eq(node.ndef, ex_ndef)
        [self.eq(node.get(k), v, msg=f'Prop {k} does not match') for (k, v) in ex_props.items()]

        diff = {prop for prop in (set(node.props) - set(ex_props)) if not prop.startswith('.')}
        if diff:
            logger.warning('form(%s): untested properties: %s', node.form.name, diff)

    async def checkNodes(self, core, ndefs):
        for ndef in ndefs:
            node = await core.nodes('', opts={'ndefs': (ndef,)})
            self.len(1, node)

    def printed(self, msgs, text):
        # a helper for testing storm print message output
        for mesg in msgs:
            if mesg[0] == 'print':
                if mesg[1].get('mesg') == text:
                    return

        raise Exception('print output not found: %r' % (text,))

    def skip(self, mesg):
        raise unittest.SkipTest(mesg)

    @contextlib.contextmanager
    def getRegrDir(self, *path):

        regr = os.getenv('SYN_REGRESSION_REPO')
        if regr is None:  # pragma: no cover
            raise unittest.SkipTest('SYN_REGRESSION_REPO is not set')

        regr = s_common.genpath(regr)

        if not os.path.isdir(regr):  # pragma: no cover
            raise Exception('SYN_REGRESSION_REPO is not a dir')

        dirn = os.path.join(regr, *path)

        with self.getTestDir(copyfrom=dirn) as regrdir:
            yield regrdir

    @contextlib.asynccontextmanager
    async def getRegrCore(self, vers, conf=None, maxvers=None):
        with self.withNexusReplay():
            with self.getRegrDir('cortexes', vers) as dirn:
                if maxvers is not None:

                    orig = s_modelrev.ModelRev
                    class ModelRev(orig):
                        def __init__(self, core):
                            orig.__init__(self, core)
                            self.revs = [k for k in self.revs if k[0] <= maxvers]

                    with mock.patch.object(s_modelrev, 'ModelRev', ModelRev):
                        async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
                            yield core
                else:
                    async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
                        yield core

    @contextlib.asynccontextmanager
    async def getRegrAxon(self, vers, conf=None):
        with self.withNexusReplay():
            with self.getRegrDir('axons', vers) as dirn:
                async with await s_axon.Axon.anit(dirn, conf=conf) as axon:
                    yield axon

    def skipIfNoInternet(self):  # pragma: no cover
        '''
        Allow skipping a test if SYN_TEST_SKIP_INTERNET envar is set.

        Raises:
            unittest.SkipTest if SYN_TEST_SKIP_INTERNET envar is set to a integer greater than 1.
        '''
        if bool(int(os.getenv('SYN_TEST_SKIP_INTERNET', 0))):
            raise unittest.SkipTest('SYN_TEST_SKIP_INTERNET envar set')

    def skipLongTest(self):  # pragma: no cover
        '''
        Allow skipping a test if SYN_TEST_SKIP_LONG envar is set.

        Raises:
            unittest.SkipTest if SYN_TEST_SKIP_LONG envar is set to a integer greater than 1.
        '''
        if bool(int(os.getenv('SYN_TEST_SKIP_LONG', 0))):
            raise unittest.SkipTest('SYN_TEST_SKIP_LONG envar set')

    def skipIfNexusReplay(self):
        '''
        Allow skipping a test if SYNDEV_NEXUS_REPLAY envar is set.

        Raises:
            unittest.SkipTest if SYNDEV_NEXUS_REPLAY envar is set to true value.
        '''
        if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
            raise unittest.SkipTest('SYNDEV_NEXUS_REPLAY envar set')

    def skipIfNoPath(self, path, mesg=None):
        '''
        Allows skipping a test if the test/files path does not exist.

        Args:
            path (str): Path to check.
            mesg (str): Optional additional message.

        Raises:
            unittest.SkipTest if the path does not exist.
        '''
        path = self.getTestFilePath(path)
        if not os.path.exists(path):
            m = f'Path does not exist: {path}'
            if mesg:
                m = f'{m} mesg={mesg}'
            raise unittest.SkipTest(m)

    def getTestOutp(self):
        '''
        Get a Output instance with a expects() function.

        Returns:
            TstOutPut: A TstOutPut instance.
        '''
        return TstOutPut()

    def thisEnvMust(self, *envvars):
        '''
        Requires a host must have environment variables set to truthy values.

        Args:
            *envars: Environment variables to require being present.
        '''
        for envar in envvars:
            if not s_common.envbool(envar):
                self.skip(f'Envar {envar} is not set to a truthy value.')

    def thisEnvMustNot(self, *envvars):
        '''
        Requires a host must not have environment variables set to truthy values.

        Args:
            *envars: Environment variables to require being absent or set to falsey values.
        '''
        for envar in envvars:
            if s_common.envbool(envar):
                self.skip(f'Envar {envar} is set to a truthy value.')

    def thisHostMust(self, **props):  # pragma: no cover
        '''
        Requires a host having a specific property.

        Args:
            **props:

        Raises:
            unittest.SkipTest if the required property is missing.
        '''
        for k, v in props.items():
            if s_thishost.get(k) != v:
                raise unittest.SkipTest('skip thishost: %s!=%r' % (k, v))

    def thisHostMustNot(self, **props):  # pragma: no cover
        '''
        Requires a host to not have a specific property.

        Args:
            **props:

        Raises:
            unittest.SkipTest if the required property is missing.
        '''

        for k, v in props.items():
            if s_thishost.get(k) == v:
                raise unittest.SkipTest('skip thishost: %s==%r' % (k, v))

    @contextlib.asynccontextmanager
    async def getTestAxon(self, dirn=None, conf=None):
        '''
        Get a test Axon as an async context manager.

        Returns:
            s_axon.Axon: A Axon object.
        '''

        if conf is None:
            conf = {}
        conf = copy.deepcopy(conf)

        with self.withNexusReplay():
            if dirn is not None:
                async with await s_axon.Axon.anit(dirn, conf) as axon:
                    yield axon

                return

            with self.getTestDir() as dirn:
                async with await s_axon.Axon.anit(dirn, conf) as axon:
                    yield axon

    @contextlib.contextmanager
    def withTestCmdr(self, cmdg):

        getItemCmdr = s_cmdr.getItemCmdr

        async def getTestCmdr(*a, **k):
            cli = await getItemCmdr(*a, **k)
            cli.prompt = cmdg
            return cli

        with mock.patch('synapse.lib.cmdr.getItemCmdr', getTestCmdr):
            yield

    @contextlib.contextmanager
    def withCliPromptMockExtendOutp(self, outp):
        '''
        Context manager to mock our use of Prompt Toolkit's print_formatted_text function and
        extend the lines to an an output object.

        Args:
            outp (TstOutPut): The outp to extend.

        Notes:
            This extends the outp with the lines AFTER the context manager has exited.

        Returns:
            mock.MagicMock: Yields a mock.MagicMock object.
        '''
        with self.withCliPromptMock() as patch:
            yield patch
        self.extendOutpFromPatch(outp, patch)

    @contextlib.contextmanager
    def withCliPromptMock(self):
        '''
        Context manager to mock our use of Prompt Toolkit's print_formatted_text function.

        Returns:
            mock.MagicMock: Yields a mock.MagikMock object.
        '''
        with mock.patch('synapse.lib.cli.print_formatted_text',
                        mock.MagicMock(return_value=None)) as patch:  # type: mock.MagicMock
            yield patch

    @contextlib.asynccontextmanager
    async def withSetLoggingMock(self):
        '''
        Context manager to mock calls to the setlogging function to avoid unittests calling logging.basicconfig.

        Returns:
            mock.MagicMock: Yields a mock.MagicMock object.
        '''
        with mock.patch('synapse.common.setlogging',
                        PickleableMagicMock(return_value=dict())) as patch:  # type: mock.MagicMock
            yield patch

    def getMagicPromptLines(self, patch):
        '''
        Get the text lines from a MagicMock object from withCliPromptMock.

        Args:
            patch (mock.MagicMock): The MagicMock object from withCliPromptMock.

        Returns:
            list: A list of lines.
        '''
        self.true(patch.called, 'Assert prompt was called')
        lines = []
        for args in patch.call_args_list:
            arg = args[0][0]
            if isinstance(arg, str):
                lines.append(arg)
                continue
            if isinstance(arg, FormattedText):
                color, text = arg[0]
                lines.append(text)
                continue
            raise ValueError(f'Unknown arg: {type(arg)}/{arg}')
        return lines

    def getMagicPromptColors(self, patch):
        '''
        Get the colored lines from a MagicMock object from withCliPromptMock.

        Args:
            patch (mock.MagicMock): The MagicMock object from withCliPromptMock.

        Returns:
            list: A list of tuples, containing color and line data.
        '''
        self.true(patch.called, 'Assert prompt was called')
        lines = []
        for args in patch.call_args_list:
            arg = args[0][0]
            if isinstance(arg, str):
                continue
            if isinstance(arg, FormattedText):
                color, text = arg[0]
                lines.append((color, text))
                continue
            raise ValueError(f'Unknown arg: {type(arg)}/{arg}')
        return lines

    def extendOutpFromPatch(self, outp, patch):
        '''
        Extend an Outp with lines from a magicMock object from withCliPromptMock.

        Args:
            outp (TstOutPut): The outp to extend.
            patch (mock.MagicMock): The patch object.

        Returns:
            None: Returns none.
        '''
        lines = self.getMagicPromptLines(patch)
        [outp.printf(line) for line in lines]

    @contextlib.asynccontextmanager
    async def getTestReadWriteCores(self, conf=None, dirn=None):
        '''
        Get a read/write core pair.

        Notes:
            By default, this returns the same cortex.  It is expected that
            a test which needs two distinct Cortexes implements the bridge
            themselves.

        Returns:
            (s_cortex.Cortex, s_cortex.Cortex): A tuple of Cortex objects.
        '''
        async with self.getTestCore(conf=conf, dirn=dirn) as core:
            yield core, core

    @contextlib.contextmanager
    def withNexusReplay(self, replay=False):
        '''
        Patch so that the Nexus apply log is applied twice. Useful to verify idempotency.

        Args:
            replay (bool): Set the default value of resolving the existence of SYNDEV_NEXUS_REPLAY variable.
                           This can be used to force the apply patch without using the environment variable.

        Notes:
            This is applied if the environment variable SYNDEV_NEXUS_REPLAY is set
            to a non zero value or the replay argument is set to True.

        Returns:
            contextlib.ExitStack: An exitstack object.
        '''
        replay = s_common.envbool('SYNDEV_NEXUS_REPLAY', defval=str(replay))

        with contextlib.ExitStack() as stack:
            if replay:
                stack.enter_context(mock.patch.object(s_nexus.NexsRoot, '_apply', _doubleapply))
            yield stack

    @contextlib.asynccontextmanager
    async def getTestCore(self, conf=None, dirn=None):
        '''
        Get a simple test Cortex as an async context manager.

        Returns:
            s_cortex.Cortex: A Cortex object.
        '''
        conf = self.getCellConf(conf=conf)

        mods = list(conf.get('modules', ()))
        conf['modules'] = mods

        mods.insert(0, ('synapse.tests.utils.TestModule', {'key': 'valu'}))

        with self.withNexusReplay():

            with self.mayTestDir(dirn) as dirn:

                async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
                    yield core

    @contextlib.asynccontextmanager
    async def getTestCoreAndProxy(self, conf=None, dirn=None):
        '''
        Get a test Cortex and the Telepath Proxy to it.

        Returns:
            (s_cortex.Cortex, s_cortex.CoreApi): The Cortex and a Proxy representing a CoreApi object.
        '''
        async with self.getTestCore(conf=conf, dirn=dirn) as core:
            core.conf['storm:log'] = True
            core.stormlog = True
            async with core.getLocalProxy() as prox:
                yield core, prox

    @contextlib.asynccontextmanager
    async def getTestJsonStor(self, dirn=None, conf=None):

        conf = self.getCellConf(conf=conf)

        with self.withNexusReplay():
            if dirn is not None:
                async with await s_jsonstor.JsonStorCell.anit(dirn, conf) as jsonstor:
                    yield jsonstor

                return

            with self.getTestDir() as dirn:
                async with await s_jsonstor.JsonStorCell.anit(dirn, conf) as jsonstor:
                    yield jsonstor

    @contextlib.asynccontextmanager
    async def getTestCryo(self, dirn=None, conf=None):
        '''
        Get a simple test Cryocell as an async context manager.

        Returns:
            s_cryotank.CryoCell: Test cryocell.
        '''
        conf = self.getCellConf(conf=conf)

        with self.withNexusReplay():
            with self.mayTestDir(dirn) as dirn:
                async with await s_cryotank.CryoCell.anit(dirn, conf=conf) as cryo:
                    yield cryo

    @contextlib.asynccontextmanager
    async def getTestCryoAndProxy(self, dirn=None):
        '''
        Get a test Cryocell and the Telepath Proxy to it.

        Returns:
            (s_cryotank: CryoCell, s_cryotank.CryoApi): The CryoCell and a Proxy representing a CryoApi object.
        '''
        async with self.getTestCryo(dirn=dirn) as cryo:
            async with cryo.getLocalProxy() as prox:
                yield cryo, prox

    @contextlib.asynccontextmanager
    async def getTestDmon(self):
        self.skipIfNoPath(path='certdir', mesg='Missing files for test dmon!')
        with self.getTestDir(mirror='certdir') as certpath:
            certdir = s_certdir.CertDir(path=certpath)
            s_certdir.addCertPath(certpath)
            async with await s_daemon.Daemon.anit(certdir=certdir) as dmon:
                await dmon.listen('tcp://127.0.0.1:0/')
                with mock.patch('synapse.lib.certdir.defdir', certdir):
                    yield dmon
            s_certdir.delCertPath(certpath)

    @contextlib.asynccontextmanager
    async def getTestCell(self, ctor=s_cell.Cell, conf=None, dirn=None):
        '''
        Get a test Cell.
        '''
        conf = self.getCellConf(conf=conf)
        with self.withNexusReplay():
            with self.mayTestDir(dirn) as dirn:
                async with await ctor.anit(dirn, conf=conf) as cell:
                    yield cell

    @contextlib.asynccontextmanager
    async def getTestCoreProxSvc(self, ssvc, ssvc_conf=None, core_conf=None):
        '''
        Get a test Cortex, the Telepath Proxy to it, and a test service instance.

        Args:
            ssvc: Ctor to the Test Service.
            ssvc_conf: Service configuration.
            core_conf: Cortex configuration.

        Returns:
            (s_cortex.Cortex, s_cortex.CoreApi, testsvc): The Cortex, Proxy, and service instance.
        '''
        async with self.getTestCoreAndProxy(core_conf) as (core, prox):
            async with self.getTestCell(ssvc, ssvc_conf) as testsvc:
                await self.addSvcToCore(testsvc, core)

                yield core, prox, testsvc

    @contextlib.contextmanager
    def mayTestDir(self, dirn: str | None) -> contextlib.AbstractContextManager[str, None, None]:
        '''
        Convenience method to make a temporary directory or use an existing one.

        Args:
            dirn: Directory to use, or None.

        Returns:
            The directory to use.
        '''
        if dirn is not None:
            yield dirn
            return

        with self.getTestDir() as dirn:
            yield dirn

    @contextlib.asynccontextmanager
    async def getTestAha(self, conf=None, dirn=None, ctor=None):

        if conf is None:
            conf = {}

        if ctor is None:
            ctor = s_aha.AhaCell.anit

        conf = s_msgpack.deepcopy(conf)

        hasdmonlisn = 'dmon:listen' in conf
        hasprovlisn = 'provision:listen' in conf

        network = conf.setdefault('aha:network', 'synapse')
        hostname = conf.setdefault('dns:name', '00.aha.loop.vertex.link')

        if hostname:
            conf.setdefault('provision:listen', f'ssl://0.0.0.0:0?hostname={hostname}')
            conf.setdefault('dmon:listen', f'ssl://0.0.0.0:0?hostname={hostname}&ca={network}')

        conf.setdefault('health:sysctl:checks', False)

        with self.withNexusReplay():

            with self.mayTestDir(dirn) as dirn:

                if conf.get('aha:network') == 'synapse':
                    dstpath = os.path.join(dirn, 'certs')
                    if not os.path.isdir(dstpath):
                        srcpath = self.getTestFilePath('aha/certs')
                        shutil.copytree(srcpath, os.path.join(dirn, 'certs'))

                async with await ctor(dirn, conf=conf) as aha:

                    mods = {}
                    if not hasdmonlisn and hostname:
                        mods['dmon:listen'] = f'ssl://0.0.0.0:{aha.sockaddr[1]}?hostname={hostname}&ca={network}'

                    if not hasprovlisn and hostname:
                        mods['provision:listen'] = f'ssl://0.0.0.0:{aha.provaddr[1]}?hostname={hostname}'

                    if mods:
                        aha.modCellConf(mods)

                    yield aha

    def getCellConf(self, conf=None):
        if conf is None:
            conf = {}
        conf = s_msgpack.deepcopy(conf)
        conf.setdefault('health:sysctl:checks', False)
        return conf

    @contextlib.asynccontextmanager
    async def addSvcToAha(self, aha, svcname, ctor,
                          conf=None, dirn=None, provinfo=None):
        '''
        Creates a service and provisions it in an Aha network via the provisioning API.

        This assumes the Aha cell has a provision:listen and aha:urls set.

        Args:
            aha (s_aha.AhaCell): Aha cell.
            svcname (str): Service name.
            ctor: Service class to add.
            conf (dict): Optional service conf.
            dirn (str): Optional directory.
            provinfo (dict): Optional provisioning info.

        Notes:
            The config data for the cell is pushed into dirn/cell.yaml.
            The cells are created with the ``ctor.anit()`` function.
        '''
        ahanetw = aha.conf.req('aha:network')
        svcfull = f'{svcname}.{ahanetw}'
        onetime = await aha.addAhaSvcProv(svcname, provinfo=provinfo)

        conf = self.getCellConf(conf=conf)
        conf['aha:provision'] = onetime

        waiter = aha.waiter(1, f'aha:svcadd:{svcfull}')
        with self.mayTestDir(dirn) as dirn:
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            async with await ctor.anit(dirn) as svc:
                self.true(await waiter.wait(timeout=12))
                yield svc

    async def addSvcToCore(self, svc, core, svcname='svc'):
        '''
        Add a service to a Cortex using telepath over tcp.
        '''
        svc.dmon.share('svc', svc)
        root = await svc.auth.getUserByName('root')
        await root.setPasswd('root')
        info = await svc.dmon.listen('tcp://127.0.0.1:0/')
        svc.dmon.test_addr = info
        host, port = info
        surl = f'tcp://root:root@127.0.0.1:{port}/svc'
        await self.runCoreNodes(core, f'service.add {svcname} {surl}')
        await self.runCoreNodes(core, f'$lib.service.wait({svcname})')

    def getTestUrl(self, dmon, name, **opts):

        host, port = dmon.addr
        netloc = '%s:%s' % (host, port)

        user = opts.get('user')
        passwd = opts.get('passwd')

        if user is not None and passwd is not None:
            netloc = '%s:%s@%s' % (user, passwd, netloc)

        return 'tcp://%s/%s' % (netloc, name)

    def getTestProxy(self, dmon, name, **kwargs):
        host, port = dmon.addr
        kwargs.update({'host': host, 'port': port})
        return s_telepath.openurl(f'tcp:///{name}', **kwargs)

    @contextlib.contextmanager
    def getTestDir(self, mirror=None, copyfrom=None, chdir=False, startdir=None) -> contextlib.AbstractContextManager[str, None, None]:
        '''
        Get a temporary directory for test purposes.
        This destroys the directory afterwards.

        Args:
            mirror (str): A Synapse test directory to mirror into the test directory.
            copyfrom (str): An arbitrary directory to copy into the test directory.
            chdir (boolean): If true, chdir the current process to that directory. This is undone when the context
                             manager exits.
            startdir (str): The directory under which to place the temporary directory

        Notes:
            The mirror argument is normally used to mirror test directory
            under ``synapse/tests/files``.  This is accomplished by passing in
            the name of the directory (such as ``testcore``) as the mirror
            argument.

            If the ``mirror`` argument is an absolute directory, that directory
            will be copied to the test directory.

        Returns:
            str: The path to a temporary directory.
        '''
        curd = os.getcwd()
        tempdir = tempfile.mkdtemp(dir=startdir)

        try:

            dstpath = tempdir

            if mirror is not None:
                srcpath = self.getTestFilePath(mirror)
                dstpath = os.path.join(dstpath, 'mirror')
                shutil.copytree(srcpath, dstpath)

            elif copyfrom is not None:
                dstpath = os.path.join(dstpath, 'mirror')
                shutil.copytree(copyfrom, dstpath)

            if chdir:
                os.chdir(dstpath)

            yield dstpath

        finally:

            if chdir:
                os.chdir(curd)

            shutil.rmtree(tempdir, ignore_errors=True)

    def getTestFilePath(self, *names):
        import synapse.tests.__init__
        path = os.path.dirname(synapse.tests.__init__.__file__)
        return os.path.join(path, 'files', *names)

    @contextlib.contextmanager
    def getLoggerStream(self, logname, mesg=''):
        '''
        Get a logger and attach a io.StringIO object to the logger to capture log messages.

        Args:
            logname (str): Name of the logger to get.
            mesg (str): A string which, if provided, sets the StreamEvent event if a message
            containing the string is written to the log.

        Examples:
            Do an action and get the stream of log messages to check against::

                with self.getLoggerStream('synapse.foo.bar') as stream:
                    # Do something that triggers a log message
                    doSomething()

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            Do an action and wait for a specific log message to be written::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomething()
                    stream.wait(timeout=10)  # Wait for the mesg to be written to the stream

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            You can also reset the message and wait for another message to occur::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomething()
                    stream.wait(timeout=10)
                    stream.setMesg('yo dawg')  # This will now wait for the 'yo dawg' string to be written.
                    stream.wait(timeout=10)

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

        Notes:
            This **only** captures logs for the current process.

        Yields:
            StreamEvent: A StreamEvent object
        '''
        stream = StreamEvent()
        stream.setMesg(mesg)
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        slogger.addHandler(handler)
        level = slogger.level
        slogger.setLevel('DEBUG')
        try:
            yield stream
        except Exception:  # pragma: no cover
            raise
        finally:
            slogger.removeHandler(handler)
            slogger.setLevel(level)

    @contextlib.contextmanager
    def getAsyncLoggerStream(self, logname, mesg='') -> contextlib.AbstractContextManager[StreamEvent, None, None]:
        '''
        Async version of getLoggerStream.

        Args:
            logname (str): Name of the logger to get.
            mesg (str): A string which, if provided, sets the StreamEvent event if a message containing the string is written to the log.

        Notes:
            The event object mixed in for the AsyncStreamEvent is a asyncio.Event object.
            This requires the user to await the Event specific calls as neccesary.

        Examples:
            Do an action and wait for a specific log message to be written::

                with self.getAsyncLoggerStream('synapse.foo.bar',
                                               'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    await doSomething()
                    # Wait for the mesg to be written to the stream
                    await stream.wait(timeout=10)

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

        Returns:
            AsyncStreamEvent: An AsyncStreamEvent object.
        '''
        stream = AsyncStreamEvent()
        stream.setMesg(mesg)
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        slogger.addHandler(handler)
        level = slogger.level
        slogger.setLevel('DEBUG')
        try:
            yield stream
        except Exception:  # pragma: no cover
            raise
        finally:
            slogger.removeHandler(handler)
            slogger.setLevel(level)

    @contextlib.contextmanager
    def getStructuredAsyncLoggerStream(self, logname, mesg='') -> contextlib.AbstractContextManager[AsyncStreamEvent, None, None]:
        '''
        Async version of getLoggerStream which uses structured logging.

        Args:
            logname (str): Name of the logger to get.
            mesg (str): A string which, if provided, sets the StreamEvent event if a message containing the string is written to the log.

        Notes:
            The event object mixed in for the AsyncStreamEvent is a asyncio.Event object.
            This requires the user to await the Event specific calls as needed.
            The messages written to the stream will be JSON lines.

        Examples:
            Do an action and wait for a specific log message to be written::

                with self.getStructuredAsyncLoggerStream('synapse.foo.bar',
                                                         '"some JSON string"') as stream:
                    # Do something that triggers a log message
                    await doSomething()
                    # Wait for the mesg to be written to the stream
                    await stream.wait(timeout=10)

                msgs = stream.jsonlines()
                # Do something with messages

        Returns:
            AsyncStreamEvent: An AsyncStreamEvent object.
        '''
        stream = AsyncStreamEvent()
        stream.setMesg(mesg)
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        formatter = s_structlog.JsonFormatter()
        handler.setFormatter(formatter)
        slogger.addHandler(handler)
        level = slogger.level
        slogger.setLevel('DEBUG')
        try:
            yield stream
        except Exception:  # pragma: no cover
            raise
        finally:
            slogger.removeHandler(handler)
            slogger.setLevel(level)

    @contextlib.asynccontextmanager
    async def getHttpSess(self, auth=None, port=None):
        '''
        Get an aiohttp ClientSession with a CookieJar.

        Args:
            auth (str, str): A tuple of username and password information for http auth.
            port (int): Port number to connect to.

        Notes:
            If auth and port are provided, the session will login to a Synapse cell
            hosted at localhost:port.

        Returns:
            aiohttp.ClientSession: An aiohttp.ClientSession object.
        '''

        jar = aiohttp.CookieJar(unsafe=True)
        conn = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(cookie_jar=jar, connector=conn) as sess:

            if auth is not None:

                if port is None:  # pragma: no cover
                    raise Exception('getHttpSess requires port for auth')

                user, passwd = auth
                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': user, 'passwd': passwd}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(user, retn['result']['name'])

            yield sess

    @contextlib.contextmanager
    def setTstEnvars(self, **props):
        '''
        Set Environment variables for the purposes of running a specific test.

        Args:
            **props: A kwarg list of envars to set. The values set are run
            through str() to ensure we're setting strings.

        Examples:
            Run a test while a envar is set::

                with self.setEnvars(magic='haha') as nop:
                    ret = dostuff()
                    self.true(ret)

        Notes:
            This helper explicitly sets and unsets values in os.environ, as
            os.putenv does not automatically updates the os.environ object.

        Yields:
            None. This context manager yields None. Upon exiting, envars are
            either removed from os.environ or reset to their previous values.
        '''
        old_data = {}
        pop_data = set()
        for key, valu in props.items():
            v = str(valu)
            oldv = os.environ.get(key, None)
            if oldv:
                if oldv == v:
                    continue
                else:
                    old_data[key] = oldv
                    os.environ[key] = v
            else:
                pop_data.add(key)
                os.environ[key] = v

        # This context manager is a nop
        try:
            yield None
        except Exception:  # pragma: no cover
            raise
        # Clean up any new envars we set and any old envars we need to reset.
        finally:
            for key in pop_data:
                del os.environ[key]
            for key, valu in old_data.items():
                os.environ[key] = valu

    async def execToolMain(self, func, argv):
        outp = self.getTestOutp()

        if inspect.iscoroutinefunction(func):
            retn = await func(argv, outp=outp)
        else:
            def execmain():
                return func(argv, outp=outp)
            retn = await s_coro.executor(execmain)
        return retn, outp

    @contextlib.contextmanager
    def redirectStdin(self, new_stdin):
        '''
        Temporary replace stdin.

        Args:
            new_stdin(file-like object):  file-like object.

        Examples:
            Patch stdin with a string buffer::

                inp = io.StringIO('stdin stuff\\nanother line\\n')
                with self.redirectStdin(inp):
                    main()

            Here's a way to use this for code that's expecting the stdin buffer to have bytes::

                inp = Mock()
                inp.buffer = io.BytesIO(b'input data')
                with self.redirectStdin(inp):
                    main()

        Returns:
            None
        '''
        old_stdin = sys.stdin
        sys.stdin = new_stdin
        yield
        sys.stdin = old_stdin

    def genraises(self, exc, gfunc, *args, **kwargs):
        '''
        Helper to validate that a generator function will throw an exception.

        Args:
            exc: Exception class to catch
            gfunc: Generator function to call.
            *args: Args passed to the generator function.
            **kwargs: Kwargs passed to the generator function.

        Notes:
            Wrap a generator function in a list() call and execute that in a
            bound local using ``self.raises(exc, boundlocal)``. The ``list()``
            will consume the generator until complete or an exception occurs.
        '''
        def testfunc():
            return list(gfunc(*args, **kwargs))

        self.raises(exc, testfunc)

    async def agenraises(self, exc, gfunc):
        '''
        Helper to validate that an async generator will throw an exception.

        Args:
            exc: Exception class to catch
            gfunc: async Generator
        '''
        await self.asyncraises(exc, alist(gfunc))

    @contextlib.contextmanager
    def setSynDir(self, dirn):
        '''
        Sets s_common.syndir to a specific directory and then unsets it afterwards.

        Args:
            dirn (str): Directory to set syndir to.

        Notes:
            This is to be used as a context manager.
        '''
        olddir = s_common.syndir
        try:
            s_common.syndir = dirn
            yield None
        finally:
            s_common.syndir = olddir

    @contextlib.contextmanager
    def getTestSynDir(self):
        '''
        Combines getTestDir() and setSynDir() into one.
        '''
        with self.getTestDir() as dirn:
            with self.setSynDir(dirn):
                yield dirn

    @contextlib.contextmanager
    def getTestCertDir(self, dirn):
        '''
        Patch the synapse.lib.certdir.certdir singleton and supporting functions
        with a CertDir instance backed by the provided directory.

        Args:
            dirn (str): The directory used to back the new CertDir singleton.

        Returns:
            s_certdir.CertDir: The patched CertDir object that is the current singleton.
        '''
        with mock.patch('synapse.lib.certdir.defdir', dirn):
            # Use the default behavior of creating the certdir from defdir
            # which was just patched
            certdir = s_certdir.CertDir()
            with mock.patch('synapse.lib.certdir.certdir', certdir):
                yield certdir

    def eq(self, x, y, msg=None):
        '''
        Assert X is equal to Y
        '''
        self.assertEqual(norm(x), norm(y), msg=msg)

    def eqOrNan(self, x, y, msg=None):
        '''
        Assert X is equal to Y or they are both NaN (needed since NaN != NaN)
        '''
        if math.isnan(x):
            self.assertTrue(math.isnan(y), msg=msg)
            return

        self.eq(x, y, msg=msg)

    def eqish(self, x, y, places=6, msg=None):
        '''
        Assert X is equal to Y within places decimal places
        '''
        self.assertAlmostEqual(x, y, places, msg=msg)

    def ne(self, x, y):
        '''
        Assert X is not equal to Y
        '''
        self.assertNotEqual(norm(x), norm(y))

    def true(self, x, msg=None):
        '''
        Assert X is True
        '''
        self.assertTrue(x, msg=msg)

    def false(self, x, msg=None):
        '''
        Assert X is False
        '''
        self.assertFalse(x, msg=msg)

    def nn(self, x, msg=None):
        '''
        Assert X is not None
        '''
        self.assertIsNotNone(x, msg=msg)
        return x

    def none(self, x, msg=None):
        '''
        Assert X is None
        '''
        self.assertIsNone(x, msg=msg)

    def noprop(self, info, prop):
        '''
        Assert a property is not present in a dictionary.
        '''
        valu = info.get(prop, s_common.novalu)
        self.eq(valu, s_common.novalu)

    def raises(self, *args, **kwargs):
        '''
        Assert a function raises an exception.
        '''
        return self.assertRaises(*args, **kwargs)

    async def asyncraises(self, exc, coro):
        with self.assertRaises(exc):
            await coro

    def sorteq(self, x, y, msg=None):
        '''
        Assert two sorted sequences are the same.
        '''
        return self.eq(sorted(x), sorted(y), msg=msg)

    def isinstance(self, obj, cls, msg=None):
        '''
        Assert a object is the instance of a given class or tuple of classes.
        '''
        self.assertIsInstance(obj, cls, msg=msg)

    def isin(self, member, container, msg=None):
        '''
        Assert a member is inside of a container.
        '''
        self.assertIn(member, container, msg=msg)

    def notin(self, member, container, msg=None):
        '''
        Assert a member is not inside of a container.
        '''
        self.assertNotIn(member, container, msg=msg)

    def gt(self, x, y, msg=None):
        '''
        Assert that X is greater than Y
        '''
        self.assertGreater(x, y, msg=msg)

    def ge(self, x, y, msg=None):
        '''
        Assert that X is greater than or equal to Y
        '''
        self.assertGreaterEqual(x, y, msg=msg)

    def lt(self, x, y, msg=None):
        '''
        Assert that X is less than Y
        '''
        self.assertLess(x, y, msg=msg)

    def le(self, x, y, msg=None):
        '''
        Assert that X is less than or equal to Y
        '''
        self.assertLessEqual(x, y, msg=msg)

    def len(self, x, obj, msg=None):
        '''
        Assert that the length of an object is equal to X
        '''
        gtyps = (
            s_coro.GenrHelp,
            s_telepath.Genr,
            s_telepath.GenrIter,
            types.GeneratorType)

        if isinstance(obj, gtyps):
            obj = list(obj)

        self.eq(x, len(obj), msg=msg)

    async def agenlen(self, x, obj, msg=None):
        '''
        Assert that the async generator produces x items
        '''
        count = 0
        async for _ in obj:
            count += 1
        self.eq(x, count, msg=msg)

    def stormIsInPrint(self, mesg, mesgs, deguid=False, whitespace=True):
        '''
        Check if a string is present in all of the print messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        if deguid:
            mesg = deguidify(mesg)

        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'print'])
        if not whitespace:
            mesg = ' '.join(mesg.split())
            print_str = ' '.join(print_str.split())

        if deguid:
            print_str = deguidify(print_str)

        self.isin(mesg, print_str)

    def stormNotInPrint(self, mesg, mesgs):
        '''
        Assert a string is not present in all of the print messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'print'])
        self.notin(mesg, print_str)

    def stormIsInWarn(self, mesg, mesgs):
        '''
        Check if a string is present in all of the warn messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'warn'])
        self.isin(mesg, print_str)

    def stormNotInWarn(self, mesg, mesgs):
        '''
        Assert a string is not present in all of the warn messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'warn'])
        self.notin(mesg, print_str)

    def stormIsInErr(self, mesg, mesgs):
        '''
        Check if a string is present in all of the error messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1][1].get('mesg', '') for m in mesgs if m[0] == 'err'])
        self.isin(mesg, print_str)

    def stormHasNoErr(self, mesgs):
        '''
        Raise an AssertionError if there is a message of type "err" in the list.

        Args:
            mesgs (list): A list of storm messages.
        '''
        for mesg in mesgs:
            if mesg[0] == 'err':
                self.fail(f'storm err mesg found: {mesg}')

    def stormHasNoWarnErr(self, mesgs):
        '''
        Raise an AssertionError if there is a message of type "err" or "warn" in the list.

        Args:
            mesgs (list): A list of storm messages.
        '''
        for mesg in mesgs:
            if mesg[0] in ('err', 'warn'):
                self.fail(f'storm err/warn mesg found: {mesg}')

    def istufo(self, obj):
        '''
        Check to see if an object is a tufo.

        Args:
            obj (object): Object being inspected.

        Notes:
            This does not make any assumptions about the contents of the dictionary.
            This validates the object to be a tuple of length two, containing a str
            or None as the first value, and a dict as the second value.

        Returns:
            None
        '''
        self.isinstance(obj, tuple)
        self.len(2, obj)
        self.isinstance(obj[0], (type(None), str))
        self.isinstance(obj[1], dict)

    @contextlib.contextmanager
    def getTestConfDir(self, name, conf=None):
        with self.getTestDir() as dirn:
            cdir = os.path.join(dirn, name)
            s_common.makedirs(cdir)
            if conf:
                s_common.yamlsave(conf, cdir, 'cell.yaml')
            yield dirn

    async def addCreatorDeleterRoles(self, core):
        '''
        Add two roles to a Cortex *proxy*, the `creator` and `deleter` roles.
        Creator allows for node:add, prop:set and tag:add actions.
        Deleter allows for node:del, prop:del and tag:del actions.

        Args:
            core: Auth enabled cortex.
        '''
        creator = await core.auth.addRole('creator')

        await creator.setRules((
            (True, ('node', 'add')),
            (True, ('node', 'prop', 'set')),
            (True, ('node', 'tag', 'add')),
            (True, ('feed:data',)),
        ))

        deleter = await core.auth.addRole('deleter')
        await deleter.setRules((
            (True, ('node', 'del')),
            (True, ('node', 'prop', 'del')),
            (True, ('node', 'tag', 'del')),
        ))

        iadd = await core.auth.addUser('icanadd')
        await iadd.grant(creator.iden)
        await iadd.setPasswd('secret')

        idel = await core.auth.addUser('icandel')
        await idel.grant(deleter.iden)
        await idel.setPasswd('secret')

    @contextlib.asynccontextmanager
    async def getTestHive(self):
        with self.getTestDir() as dirn:
            async with self.getTestHiveFromDirn(dirn) as hive:
                yield hive

    @contextlib.asynccontextmanager
    async def getTestHiveFromDirn(self, dirn):

        import synapse.lib.const as s_const
        map_size = s_const.gibibyte

        async with await s_lmdbslab.Slab.anit(dirn, map_size=map_size) as slab:

            async with await s_hive.SlabHive.anit(slab) as hive:
                yield hive

    async def runCoreNodes(self, core, query, opts=None):
        '''
        Run a storm query through a Cortex as a SchedCoro and return the results.
        '''
        async def coro():
            return await core.nodes(query, opts)
        return await core.schedCoro(coro())

ONLOAD_TIMEOUT = int(os.getenv('SYNDEV_PKG_LOAD_TIMEOUT', 30))  # seconds

class StormPkgTest(SynTest):

    vcr = None
    assetdir = None
    pkgprotos = ()

    @contextlib.asynccontextmanager
    async def getTestCore(self, conf=None, dirn=None, prepkghook=None):

        async with SynTest.getTestCore(self, conf=None, dirn=None) as core:

            if prepkghook is not None:
                await prepkghook(core)

            for pkgproto in self.pkgprotos:

                pkgdef = s_genpkg.loadPkgProto(pkgproto, no_docs=True, readonly=True)

                waiter = None
                if pkgdef.get('onload') is not None:
                    waiter = core.waiter(1, 'core:pkg:onload:complete')

                await core.addStormPkg(pkgdef)

                if waiter is not None:
                    self.nn(await waiter.wait(timeout=ONLOAD_TIMEOUT),
                            f'Package onload failed to run for {pkgdef.get("name")}')

            if self.assetdir is not None:

                if self.vcr is None:
                    self.vcr = vcr.VCR()

                assetdir = s_common.gendir(self.assetdir)
                vcrname = f'{self.__class__.__name__}.{self._testMethodName}.yaml'
                cass = self.vcr.use_cassette(s_common.genpath(assetdir, vcrname))
                await core.enter_context(cass)

            await self.initTestCore(core)
            yield core

    async def initTestCore(self, core):
        '''
        This is executed after the package has been loaded and a VCR context has been entered.
        '''
        pass
