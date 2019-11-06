import asyncio
import logging
import contextlib
import collections
import contextvars
import dataclasses

from typing import Optional

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.cache as s_cache
import synapse.lib.msgpack as s_msgpack
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

class Triggers:
    def __init__(self, view):
        self._rules = {}
        self.view = view

        self.tagadd = collections.defaultdict(list)    # (form, tag): rule
        self.tagdel = collections.defaultdict(list)    # (form, tag): rule

        self.tagaddglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs
        self.tagdelglobs = collections.defaultdict(s_cache.TagGlobs)    # form: TagGlobs

        self.nodeadd = collections.defaultdict(list)   # form: rule
        self.nodedel = collections.defaultdict(list)   # form: rule
        self.propset = collections.defaultdict(list)   # prop: rule

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
            [await rule.execute(node) for rule in self.nodeadd.get(node.form.name, ())]

    async def runNodeDel(self, node):
        with self._recursion_check():
            [await rule.execute(node) for rule in self.nodedel.get(node.form.name, ())]

    async def runPropSet(self, node, prop, oldv):
        with self._recursion_check():
            [await rule.execute(node) for rule in self.propset.get(prop.full, ())]
            if prop.univ is not None:
                [await rule.execute(node) for rule in self.propset.get(prop.univ, ())]

    async def runTagAdd(self, node, tag):

        vars = {'tag': tag}
        with self._recursion_check():

            for rule in self.tagadd.get((node.form.name, tag), ()):
                await rule.execute(node, vars=vars)

            for rule in self.tagadd.get((None, tag), ()):
                await rule.execute(node, vars=vars)

            # check for form specific globs
            globs = self.tagaddglobs.get(node.form.name)
            if globs is not None:
                for expr, rule in globs.get(tag):
                    await rule.execute(node, vars=vars)

            # check for form agnostic globs
            globs = self.tagaddglobs.get(None)
            if globs is not None:
                for expr, rule in globs.get(tag):
                    await rule.execute(node, vars=vars)

    async def runTagDel(self, node, tag):

        vars = {'tag': tag}
        with self._recursion_check():

            for rule in self.tagdel.get((node.form.name, tag), ()):
                await rule.execute(node, vars=vars)

            for rule in self.tagdel.get((None, tag), ()):
                await rule.execute(node, vars=vars)

            # check for form specific globs
            globs = self.tagdelglobs.get(node.form.name)
            if globs is not None:
                for expr, rule in globs.get(tag):
                    await rule.execute(node, vars=vars)

            # check for form agnostic globs
            globs = self.tagdelglobs.get(None)
            if globs is not None:
                for expr, rule in globs.get(tag):
                    await rule.execute(node, vars=vars)

    def _load_rule(self, iden, ver, cond, user, query, enabled, info):
        rule = Rule(ver, cond, user, query, self.view.iden, enabled, triggers=self, iden=iden, **info)

        # Make sure the query parses
        self.view.core.getStormQuery(rule.storm)

        self._rules[iden] = rule

        if rule.cond == 'node:add':
            self.nodeadd[rule.form].append(rule)
            return rule

        if rule.cond == 'node:del':
            self.nodedel[rule.form].append(rule)
            return rule

        if rule.cond == 'prop:set':
            self.propset[rule.prop].append(rule)
            return rule

        if rule.cond == 'tag:add':

            if '*' not in rule.tag:
                self.tagadd[(rule.form, rule.tag)].append(rule)
                return rule

            # we have a glob add
            self.tagaddglobs[rule.form].add(rule.tag, rule)
            return rule

        if rule.cond == 'tag:del':

            if '*' not in rule.tag:
                self.tagdel[(rule.form, rule.tag)].append(rule)
                return rule

            self.tagdelglobs[rule.form].add(rule.tag, rule)
            return rule

        raise s_exc.NoSuchCond(name=rule.cond)

    def list(self):
        return list(self._rules.items())

    def mod(self, iden, query):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden(iden=iden)

        self.view.core.getStormQuery(query)

        rule.storm = query
        self.view.core.trigstor.stor(iden, rule)

    def enable(self, iden):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden(iden=iden)

        rule.enabled = True
        self.view.core.trigstor.stor(iden, rule)

    def disable(self, iden):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden(iden=iden)

        rule.enabled = False
        self.view.core.trigstor.stor(iden, rule)

    def add(self, useriden, condition, query, info):
        iden = s_common.guid()

        if not query:
            raise ValueError('empty query')

        self.view.core.getStormQuery(query)

        rule = self._load_rule(iden, 1, condition, useriden, query, True, info=info)
        self.view.core.trigstor.stor(iden, rule)
        return iden

    def delete(self, iden):

        rule = self._rules.pop(iden, None)
        if rule is None:
            raise s_exc.NoSuchIden(iden=iden)

        self.view.core.trigstor.delete(iden)

        if rule.cond == 'node:add':
            self.nodeadd[rule.form].remove(rule)
            return

        if rule.cond == 'node:del':
            self.nodedel[rule.form].remove(rule)
            return

        if rule.cond == 'prop:set':
            self.propset[rule.prop].remove(rule)
            return

        if rule.cond == 'tag:add':

            if '*' not in rule.tag:
                self.tagadd[(rule.form, rule.tag)].remove(rule)
                return

            globs = self.tagaddglobs.get(rule.form)
            globs.rem(rule.tag, rule)
            return

        if rule.cond == 'tag:del':

            if '*' not in rule.tag:
                self.tagdel[(rule.form, rule.tag)].remove(rule)
                return

            globs = self.tagdelglobs.get(rule.form)
            globs.rem(rule.tag, rule)
            return

    async def get(self, iden):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden(iden=iden)
        return rule

