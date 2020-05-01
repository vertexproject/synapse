import asyncio
import logging
import contextlib
import collections
import contextvars

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.cache as s_cache
import synapse.lib.config as s_config
import synapse.lib.grammar as s_grammar
import synapse.lib.provenance as s_provenance

logger = logging.getLogger(__name__)

Conditions = set((
    'tag:add',
    'tag:del',
    'node:add',
    'node:del',
    'prop:set',
))

RecursionDepth = contextvars.ContextVar('RecursionDepth', default=0)

# TODO: standardize locations for form/prop/tags regex

tagrestr = r'((\w+|\*|\*\*)\.)*(\w+|\*|\*\*)'  # tag with optional single or double * as segment
_tagre, _formre, _propre = (f'^{re}$' for re in (tagrestr, s_grammar.formrestr, s_grammar.proporunivrestr))

_tagtrigvalid = {'properties': {'form': {'type': 'string', 'pattern': _formre},
                                'tag': {'type': 'string', 'pattern': _tagre}},
                 'required': ['tag']}
TrigSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'cond': {'enum': ['node:add', 'node:del', 'tag:add', 'tag:del', 'prop:set']},
        'storm': {'type': 'string'},
        'enabled': {'type': 'boolean'},
    },
    'additionalProperties': True,
    'required': ['iden', 'user', 'storm', 'enabled'],
    'allOf': [
        {
            'if': {'properties': {'cond': {'const': 'node:add'}}},
            'then': {'properties': {'form': {'type': 'string'}}, 'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'node:del'}}},
            'then': {'properties': {'form': {'type': 'string'}}, 'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:add'}}},
            'then': _tagtrigvalid,
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:del'}}},
            'then': _tagtrigvalid,
        },
        {
            'if': {'properties': {'cond': {'const': 'prop:set'}}},
            'then': {'properties': {'prop': {'type': 'string', 'pattern': _propre}}, 'required': ['prop']},
        },
    ],
}

def reqValidTdef(conf):
    s_config.Config(TrigSchema, conf=conf).reqConfValid()

class Triggers:
    '''
    Manages "triggers", conditions where changes in data result in new storm queries being executed.

    Note:
        These methods should not be called directly under normal circumstances.  Use the owning "View" object to ensure
        that mirrors/clusters members get the same changes.
    '''
    def __init__(self, view):

        self.view = view
        self.triggers = {}

        self.tagadd = collections.defaultdict(list)    # (form, tag): [ Triger ... ]
        self.tagset = collections.defaultdict(list)    # (form, tag): [ Triger ... ]
        self.tagdel = collections.defaultdict(list)    # (form, tag): [ Triger ... ]

        self.tagaddglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs
        self.tagsetglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs
        self.tagdelglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs

        self.nodeadd = collections.defaultdict(list)   # form: [ Trigger ... ]
        self.nodedel = collections.defaultdict(list)   # form: [ Trigger ... ]
        self.propset = collections.defaultdict(list)   # prop: [ Trigger ... ]

    @contextlib.contextmanager
    def _recursion_check(self):

        depth = RecursionDepth.get()
        if depth > 64:
            raise s_exc.RecursionLimitHit(mesg='Hit trigger limit')
        token = RecursionDepth.set(depth + 1)

        try:
            yield

        finally:
            RecursionDepth.reset(token)

    async def runNodeAdd(self, node):
        with self._recursion_check():
            [await trig.execute(node) for trig in self.nodeadd.get(node.form.name, ())]

    async def runNodeDel(self, node):
        with self._recursion_check():
            [await trig.execute(node) for trig in self.nodedel.get(node.form.name, ())]

    async def runPropSet(self, node, prop, oldv):
        vars = {'propname': prop.name, 'propfull': prop.full}
        with self._recursion_check():
            [await trig.execute(node, vars=vars) for trig in self.propset.get(prop.full, ())]
            if prop.univ is not None:
                [await trig.execute(node, vars=vars) for trig in self.propset.get(prop.univ.full, ())]

    async def runTagAdd(self, node, tag):

        vars = {'tag': tag}
        with self._recursion_check():

            for trig in self.tagadd.get((node.form.name, tag), ()):
                await trig.execute(node, vars=vars)

            for trig in self.tagadd.get((None, tag), ()):
                await trig.execute(node, vars=vars)

            # check for form specific globs
            globs = self.tagaddglobs.get(node.form.name)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars)

            # check for form agnostic globs
            globs = self.tagaddglobs.get(None)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars)

    async def runTagDel(self, node, tag):

        vars = {'tag': tag}
        with self._recursion_check():

            for trig in self.tagdel.get((node.form.name, tag), ()):
                await trig.execute(node, vars=vars)

            for trig in self.tagdel.get((None, tag), ()):
                await trig.execute(node, vars=vars)

            # check for form specific globs
            globs = self.tagdelglobs.get(node.form.name)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars)

            # check for form agnostic globs
            globs = self.tagdelglobs.get(None)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars)

    def load(self, tdef):

        trig = Trigger(self.view, tdef)

        # Make sure the query parses
        storm = trig.tdef['storm']
        self.view.core.getStormQuery(storm)

        cond = trig.tdef.get('cond')
        tag = trig.tdef.get('tag')
        form = trig.tdef.get('form')
        prop = trig.tdef.get('prop')

        if cond not in Conditions:
            raise s_exc.NoSuchCond(name=cond)

        if cond in ('node:add', 'node:del') and form is None:
            raise s_exc.BadOptValu(mesg='form must be present for node:add or node:del')
        if cond in ('node:add', 'node:del') and tag is not None:
            raise s_exc.BadOptValu(mesg='tag must not be present for node:add or node:del')
        if cond in ('tag:add', 'tag:del'):
            if tag is None:
                raise s_exc.BadOptValu(mesg='missing tag')
            s_chop.validateTagMatch(tag)
        if prop is not None and cond != 'prop:set':
            raise s_exc.BadOptValu(mesg='prop parameter invalid')

        if cond == 'node:add':
            self.nodeadd[form].append(trig)

        elif cond == 'node:del':
            self.nodedel[form].append(trig)

        elif cond == 'prop:set':
            if prop is None:
                raise s_exc.BadOptValu(mesg='missing prop parameter')
            if form is not None or tag is not None:
                raise s_exc.BadOptValu(mesg='form and tag must not be present for prop:set')
            self.propset[prop].append(trig)

        elif cond == 'tag:add':

            if '*' not in tag:
                self.tagadd[(form, tag)].append(trig)
            else:
                # we have a glob add
                self.tagaddglobs[form].add(tag, trig)

        elif cond == 'tag:del':

            if '*' not in tag:
                self.tagdel[(form, tag)].append(trig)
            else:
                self.tagdelglobs[form].add(tag, trig)

        self.triggers[trig.iden] = trig
        return trig

    def list(self):
        return list(self.triggers.items())

    def pop(self, iden):

        trig = self.triggers.pop(iden, None)
        if trig is None:
            return None

        cond = trig.tdef.get('cond')

        if cond == 'node:add':
            form = trig.tdef['form']
            self.nodeadd[form].remove(trig)
            return trig

        if cond == 'node:del':
            form = trig.tdef['form']
            self.nodedel[form].remove(trig)
            return trig

        if cond == 'prop:set':
            prop = trig.tdef.get('prop')
            self.propset[prop].remove(trig)
            return trig

        if cond == 'tag:add':

            tag = trig.tdef.get('tag')
            form = trig.tdef.get('form')

            if '*' not in tag:
                self.tagadd[(form, tag)].remove(trig)
                return trig

            globs = self.tagaddglobs.get(form)
            globs.rem(tag, trig)
            return trig

        if cond == 'tag:del':

            tag = trig.tdef['tag']
            form = trig.tdef.get('form')

            if '*' not in tag:
                self.tagdel[(form, tag)].remove(trig)
                return trig

            globs = self.tagdelglobs.get(form)
            globs.rem(tag, trig)
            return trig

        raise AssertionError('trigger has invalid condition')

    def get(self, iden):
        return self.triggers.get(iden)

