import contextlib

import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope

class Rules:
    '''
    Rules provides an abstraction for metadata
    based filtration of events and tufos.

    Each "rule" is a tuple of:
        (allow, perm): (bool, (str, dict))
    '''

    def __init__(self, rules):
        self._r_rules = rules
        self._r_match = s_cache.MatchCache()
        self._r_rules_by_perm = s_cache.Cache(onmiss=self._onRulesPermMiss)

    def _onRulesPermMiss(self, name):
        retn = []
        for rule in self._r_rules:
            if self._r_match.match(name, rule[1][0]):
                retn.append(rule)
        return retn

    def _cmprule(self, rule, perm):

        for prop, must in rule[1][1].items():

            valu = perm[1].get(prop)
            if valu is None:
                return False

            if not self._r_match.match(valu, must):
                return False

        return True

    def allow(self, perm):
        '''
        Returns True if the given perm/info is allowed by the rules.

        Args:
            perm ((str,dict)): The requested permission tuple

        Returns:
            (bool):  True if the rules allow the perm/info
        '''
        for rule in self._r_rules_by_perm.get(perm[0]):
            if self._cmprule(rule, perm):
                return rule[0]

        return False

def whoami():
    '''
    Return the name of the current synapse user for this thread.

    Example:

        name = s_auth.whoami()

    '''
    return s_scope.get('syn:user', 'root@localhost')

@contextlib.contextmanager
def runas(user):
    '''
    Construct and return a with-block object which runs as the given
    synapse user name.

    Example:

        import synapse.lib.auth as s_auth

        s_auth.runas('visi@localhost'):
            # calls from here down may use check user/perms
            dostuff()

    '''
    with s_scope.enter({'syn:user': user}):
        yield
