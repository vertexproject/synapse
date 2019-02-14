import os

import synapse.common as s_common

class CoreModule:
    '''
    '''

    confdefs = ()
    mod_name = None

    def __init__(self, core):

        self.core = core        # type: synapse.cortex.Cortex
        self.model = core.model # type: synapse.datamodel.Model

        # Avoid getModPath / getConfPath during __init__ since these APIs
        # will create directories. We do not need that behavior by default.
        self._modpath = os.path.join(self.core.dirn,
                                     'mods',
                                     self.getModName())
        self._confpath = os.path.join(self._modpath, 'conf.yaml')
        conf = {}
        if os.path.isfile(self._confpath):
            conf = s_common.yamlload(self._confpath)
        self.conf = s_common.config(conf, self.confdefs)

    def getStormCmds(self):  # pragma: no cover
        '''
        Module implementers may over-ride this to provide a list of Storm
        commands which will be loaded into the Cortex.

        Returns:
            list: A list of Storm Command classes (not instances).
        '''
        return ()

    def getModelDefs(self):
        return ()

    def getModelRevs(self):
        return ()

    def getConfPath(self):
        '''
        Get the path to the module specific config file (conf.yaml).

        Notes:
            This creates the parent directory for the conf.yaml file if it does
            not exist. This API exists to allow a implementor to get the conf
            path during initCoreModule and drop a example config if needed.
            One use case of that is for missing configuration values, an
            example config can be written to the file and a exception raised.

        Returns:
            str: Path to where the conf file is located at.
        '''
        self.getModDir()
        return self._confpath

    def getModDir(self):
        '''
        Get the path to the module specific directory.

        Notes:
            This creates the directory if it did not previously exist.

        Returns:
            str: The filepath to the module specific directory.
        '''
        return s_common.gendir(self._modpath)

    def getModName(self):
        '''
        Return the lowercased name of this module.

        Notes:
            This pulls the ``mod_name`` attribute on the class. This allows
            an implementer to set a arbitrary name for the module.  If this
            attribute is not set, it defaults to ``self.__class__.__name__``.

        Returns:
            (str): The module name.
        '''
        ret = self.mod_name
        if ret is None:
            ret = self.__class__.__name__
        return ret.lower()

    def getModPath(self, *paths):
        '''
        Construct a path relative to this module's working directory.

        Args:
            (*paths): A list of path strings

        Notes:
            This creates the module specific directory if it does not exist.

        Returns:
            (str): The full path (or None if no cortex dir is configured).
        '''
        dirn = self.getModDir()
        return s_common.genpath(dirn, *paths)

    async def initCoreModule(self):
        '''
        Module implementers may over-ride this method to initialize the
        module during initial construction.  Any exception raised within
        this method will be raised from the constructor and mark the module
        as failed.

        Notes:
            This is called for modules after getModelDefs() and getStormCmds()
            has been called, in order to allow for model loading and storm
            command loading prior to code execution offered by initCoreModule.

        Returns:
            None
        '''
        pass
