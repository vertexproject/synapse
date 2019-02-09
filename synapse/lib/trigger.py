import os
import logging
import contextlib
import collections
import contextvars
import dataclasses

from typing import Optional

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.msgpack as s_msgpack

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

    TRIGGERS_DB_NAME = 'triggers'
    RECURSION_LIMIT = 16

    @dataclasses.dataclass
    class Rule:
        ver: int  # version: must be 0
        cond: str  # condition from above list
        user: str  # username
        storm: str  # story query
        form: Optional[str] = dataclasses.field(default=None) # form name
        tag: Optional[str] = dataclasses.field(default=None) # tag name
        prop: Optional[str] = dataclasses.field(default=None) # property name

        def __post_init__(self):
            if self.ver != 0:
                raise s_exc.BadOptValu(mesg='Unexpected rule version')
            if self.cond not in Conditions:
                raise s_exc.BadOptValu(mesg='Invalid trigger condition')
            if self.cond in ('node:add', 'node:del') and self.form is None:
                raise s_exc.BadOptValu(mesg='form must be present for node:add or node:del')
            if self.cond in ('node:add', 'node:del') and self.tag is not None:
                raise s_exc.BadOptValu(mesg='tag must not be present for node:add or node:del')
            if self.cond == 'prop:set' and (self.form is not None or self.tag is not None):
                raise s_exc.BadOptValu(mesg='form and tag must not be present for prop:set')
            if self.cond in ('tag:add', 'tag:del') and self.tag is None:
                raise s_exc.BadOptValu(mesg='missing tag')
            if self.prop is not None and self.cond != 'prop:set':
                raise s_exc.BadOptValu(mesg='prop parameter invalid')
            if self.cond == 'prop:set' and self.prop is None:
                raise s_exc.BadOptValu(mesg='missing prop parameter')
            if self.tag is not None:
                if '*' in self.tag[:-1] or (self.tag[-1] == '*' and self.tag[-2] != '.'):
                    raise s_exc.BadOptValu(mesg='only tag globbing at end supported')

        def en(self):
            return s_msgpack.en(dataclasses.asdict(self))

        async def execute(self, node, tag=None):
            '''
            Actually execute the query
            '''
            opts = None if tag is None else {'vars': {'tag': tag}}
            if node.snap.core.auth is not None:
                user = node.snap.core.auth.getUserByName(self.user)
                if user is None:
                    logger.warning('Unknown user %s in stored trigger', self.user)
                    return
            else:
                user = None
            try:
                await s_common.aspin(node.storm(self.storm, opts=opts, user=user))
            except Exception:
                logger.exception('Trigger encountered exception running storm query %s', self.storm)

    def __init__(self, core):
        '''
        Initialize a cortex triggers subsystem.

        Note:
            Triggers will not fire until enable() is called.
        '''
        self._rules = {}
        self._rule_by_prop = collections.defaultdict(list)
        self._rule_by_form = collections.defaultdict(list)
        self._rule_by_tag = collections.defaultdict(list)
        self.core = core
        self.enabled = False
        self._load_all(self.core.slab)
        self._deferred_events = []

    async def enable(self):
        '''
        Enable triggers to start firing.

        Go through all the rules, making sure the query is valid, and remove the ones that aren't.  (We can't evaluate
        queries until enabled because not all the modules are loaded yet.)
        '''
        if self.enabled:
            return

        to_delete = []
        for iden, rule in self._rules.items():
            try:
                self.core.getStormQuery(rule.storm)
            except Exception as e:
                logger.warning('Invalid rule %r found in storage: %r.  Removing.', iden, e)
                to_delete.append(iden)
        for iden in to_delete:
            self.delete(iden, persistent=False)

        self.enabled = True

        # Re-evaluate all the events that occurred before we were enabled
        for node, cond, info in self._deferred_events:
            await self.run(node, cond, info=info)

        self._deferred_events.clear()

    def _load_all(self, slab):
        db = slab.initdb(self.TRIGGERS_DB_NAME)
        for iden, val in self.core.slab.scanByRange(b'', db=db):
            try:
                ruledict = s_msgpack.un(val)
                ver = ruledict.pop('ver')
                cond = ruledict.pop('cond')
                user = ruledict.pop('user')
                query = ruledict.pop('storm')
                self._load_rule(iden, ver, cond, user, query, info=ruledict)
            except Exception as e:
                logger.warning('Invalid rule %r found in storage: %r', iden, e)
                continue

    def _load_rule(self, iden, ver, cond, user, query, info):

        rule = Triggers.Rule(ver, cond, user, query, **info)

        ''' Make sure the query parses '''
        if self.enabled:
            self.core.getStormQuery(rule.storm)

        self._rules[iden] = rule
        if rule.prop is not None:
            self._rule_by_prop[rule.prop].append(rule)
        elif rule.form is not None:
            self._rule_by_form[rule.form].append(rule)
        else:
            assert rule.tag
            self._rule_by_tag[rule.tag].append(rule)
        return rule

    def list(self):
        return [(iden, dataclasses.asdict(rule)) for iden, rule in self._rules.items()]

    def mod(self, iden, query):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden()

        if self.enabled:
            self.core.getStormQuery(query)

        db = self.core.slab.initdb(self.TRIGGERS_DB_NAME)
        rule.storm = query
        self.core.slab.put(iden, rule.en(), db=db)

    @contextlib.contextmanager
    def _recursion_check(self):
        depth = RecursionDepth.get()
        if depth > self.RECURSION_LIMIT:
            raise s_exc.RecursionLimitHit(mesg='Hit trigger limit')
        token = RecursionDepth.set(depth + 1)

        try:
            yield

        finally:
            RecursionDepth.reset(token)

    async def run(self, node, cond, *, info):
        '''
        Execute any rules that match the condition and arguments
        '''

        if not self.enabled:
            self._deferred_events.append((node, cond, info))
            return

        if __debug__:
            try:
                Triggers.Rule(0, cond, '', '', **info)
            except s_exc.BadOptValu:
                logger.exception('fire called with inconsistent arguments')
                assert False

        def parent_glob(tag):
            ''' Returns foo.* given foo.bar or None if already top level '''
            if tag is None or tag[0] == '.' or '.' not in tag:
                return None
            return tag.rsplit('.', 1)[0] + '.*'

        with self._recursion_check():

            prop = info.get('prop')
            tag = info.get('tag')
            form = info.get('form')

            if prop is not None:
                for rule in self._rule_by_prop[prop]:
                    await rule.execute(node)
                return

            glob_tag = parent_glob(tag)

            if form is not None:
                for rule in self._rule_by_form[form]:
                    if cond == rule.cond and (rule.tag is None or rule.tag == tag or rule.tag == glob_tag):
                        await rule.execute(node, tag)

            if tag is not None:
                for rule in self._rule_by_tag[tag]:
                    if cond == rule.cond:
                        await rule.execute(node, tag)
                if tag[0] != '.' and '.' in tag:
                    for rule in self._rule_by_tag[glob_tag]:
                        if cond == rule.cond:
                            await rule.execute(node, tag)

    def add(self, username, condition, query, *, info):

        iden = os.urandom(16)
        db = self.core.slab.initdb(self.TRIGGERS_DB_NAME)

        if not query:
            raise ValueError('empty query')

        # Check the storm query if we can
        if self.enabled:
            self.core.getStormQuery(query)

        rule = self._load_rule(iden, 0, condition, username, query, info=info)
        self.core.slab.put(iden, rule.en(), db=db)
        return iden

    def delete(self, iden, persistent=True):
        '''
        Args:
            persistent (bool): if True, removes from persistent storage as well
        '''
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden()

        db = self.core.slab.initdb(self.TRIGGERS_DB_NAME)

        if rule.prop is not None:
            self._rule_by_prop[rule.prop].remove(rule)
        elif rule.form is not None:
            self._rule_by_form[rule.form].remove(rule)
        else:
            assert rule.tag is not None
            self._rule_by_tag[rule.tag].remove(rule)

        del self._rules[iden]
        if persistent:
            self.core.slab.delete(iden, db=db)

    def get(self, iden):
        rule = self._rules.get(iden)
        if rule is None:
            raise s_exc.NoSuchIden()
        return dataclasses.asdict(rule)