class Trigger:

    def __init__(self, view, tdef):
        self.view = view
        self.tdef = tdef
        self.iden = tdef.get('iden')

    async def set(self, name, valu):
        '''
        Set one of the dynamic elements of the trigger definition.
        '''
        assert name in ('enabled', 'storm', 'doc', 'name')

        if valu == self.tdef.get(name):
            return

        if name == 'storm':
            self.view.core.getStormQuery(valu)

        self.tdef[name] = valu
        await self.view.trigdict.set(self.iden, self.tdef)

    def get(self, name):
        return self.tdef.get(name)

    async def execute(self, node, vars=None):
        '''
        Actually execute the query
        '''
        opts = {}

        if not self.tdef.get('enabled'):
            return

        if vars is not None:
            opts['vars'] = vars

        useriden = self.tdef.get('user')

        user = node.snap.core.auth.user(useriden)
        if user is None:
            logger.warning('Unknown user %s in stored trigger', useriden)
            return

        tag = self.tdef.get('tag')
        cond = self.tdef.get('cond')
        form = self.tdef.get('form')
        prop = self.tdef.get('prop')
        storm = self.tdef.get('storm')

        with s_provenance.claim('trig', cond=cond, form=form, tag=tag, prop=prop):

            try:
                await s_common.aspin(node.storm(storm, opts=opts, user=user))
            except (asyncio.CancelledError, s_exc.RecursionLimitHit):
                raise
            except Exception:
                logger.exception('Trigger encountered exception running storm query %s', storm)

    def pack(self):
        tdef = self.tdef.copy()

        useriden = tdef['user']
        triguser = self.view.core.auth.user(useriden)
        tdef['username'] = triguser.name

        return tdef

    def getStorNode(self, form):
        ndef = (form.name, form.type.norm(self.iden)[0])
        buid = s_common.buid(ndef)

        props = {
            'doc': self.tdef.get('doc', ''),
            'name': self.tdef.get('name', ''),
            'vers': self.tdef.get('ver', 1),
            'cond': self.tdef.get('cond'),
            'storm': self.tdef.get('storm'),
            'enabled': self.tdef.get('enabled'),
            'user': self.tdef.get('user'),
        }

        tag = self.tdef.get('tag')
        if tag is not None:
            props['tag'] = tag

        formprop = self.tdef.get('form')
        if formprop is not None:
            props['form'] = formprop

        prop = self.tdef.get('prop')
        if prop is not None:
            props['prop'] = prop

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms,
        })
