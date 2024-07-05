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

logger = logging.getLogger(__name__)

Conditions = set((
    'tag:add',
    'tag:del',
    'node:add',
    'node:del',
    'prop:set',
    'edge:add',
    'edge:del'
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
        'n2form': {'type': 'string', 'pattern': _formre},
        'tag': {'type': 'string', 'pattern': _tagre},
        'prop': {'type': 'string', 'pattern': _propre},
        'verb': {'type': 'string', },
        'name': {'type': 'string', },
        'doc': {'type': 'string', },
        'cond': {'enum': ['node:add', 'node:del', 'tag:add', 'tag:del', 'prop:set', 'edge:add', 'edge:del']},
        'storm': {'type': 'string'},
        'async': {'type': 'boolean'},
        'enabled': {'type': 'boolean'},
        'created': {'type': 'integer', 'minimum': 0},
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
        {
            'if': {'properties': {'cond': {'const': 'edge:add'}}},
            'then': {'required': ['verb']},
        },
        {
            'if': {'properties': {'cond': {'const': 'edge:del'}}},
            'then': {'required': ['verb']},
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

        self.tagadd = collections.defaultdict(list)    # (form, tag): [ Trigger ... ]
        self.tagset = collections.defaultdict(list)    # (form, tag): [ Trigger ... ]
        self.tagdel = collections.defaultdict(list)    # (form, tag): [ Trigger ... ]

        self.tagaddglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs
        self.tagsetglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs
        self.tagdelglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs

        self.nodeadd = collections.defaultdict(list)   # form: [ Trigger ... ]
        self.nodedel = collections.defaultdict(list)   # form: [ Trigger ... ]
        self.propset = collections.defaultdict(list)   # prop: [ Trigger ... ]

        self.edgeadd = collections.defaultdict(list)   # (n1form, verb, n2form: [ Trigger ... ]
        self.edgedel = collections.defaultdict(list)   # (n1form, verb, n2form: [ Trigger ... ]

        self.edgeaddglobs = collections.defaultdict(s_cache.EdgeGlobs)  # (n1form, n2form: [ EdgeGlobs ... ]
        self.edgedelglobs = collections.defaultdict(s_cache.EdgeGlobs)  # (n1form, n2form: [ EdgeGlobs ... ]

        self.edgeaddcache = s_cache.LruDict()
        self.edgedelcache = s_cache.LruDict()

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
        vars = {'propname': prop.name, 'propfull': prop.full,
                'auto': {'opts': {'propname': prop.name, 'propfull': prop.full, }},
                }
        with self._recursion_check():
            [await trig.execute(node, vars=vars) for trig in self.propset.get(prop.full, ())]
            if prop.univ is not None:
                [await trig.execute(node, vars=vars) for trig in self.propset.get(prop.univ.full, ())]

    async def runTagAdd(self, node, tag):

        vars = {'tag': tag, 'auto': {'opts': {'tag': tag}}}
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

        vars = {'tag': tag,
                'auto': {'opts': {'tag': tag}},
                }
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

    async def runEdgeAdd(self, n1, verb, n2):
        n1form = n1.form.name if n1 else None
        n2form = n2.form.name if n2 else None
        n2iden = n2.iden() if n2 else None
        varz = {'auto': {'opts': {'verb': verb, 'n2iden': n2iden}}}
        with self._recursion_check():
            cachekey = (n1form, verb, n2form)
            cached = self.edgeaddcache.get(cachekey)
            if cached is None:
                cached = []
                for trig in self.edgeadd.get((None, verb, None), ()):
                    cached.append(trig)

                globs = self.edgeaddglobs.get((None, None))
                if globs:
                    for _, trig in globs.get(verb):
                        cached.append(trig)

                if n1:
                    for trig in self.edgeadd.get((n1form, verb, None), ()):
                        cached.append(trig)

                    globs = self.edgeaddglobs.get((n1form, None))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                if n2:
                    for trig in self.edgeadd.get((None, verb, n2form), ()):
                        cached.append(trig)

                    globs = self.edgeaddglobs.get((None, n2form))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                if n1 and n2:
                    for trig in self.edgeadd.get((n1form, verb, n2form), ()):
                        cached.append(trig)

                    globs = self.edgeaddglobs.get((n1form, n2form))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                self.edgeaddcache[cachekey] = cached

            for trig in cached:
                await trig.execute(n1, vars=varz)

    async def runEdgeDel(self, n1, verb, n2):
        n1form = n1.form.name if n1 else None
        n2form = n2.form.name if n2 else None
        n2iden = n2.iden() if n2 else None
        varz = {'auto': {'opts': {'verb': verb, 'n2iden': n2iden}}}
        with self._recursion_check():
            cachekey = (n1form, verb, n2form)
            cached = self.edgedelcache.get(cachekey)
            if cached is None:
                cached = []
                for trig in self.edgedel.get((None, verb, None), ()):
                    cached.append(trig)

                globs = self.edgedelglobs.get((None, None))
                if globs:
                    for _, trig in globs.get(verb):
                        cached.append(trig)

                if n1:
                    for trig in self.edgedel.get((n1form, verb, None), ()):
                        cached.append(trig)

                    globs = self.edgedelglobs.get((n1form, None))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                if n2:
                    for trig in self.edgedel.get((None, verb, n2form), ()):
                        cached.append(trig)

                    globs = self.edgedelglobs.get((None, n2form))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                if n1 and n2:
                    for trig in self.edgedel.get((n1form, verb, n2form), ()):
                        cached.append(trig)

                    globs = self.edgedelglobs.get((n1form, n2form))
                    if globs:
                        for _, trig in globs.get(verb):
                            cached.append(trig)

                self.edgedelcache[cachekey] = cached

            for trig in cached:
                await trig.execute(n1, vars=varz)

    async def load(self, tdef):

        trig = Trigger(self.view, tdef)

        # Make sure the query parses
        storm = trig.tdef['storm']
        await self.view.core.getStormQuery(storm)

        cond = trig.tdef.get('cond')
        tag = trig.tdef.get('tag')
        form = trig.tdef.get('form')
        prop = trig.tdef.get('prop')
        verb = trig.tdef.get('verb')
        n2form = trig.tdef.get('n2form')

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
        if cond in ('edge:add', 'edge:del') and verb is None:
            raise s_exc.BadOptValu(mesg='verb must be present for edge:add or edge:del')

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

        elif cond == 'edge:add':
            self.edgeaddcache.clear()
            if '*' not in verb:
                self.edgeadd[(form, verb, n2form)].append(trig)
            else:
                self.edgeaddglobs[(form, n2form)].add(verb, trig)

        elif cond == 'edge:del':
            self.edgedelcache.clear()
            if '*' not in verb:
                self.edgedel[(form, verb, n2form)].append(trig)
            else:
                self.edgedelglobs[(form, n2form)].add(verb, trig)

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

        if cond == 'edge:add':
            verb = trig.tdef['verb']
            form = trig.tdef.get('form')
            n2form = trig.tdef.get('n2form')

            self.edgeaddcache.clear()
            if '*' not in verb:
                self.edgeadd[(form, verb, n2form)].remove(trig)
                return trig

            globs = self.edgeaddglobs.get((form, n2form))
            globs.rem(verb, trig)
            return trig

        if cond == 'edge:del':
            verb = trig.tdef['verb']
            form = trig.tdef.get('form')
            n2form = trig.tdef.get('n2form')

            self.edgedelcache.clear()
            if '*' not in verb:
                self.edgedel[(form, verb, n2form)].remove(trig)
                return trig

            globs = self.edgedelglobs.get((form, n2form))
            globs.rem(verb, trig)
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
        if name not in ('enabled', 'user', 'storm', 'doc', 'name', 'async'):
            raise s_exc.BadArg(mesg=f'Invalid key name provided: {name}')

        if valu == self.tdef.get(name):
            return

        if name == 'user':
            self.user = await self.view.core.auth.reqUser(valu)

        if name == 'storm':
            await self.view.core.getStormQuery(valu)

        self.tdef[name] = valu
        self.view.trigdict.set(self.iden, self.tdef)

    def get(self, name):
        return self.tdef.get(name)

    async def execute(self, node, vars=None):
        '''
        Actually execute the query
        '''
        if not self.tdef.get('enabled'):
            return

        if self.tdef.get('async'):
            triginfo = {'buid': node.buid, 'trig': self.iden, 'vars': vars}
            await self.view.addTrigQueue(triginfo)
            return

        return await self._execute(node, vars=vars)

    async def _execute(self, node, vars=None):

        locked = self.user.info.get('locked')
        if locked:
            if not self.lockwarned:
                self.lockwarned = True
                logger.warning(f'Skipping trigger execution because user {self.user.iden} is locked')
            return

        storm = self.tdef.get('storm')

        query = await self.view.core.getStormQuery(storm)

        if vars is None:
            vars = {}
        else:
            vars = vars.copy()

        autovars = vars.setdefault('auto', {})
        autovars.update({'iden': self.iden, 'type': 'trigger'})
        optvars = autovars.setdefault('opts', {})
        optvars['form'] = node.ndef[0]
        optvars['valu'] = node.ndef[1]

        opts = {'vars': vars, 'user': self.user.iden, 'view': self.view.iden}

        self.startcount += 1

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
            '.created': self.tdef.get('created')
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

        verb = self.tdef.get('verb')
        if verb is not None:
            props['verb'] = verb

        n2form = self.tdef.get('n2form')
        if n2form is not None:
            props['n2form'] = n2form

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms,
        })
