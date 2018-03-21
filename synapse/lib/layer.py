'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import logging

import synapse.common as s_common

logger = logging.getLogger(__name__)

#class Type:

    #def __init__(self, name, modl, info, opts=None):

        #if opts is None:
            #opts = {}

        #self._type_name = name
        #self._type_modl = modl
        #self._type_info = info
        #self._type_opts = opts

class Layer:
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    def __init__(self, dirn, conf=None):

        self.dirn = s_common.gendir(dirn)
        s_config.Configable.__init__(self)

        if conf is not None:
            self.setConfOpts(conf)

        path = s_common.genpath(dirn, 'props.lmdb')
        self._lenv_props = lmdb.open_db(path)

        # ('prop:eq', (prop, valu, kval), {}) -> ((buid, prop, valu), ...)
        # prop:pref
        # prop:range

        # ('node:prop', ((buid, prop, valu), ...), {}) -> node fragments

        self._lift_funcs = {}
        self.postLayerInit()

    def setLiftFunc(self, name, func):
        self._lift_funcs[name] = func

    def getLiftFunc(self, name):
        return self._lift_funcs.get(name)

    def lift(self, *opers):
        '''
        Yield results from a list of chained operator tuples.
        '''
        genr = None
        for oper in opers:

            func = self.getLiftFunc(oper[0])
            if func is None:
                raise NoSuchLift(name=oper[0])

            if last is not None:
                oper = (oper[0], last, 
            genr = 


        try:
            for item in func(oper):
                yield item

    def stor(self, opers):
        '''
        Execute a series of storage operations.
        '''

    #def getDataModel(self):
        #'''
        #'''

    #def getRowsBy(self, lift):
        #'''
        #Yield rows by a given lift operation.
        #'''

    #def initConfDefs(self):
        #pass
        #self.addConfDefs()

#class LmdbLayer(Layer):
