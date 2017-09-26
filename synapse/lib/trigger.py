import logging
import collections

import synapse.lib.cache as s_cache

logger = logging.getLogger(__name__)

class Triggers:

    def __init__(self):
        self._trig_list = []
        self._trig_match = s_cache.MatchCache()
        self._trig_byname = s_cache.Cache(onmiss=self._onTrigNameMiss)

    def clear(self):
        '''
        Clear all previously registered triggers
        '''
        self._trig_list = []
        self._trig_byname.clear()

    def add(self, func, perm):
        '''
        Add a new callback to the triggers.

        Args:
            func (function):    The function to call
            perm (str,dict):    The permission tufo

        Returns:
            (None)
        '''
        self._trig_list.append((perm, func))
        self._trig_byname.clear()

    def _onTrigNameMiss(self, name):
        retn = []
        for perm, func in self._trig_list:
            if self._trig_match.match(name, perm[0]):
                retn.append((perm, func))
        return retn

    def _cmpperm(self, perm, must):

        for prop, match in must[1].items():

            valu = perm[1].get(prop)
            if valu is None:
                return False

            if not self._trig_match.match(valu, match):
                return False

        return True

    def trigger(self, perm, *args, **kwargs):
        '''
        Fire any matching trigger functions for the given perm.

        Args:
            perm ((str,dict)):  The perm tufo to trigger
            *args (list):       args list to use calling the trigger function
            **kwargs (dict):    kwargs dict to use calling the trigger function

        Returns:
            (None)
        '''
        for must, func in self._trig_byname.get(perm[0]):
            if self._cmpperm(perm, must):
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.exception(e)
