# FIXME support ival splices
# FIXME implement roles/groups/users/perms

import copy
import fnmatch
import operator

from synapse.eventbus import EventBus
import synapse.lib.syntax as s_syntax

class Membrane(EventBus):

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
    _DEFAULT_RULE = [{'query': '', 'insts': []}]
    _OPERS = {
        'eq': operator.eq,
        'ne': operator.ne,
        'le': operator.le,
        'ge': operator.ge,
        'lt': operator.lt,
        'gt': operator.gt,
        'has': operator.eq,
        'tag': fnmatch.fnmatch,
    }

    def __init__(self, src=None, dst=None, rules=None, default=False):
        '''
        Filters Cortex splices based on rules and forwards to destination Cortex if rules allow.

        Args:
            dst: the destination Cortex to forward messages to
            rules: the filter rules
        '''
        EventBus.__init__(self)

        self.src = src
        self.dst = dst
        if not(self.src or self.dst):
            # FIXME create exception type for this
            raise Exception('need a src or dst')

        if not self.src:
            self.src = self

        if not self.dst:
            self.dst = self

        self.rules = {'': {k: copy.deepcopy(Membrane._DEFAULT_RULE) for k in Membrane._SPLICE_NAMES}}
        if rules:
            self._prep_rules(rules)

        self.default = default

        self.src.on('splice', self.filter)

    def filter(self, mesg):
        '''
        Runs the filter on a given splice message.

        Args:
            mesg (str, dict): a synapse splice message

        Returns:
            (boolean): True if the splice was forwarded
        '''
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
        return self.fire('splice', **mesg[1])

    def _prep_rules(self, rules):
        for key in rules:
            for rule in rules[key]:
                insts = s_syntax.parse(rule.get('query', ''))
                for inst in insts:
                    if inst[0] != 'filt':
                        raise Exception('invalid inst: %s' % inst[0])  # FIXME exception type
                rule['insts'] = insts
                self.rules[''][key].append(rule)

    def _eval_rules(self, splice):
        act = splice.get('act')
        user = splice.get('user')
        if user is None: user = ''  # "no user" comes in as None, we want empty string

        for rule in self.rules.get(user, {}).get(act, []):
            insts = rule.get('insts')
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

            if oper == 'filt':
                rcmp = inst[1].get('cmp')
                rmode = inst[1].get('mode')
                rprop = inst[1].get('prop')
                rvalu = inst[1].get('valu')
                rtag = inst[1].get('tag')

                if rcmp != 'tag':
                    fullprop = form
                    if prop:
                        fullprop += ':' + prop

                    if rmode == 'must' and rprop != fullprop:
                        print('if filt is in must mode, props must match')
                        return False

                    if rprop != fullprop:
                        print('rprop is not fullprop')
                        continue

                cmpfn = Membrane._OPERS.get(rcmp)
                cmpa, cmpb = valu, rvalu
                if rcmp == 'has':
                    cmpa, cmpb = fullprop, rprop
                elif rcmp == 'tag':
                    cmpa, cmpb = tag, rvalu

                matched = cmpfn(cmpa, cmpb)
                if rmode == 'must':
                    return matched
                elif matched is True and rmode == 'cant':
                    return False