class TriggerStorage:

    def __init__(self, core):
        '''
        Initialize a cortex triggers subsystem.
        '''
        self.core = core

        self.trigdb = self.core.slab.initdb('triggers')

        self._load_all()

    def migrate_v0_rules(self):
        '''
        Remove any v0 (i.e. pre-010) rules from storage and replace them with v1 rules.

        Notes:
            v0 had two differences user was a username.  Replaced with iden of user as 'iden' field.
            Also 'iden' was storage as binary.  Now it is stored as hex string.
        '''
        # TODO:  due to our migration policy, remove in 0.2.0

        for iden, valu in self.core.slab.scanByFull(db=self.trigdb):
            ruledict = s_msgpack.un(valu)
            ver = ruledict.get('ver')
            if ver != 0:
                continue

            user = ruledict.pop('user')
            if user is None:
                logger.warning('Username missing in stored trigger rule %r', iden)
                continue

            # In v0, stored user was username, in >0 user is useriden
            user = self.core.auth.getUserByName(user).iden
            if user is None:
                logger.warning('Unrecognized username in stored trigger rule %r', iden)
                continue

            ruledict['ver'] = 1
            ruledict['useriden'] = user
            newiden = s_common.ehex(iden)
            self.core.slab.pop(iden, db=self.trigdb)
            self.core.slab.put(newiden.encode(), s_msgpack.en(ruledict), db=self.trigdb)

    def _migrate_old_view(self):
        '''
        Migrate from when cortex iden == view iden to where they are different
        '''
        # TODO:  due to our migration policy, remove in 0.3.0
        for iden, valu in self.core.slab.scanByFull(db=self.trigdb):
            ruledict = s_msgpack.un(valu)

            viewiden = ruledict.pop('viewiden', None)
            if viewiden == self.core.iden:
                viewiden = self.core.view.iden
                ruledict['viewiden'] = viewiden
                self.core.slab.put(iden, s_msgpack.en(ruledict), db=self.trigdb)

    def _load_all(self):
        self.migrate_v0_rules()
        self._migrate_old_view()
        for iden, valu in self.core.slab.scanByFull(db=self.trigdb):
            try:
                ruledict = s_msgpack.un(valu)
                ver = ruledict.pop('ver')
                cond = ruledict.pop('cond')
                user = ruledict.pop('useriden')
                query = ruledict.pop('storm')
                enabled = ruledict.pop('enabled', True)
                viewiden = ruledict.pop('viewiden', None)
                view = self.core.getView(viewiden)
                view.triggers._load_rule(iden.decode(), ver, cond, user, query, enabled, info=ruledict)
            except (KeyError, s_exc.SynErr) as e:
                logger.warning('Invalid rule %r found in storage: %r', iden, e)
                continue

    def stor(self, iden, rule):
        self.core.slab.put(iden.encode(), rule.en(), db=self.trigdb)

    def delete(self, iden):
        self.core.slab.delete(iden.encode(), db=self.trigdb)

