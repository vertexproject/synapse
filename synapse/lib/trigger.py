import asyncio
import logging
import contextlib
import collections
import contextvars

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
import synapse.lib.provenance as s_provenance

logger = logging.getLogger(__name__)

Conditions = set((
    'tag:add',
    'tag:del',
    'tag:set',
    'node:add',
    'node:del',
    'prop:set',
))

RecursionDepth = contextvars.ContextVar('RecursionDepth', default=0)

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
        with self._recursion_check():
            [await trig.execute(node) for trig in self.propset.get(prop.full, ())]
            if prop.univ is not None:
                [await trig.execute(node) for trig in self.propset.get(prop.univ, ())]

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

    async def runTagSet(self, node, tag, oldv):

        vars = {'tag': tag}
        with self._recursion_check():

            for trig in self.tagset.get((node.form.name, tag), ()):
                await trig.execute(node, vars=vars)

            for trig in self.tagset.get((None, tag), ()):
                await trig.execute(node, vars=vars)

            # check for form specific globs
            globs = self.tagsetglobs.get(node.form.name)
            if globs is not None:
                for _, trig in globs.get(tag):
                    await trig.execute(node, vars=vars)

            # check for form agnostic globs
            globs = self.tagsetglobs.get(None)
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

        self.triggers[trig.iden] = trig

        cond = trig.tdef.get('cond')

        if cond == 'node:add':
            form = trig.tdef['form']
            self.nodeadd[form].append(trig)
            return trig

        if cond == 'node:del':
            form = trig.tdef['form']
            self.nodedel[form].append(trig)
            return trig

        if cond == 'prop:set':
            prop = trig.tdef['prop']
            self.propset[prop].append(trig)
            return trig

        if cond == 'tag:add':

            tag = trig.tdef['tag']
            form = trig.tdef.get('form')

            if '*' not in tag:
                self.tagadd[(form, tag)].append(trig)
                return trig

            # we have a glob add
            self.tagaddglobs[form].add(tag, trig)
            return trig

        if cond == 'tag:del':

            tag = trig.tdef.get('tag')
            form = trig.tdef.get('form')

            if '*' not in trig.tag:
                self.tagdel[(trig.form, trig.tag)].append(trig)
                return trig

            self.tagdelglobs[trig.form].add(trig.tag, trig)
            return trig

        if cond == 'tag:set':

            if '*' not in trig.tag:
                self.tagset[(trig.form, trig.tag)].append(trig)
                return trig

            # we have a glob add
            self.tagsetglobs[trig.form].add(trig.tag, trig)
            return trig

        raise s_exc.NoSuchCond(name=cond)

    def list(self):
        return list(self.triggers.items())

    def _reqTrig(self, iden):
        trig = self.triggers.get(iden)
        if trig is None:
            mesg = f'No trigger with iden {iden}'
            raise s_exc.NoSuchIden(iden=iden, mesg=mesg)
        return trig

    def pop(self, iden):

        trig = self.triggers.pop(iden, None)
        if trig is None:
            self.get(iden)

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

    def get(self, iden):
        trig = self.triggers.get(iden)
        if trig is None:
            mesg = f'No trigger with iden {iden}'
            raise s_exc.NoSuchIden(iden=iden, mesg=mesg)
        return trig


class Trigger:

    def __init__(self, view, tdef):
        self.view = view
        self.tdef = tdef
        # FIXME: need json schema check
        assert 'storm' in tdef

        self.iden = tdef.get('iden')

    async def set(self, name, valu):
        '''
        Set one of the dynamic elements of the trigger definition.
        '''
        assert name in ('enabled', 'storm', 'doc', 'name')

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
            except asyncio.CancelledError: # pragma: no cover
                raise
            except Exception:
                logger.exception('Trigger encountered exception running storm query %s', self.storm)

    def pack(self):
        return self.tdef.copy()

    def getStorNode(self, form='syn:trigger'):
        ndef = (form, self.iden)
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

        form = self.tdef.get('form')
        if form is not None:
            props['form'] = form

        prop = self.tdef.get('prop')
        if prop is not None:
            props['prop'] = prop

        return (buid, {
            'ndef': ndef,
            'props': props,
        })
