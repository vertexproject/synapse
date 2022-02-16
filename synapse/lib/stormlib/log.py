import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes


logger = logging.getLogger(__name__)

stormlogger = logging.getLogger('synapse.storm.log')

@s_stormtypes.registry.registerLib
class LoggerLib(s_stormtypes.Lib):
    '''
    A Storm library which implements server side logging.
    '''
    # _storm_locals = (
    #     {'name': 'info'}
    # )

    _storm_lib_path = ('log',)

    def getObjLocals(self):
        return {
            'info': self._logInfo,
            'debug': self._logDebug,
            'error': self._logError,
            'warning': self._logWarning,
        }

    async def _getExtra(self, extra=None):
        if extra is None:
            return extra
        extra = await s_stormtypes.toprim(extra)
        if extra and not isinstance(extra, dict):
            mesg = f'extra provided to log call must be a dictionary compatible type. Got {type(extra)}.'
            raise s_exc.StormRuntimeError(mesg=mesg)
        extra = {'synapse': extra}
        return extra

    @s_stormtypes.stormfunc(readonly=True)
    async def _logDebug(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'debug'), gateiden=None)
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.debug(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logInfo(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'info'), gateiden=None)
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.info(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logWarning(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'warning'), gateiden=None)
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.warning(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logError(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'error'), gateiden=None)
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.error(mesg, extra=extra)
        return None
