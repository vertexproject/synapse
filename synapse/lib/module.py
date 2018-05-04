import os
import datetime

import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

class CoreModule:
    '''
    '''

    confdefs = ()

    def __init__(self, core):

        # TODO: get config from dir
        #self.conf = s_common.config(conf, self.confdefs)

        self.core = core        # type: synapse.cortex.Cortex
        self.model = core.model # type: synapse.datamodel.Model

    def getModelDefs(self):
        return ()

    def getModelRevs(self):
        return ()

    def getModName(self):
        '''
        Return the name of this module.

        Returns:
            (str): The module name.
        '''
        return self._mod_name

    def getModIden(self):
        '''
        Return the GUID which identifies this module.

        Returns:
            (str):  The GUID string.
        '''
        return self._mod_iden

    def getModPath(self, *paths):
        '''
        Construct a path relative to this module's working directory.

        Args:
            (*paths): A list of path strings

        Returns:
            (str): The full path (or None if no cortex dir is configured).
        '''
        name = self.getModName()

        dirn = self.core.getCorePath('mods', name)
        if dirn is None:
            return None

        if not os.path.isdir(dirn):
            os.makedirs(dirn, mode=0o700)

        return self.core.getCorePath('mods', name, *paths)

    def initCoreModule(self):
        '''
        Module implementers may over-ride this method to initialize the
        module during initial construction.  Any exception raised within
        this method will be raised from the constructor and mark the module
        as failed.

        Args:

        Returns:
            None
        '''
        pass
