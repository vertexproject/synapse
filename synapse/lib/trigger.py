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

TrigSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'form': {'type': 'string', 'pattern': _formre},
        'tag': {'type': 'string', 'pattern': _tagre},
        'prop': {'type': 'string', 'pattern': _propre},
        'name': {'type': 'string', },
        'doc': {'type': 'string', },
        'cond': {'enum': ['node:add', 'node:del', 'tag:add', 'tag:del', 'prop:set']},
        'storm': {'type': 'string'},
        'async': {'type': 'boolean'},
        'enabled': {'type': 'boolean'},
    },
    'additionalProperties': True,
    'required': ['iden', 'user', 'storm', 'enabled'],
    'allOf': [
        {
            'if': {'properties': {'cond': {'const': 'node:add'}}},
            'then': {'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'node:del'}}},
            'then': {'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:add'}}},
            'then': {'required': ['tag']},
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:del'}}},
            'then': {'required': ['tag']},
        },
        {
            'if': {'properties': {'cond': {'const': 'prop:set'}}},
            'then': {'required': ['prop']},
        },
    ],
}
TrigSchemaValidator = s_config.getJsValidator(TrigSchema)

def reqValidTdef(conf):
    TrigSchemaValidator(conf)

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

    async def runNodeAdd(self, node, view=None):
        with self._recursion_check():
            [await trig.execute(node, view=view) for trig in self.nodeadd.get(node.form.name, ())]

    async def runNodeDel(self, node, view=None):
        with self._recursion_check():
            [await trig.execute(node, view=view) for trig in self.nodedel.get(node.form.name, ())]

    async def runPropSet(self, node, prop, oldv, view=None):
        vars = {'propname': prop.name, 'propfull': prop.full,
                'auto': {'opts': {'propname': prop.name, 'propfull': prop.full, }},
                }
        with self._recursion_check():
            [await trig.execute(node, vars=vars, view=view) for trig in self.propset.get(prop.full, ())]
            if prop.univ is not None:
                [await trig.execute(node, vars=vars, view=view) for trig in self.propset.get(prop.univ.full, ())]

    async def runTagAdd(self, node, tag, view=None):

        vars = {'tag': tag,
                'auto': {'opts': {'tag': tag}},
                }
        with self._recursion_check():

            for trig in self.tagadd.get((node.form.name, tag), ()):
                await trig.execute(node, vars=vars, view=view)

            for trig in self.tagadd.get((None, tag), ()):
                await trig.execute(node, vars=vars, view=view)

            # check for form specific globs
            globs = self.tagaddglobs.get(node.form.name)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars, view=view)

            # check for form agnostic globs
            globs = self.tagaddglobs.get(None)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars, view=view)

    async def runTagDel(self, node, tag, view=None):

        vars = {'tag': tag,
                'auto': {'opts': {'tag': tag}},
                }
        with self._recursion_check():

            for trig in self.tagdel.get((node.form.name, tag), ()):
                await trig.execute(node, vars=vars, view=view)

            for trig in self.tagdel.get((None, tag), ()):
                await trig.execute(node, vars=vars, view=view)

            # check for form specific globs
            globs = self.tagdelglobs.get(node.form.name)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars, view=view)

            # check for form agnostic globs
            globs = self.tagdelglobs.get(None)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars, view=view)

    async def load(self, tdef):

        trig = Trigger(self.view, tdef)

        # Make sure the query parses
        storm = trig.tdef['storm']
        await self.view.core.getStormQuery(storm)

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
        self.lockwarned = False
        self.startcount = 0
        self.errcount = 0
        self.lasterrs = collections.deque((), maxlen=5)

        useriden = self.tdef.get('user')
        self.user = self.view.core.auth.user(useriden)

    async def set(self, name, valu):
        '''
        Set one of the dynamic elements of the trigger definition.
        '''
        assert name in ('enabled', 'user', 'storm', 'doc', 'name', 'async')

        if valu == self.tdef.get(name):
            return

        if name == 'user':
            self.user = await self.view.core.auth.reqUser(valu)

        if name == 'storm':
            await self.view.core.getStormQuery(valu)

        self.tdef[name] = valu
        await self.view.trigdict.set(self.iden, self.tdef)

    def get(self, name):
        return self.tdef.get(name)

    async def execute(self, node, vars=None, view=None):
        '''
        Actually execute the query
        '''
        if not self.tdef.get('enabled'):
            return

        if self.tdef.get('async'):
            triginfo = {'buid': node.buid, 'trig': self.iden, 'vars': vars}
            await self.view.addTrigQueue(triginfo)
            return

        return await self._execute(node, vars=vars, view=view)

    async def _execute(self, node, vars=None, view=None):

        locked = self.user.info.get('locked')
        if locked:
            if not self.lockwarned:
                self.lockwarned = True
                logger.warning(f'Skipping trigger execution because user {self.user.iden} is locked')
            return

        tag = self.tdef.get('tag')
        cond = self.tdef.get('cond')
        form = self.tdef.get('form')
        prop = self.tdef.get('prop')
        storm = self.tdef.get('storm')

        query = await self.view.core.getStormQuery(storm)

        if view is None:
            view = self.view.iden

        if vars is None:
            vars = {}
        else:
            vars = vars.copy()

        autovars = vars.setdefault('auto', {})
        autovars.update({'iden': self.iden, 'type': 'trigger'})
        optvars = autovars.setdefault('opts', {})
        optvars['form'] = node.ndef[0]
        optvars['valu'] = node.ndef[1]

        opts = {
            'vars': vars,
            'view': view,
            'user': self.user.iden,
        }

        self.startcount += 1

        with s_provenance.claim('trig', cond=cond, form=form, tag=tag, prop=prop):
            try:
                async with self.view.core.getStormRuntime(query, opts=opts) as runt:

                    runt.addInput(node)
                    await s_common.aspin(runt.execute())

            except (asyncio.CancelledError, s_exc.RecursionLimitHit):
                raise

            except Exception as e:
                self.errcount += 1
                self.lasterrs.append(str(e))
                logger.exception('Trigger encountered exception running storm query %s', storm)

    def pack(self):
        tdef = self.tdef.copy()

        useriden = tdef['user']
        triguser = self.view.core.auth.user(useriden)
        tdef['startcount'] = self.startcount
        tdef['errcount'] = self.errcount
        tdef['lasterrs'] = list(self.lasterrs)
        if triguser is not None:
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