@dataclasses.dataclass
class Rule:
    ver: int  # version: must be 1
    cond: str  # condition from above list
    useriden: str
    storm: str  # storm query
    viewiden: str # owning view
    enabled: bool = True
    doc: Optional[str] = dataclasses.field(default='') # documentation / description
    name: Optional[str] = dataclasses.field(default='') # humon friendly name
    form: Optional[str] = dataclasses.field(default=None) # form name
    tag: Optional[str] = dataclasses.field(default=None) # tag name
    prop: Optional[str] = dataclasses.field(default=None) # property name

    iden: dataclasses.InitVar[Optional[str]] = None
    triggers: dataclasses.InitVar[Optional[Triggers]] = None

    def __post_init__(self, iden, triggers):

        self.iden = iden
        self.triggers = triggers

        if self.ver != 1:
            raise s_exc.BadOptValu(mesg='Unexpected rule version')
        if self.cond not in Conditions:
            raise s_exc.BadOptValu(mesg='Invalid trigger condition')
        if self.cond in ('node:add', 'node:del') and self.form is None:
            raise s_exc.BadOptValu(mesg='form must be present for node:add or node:del')
        if self.cond in ('node:add', 'node:del') and self.tag is not None:
            raise s_exc.BadOptValu(mesg='tag must not be present for node:add or node:del')
        if self.cond == 'prop:set' and (self.form is not None or self.tag is not None):
            raise s_exc.BadOptValu(mesg='form and tag must not be present for prop:set')
        if self.cond in ('tag:add', 'tag:del'):
            if self.tag is None:
                raise s_exc.BadOptValu(mesg='missing tag')
            s_chop.validateTagMatch(self.tag)
        if self.prop is not None and self.cond != 'prop:set':
            raise s_exc.BadOptValu(mesg='prop parameter invalid')
        if self.cond == 'prop:set' and self.prop is None:
            raise s_exc.BadOptValu(mesg='missing prop parameter')

    def en(self):
        return s_msgpack.en(dataclasses.asdict(self))

    async def execute(self, node, vars=None):
        '''
        Actually execute the query
        '''
        opts = {}

        if not self.enabled:
            return

        if vars is not None:
            opts['vars'] = vars

        user = node.snap.core.auth.user(self.useriden)
        if user is None:
            logger.warning('Unknown user %s in stored trigger', self.useriden)
            return

        with s_provenance.claim('trig', cond=self.cond, form=self.form, tag=self.tag, prop=self.prop):

            try:
                await s_common.aspin(node.storm(self.storm, opts=opts, user=user))
            except asyncio.CancelledError: # pragma: no cover
                raise
            except Exception:
                logger.exception('Trigger encountered exception running storm query %s', self.storm)

    def pack(self):
        return dataclasses.asdict(self)

    async def reqAllowed(self, user, perm):
        if not await self.allowed(user, perm):
            raise s_exc.AuthDeny(perm=perm)

    async def allowed(self, user, perm):
        if user.iden == self.useriden:
            return True

        return user.allowed(perm)

    async def setDoc(self, text):
        self.doc = text
        await self._save()

    async def setName(self, text):
        self.name = text
        await self._save()

    async def _save(self):
        self.triggers.view.core.trigstor.stor(self.iden, self)
