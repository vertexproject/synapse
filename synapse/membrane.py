# FIXME support ival splices
# FIXME implement roles/groups/users/perms

import copy
import fnmatch
import operator

from synapse.eventbus import EventBus
import synapse.lib.syntax as s_syntax

class Membrane(EventBus):

    def __init__(self, src=None, dst=None, rules=None, default=None):
        '''
        Filters Cortex splices based on rules and forwards to destination Cortex if rules allow.

        Args:
            dst: the destination Cortex to forward messages to
            rules: the filter rules
        '''
        EventBus.__init__(self)

        _SPLICE_NAMES = (
            'node:add',
            'node:del',
            'node:prop:set',
            'node:prop:del',
            'node:tag:add',
            'node:tag:del',
            #'node:ival:set',
            #'node:ival:del',
        )
        _DEFAULT_RULE = [{'query': ''}]
        _DEFAULT_RULES = {'': {k: copy.deepcopy(_DEFAULT_RULE) for k in _SPLICE_NAMES}}

        self.rules = copy.deepcopy(_DEFAULT_RULES)
        if rules:
            for key in rules:
                for rule in rules[key]:
                    if self._is_valid_rule(rule):
                        self.rules[''][key].append(rule)

        self.opers = {
            'eq': operator.eq,
            'ne': operator.ne,
            'le': operator.le,
            'ge': operator.ge,
            'lt': operator.lt,
            'gt': operator.gt,

            'has': operator.eq,
            'tag': fnmatch.fnmatch,
        }

        self.default = False
        if default in (True, False):
            self.default = default

        self.src = src
        if not self.src:
            self.src = self

        self.dst = dst
        if not self.dst:
            self.dst = self

        self.src.on('splice', self.filter)

    def filter(self, mesg):
        '''
        Runs the filter on a given splice message.

        Args:
            mesg: a synapse splice message

        Returns:
            result: boolean
        '''
        if not(isinstance(mesg, tuple) and len(mesg) == 2 and mesg[0] == 'splice' and isinstance(mesg[1], dict)):
            print('invalid message: %s' % mesg)
            return

        result = self._eval_rules(mesg[1])
        if result is None:
            result = self.default

        if result:
            self.dst.splice(mesg)

        return result

    def splice(self, mesg):
        '''
        Refire a splice message
        '''
        if not(isinstance(mesg, tuple) and len(mesg) == 2 and mesg[0] == 'splice' and isinstance(mesg[1], dict)):
            print('invalid message: %s' % mesg)
            return

        return self.fire('splice', **mesg[1])

    def _is_valid_rule(self, rule):
        for inst in s_syntax.parse(rule.get('query', '')):
            if inst[0] != 'filt':
                print('invalid inst: %s' % inst[0])
                return False
        return True

    def _eval_rules(self, splice):
        act = splice.get('act')
        user = splice.get('user')
        if user is None: user = ''  # "no user" comes in as None, we want empty string

        for rule in self.rules.get(user, {}).get(act, []):
            query = rule.get('query', '')
            insts = s_syntax.parse(query)
            if not insts:
                print('nothing to do')
                continue

            ret = self._eval_insts(splice, insts)
            if ret is not None:
                return ret

    def _eval_insts(self, splice, insts):

        form = splice.get('form')
        valu = splice.get('valu')
        prop = splice.get('prop')
        tag = splice.get('tag')

        for inst in insts:
            oper = inst[0]

            if oper is 'filt':
                rcmp = inst[1].get('cmp')
                rmode = inst[1].get('mode')
                rprop = inst[1].get('prop')
                rvalu = inst[1].get('valu')
                rtag = inst[1].get('tag')

                if rcmp is not 'tag':
                    fullprop = form
                    if prop:
                        fullprop += ':' + prop

                    if rmode is 'must' and rprop != fullprop:
                        print('if filt is in must mode, props must match')
                        return False

                    if rprop != fullprop:
                        print('rprop is not fullprop')
                        continue

                cmpfn = self.opers.get(rcmp)
                cmpa, cmpb = valu, rvalu
                if rcmp == 'has':
                    cmpa, cmpb = fullprop, rprop
                elif rcmp is 'tag':
                    cmpa, cmpb = tag, rvalu

                matched = cmpfn(cmpa, cmpb)
                if rmode is 'must':
                    return matched
                elif matched is True and rmode is 'cant':
                    return False
