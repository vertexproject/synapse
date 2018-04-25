import logging

logger = logging.getLogger(__name__)

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.config as s_config

class Service(s_config.Config):

    def __init__(self, dirn, conf=None):
        s_config.Config.__init__(self, opts=conf)

        #s_telepath.Aware.__init__(self)
        self.dirn = s_common.gendir(dirn)

        self.cmdfuncs = {}

        self.addSvcCmd('ping', self._svcCmdPing)

        self.postSvcInit()

    def _svcCmdPing(self, text):
        yield 'pong: %s' % (text,)

    def getSvcType(self):
        return self.__class__.__name__.lower()

    def addSvcCmd(self, name, func):
        self.cmdfuncs[name] = func

    def runSvcCmd(self, line):
        '''
        Execute a command line, most likely from a remote Cmdr().
        '''
        try:

            name, rest = line.split(None, 1)

            func = self.cmdfuncs.get(name)
            if func is None:
                yield 'NoSuchCmd: %s' % (name,)
                return

            for text in func(rest):
                yield text

        except Exception as e:
            logger.exception()
            logger.warning('cmd error (%s): %e' % (line, e))
            yield '%s error: %s' % (name, e)

    def postSvcInit(self):
        pass

    def getSvcApi(self):
        return self

    #def getSvcRest(self):
        #return None

    #def getSvcAuth(self):
        #return None

    def getSvcDir(self, *path):
        '''
        Return a directory relative to the service directory.

        Args:
            (path): List of path elements to join.

        Returns:
            (str): The joined path relative to the service directory.
        '''
        return s_common.gendir(self.dirn, *path)

    def getSvcPath(self, *path):
        '''
        Return a path relative to the service directory.

        Args:
            (path): List of path elements to join.

        Returns:
            (str): The joined path relative to the service directory.
        '''
        return s_common.genpath(self.dirn, *path)

    #def getTeleApi(self):
        #return self
