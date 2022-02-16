import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes


logger = logging.getLogger(__name__)

stormlogger = logging.getLogger('synapse.storm.log')

@s_stormtypes.registry.registerLib
class LoggerLib(s_stormtypes.Lib):
    '''
    A Storm library which implements server side logging. These messages are logged to the
    ``synapse.storm.log`` logger.
    '''
    _storm_locals = (
        {'name': 'debug', 'desc': '''
        Log a message to the Cortex at the debug log level.

        Notes:
            This requires the ``storm.lib.log.debug`` permission to use.

        Examples:
            Log a debug message::

                $lib.log.debug('I am a debug message!')

            Log a debug message with extra information::

                $lib.log.debug('Extra information included here.', extra=({"key": $valu}))''',
         'type': {'type': 'function', '_funcname': '_logDebug',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'The message to log.'},
                      {'name': 'extra', 'type': 'dict', 'desc': 'Extra key / value pairs to include when structured '
                                                                'logging is enabled on the Cortex.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null'},
                  }
         },
        {'name': 'info', 'desc': '''
            Log a message to the Cortex at the info log level.

            Notes:
                This requires the ``storm.lib.log.info`` permission to use.

            Examples:
                Log an info message::

                    $lib.log.info('I am a info message!')

                Log an info message with extra information::

                    $lib.log.info('Extra information included here.', extra=({"key": $valu}))''',
         'type': {'type': 'function', '_funcname': '_logInfo',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'The message to log.'},
                      {'name': 'extra', 'type': 'dict', 'desc': 'Extra key / value pairs to include when structured '
                                                                'logging is enabled on the Cortex.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null'},
                  }
         },
        {'name': 'warning', 'desc': '''
            Log a message to the Cortex at the warning log level.

            Notes:
                This requires the ``storm.lib.log.warning`` permission to use.

            Examples:
                Log a warning message::

                    $lib.log.warning('I am a warning message!')

                Log a warning message with extra information::

                    $lib.log.warning('Extra information included here.', extra=({"key": $valu}))''',
         'type': {'type': 'function', '_funcname': '_logDebug',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'The message to log.'},
                      {'name': 'extra', 'type': 'dict', 'desc': 'Extra key / value pairs to include when structured '
                                                                'logging is enabled on the Cortex.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null'},
                  }
         },
        {'name': 'error', 'desc': '''
            Log a message to the Cortex at the error log level.

            Notes:
                This requires the ``storm.lib.log.error`` permission to use.

            Examples:
                Log an error message::

                    $lib.log.error('I am a error message!')

                Log an error message with extra information::

                    $lib.log.error('Extra information included here.', extra=({"key": $valu}))''',
         'type': {'type': 'function', '_funcname': '_logDebug',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'The message to log.'},
                      {'name': 'extra', 'type': 'dict', 'desc': 'Extra key / value pairs to include when structured '
                                                                'logging is enabled on the Cortex.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null'},
                  }
         },
    )

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
            mesg = f'extra provided to log call must be a dictionary compatible type. Got {extra.__class__.__name__} ' \
                   f'instead.'
            raise s_exc.BadArg(mesg=mesg, arg='extra')
        extra = {'synapse': extra}
        return extra

    @s_stormtypes.stormfunc(readonly=True)
    async def _logDebug(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'debug'))
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.debug(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logInfo(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'info'))
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.info(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logWarning(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'warning'))
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.warning(mesg, extra=extra)
        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _logError(self, mesg, extra=None):
        self.runt.confirm(('storm', 'lib', 'log', 'error'))
        mesg = await s_stormtypes.tostr(mesg)
        extra = await self._getExtra(extra)
        stormlogger.error(mesg, extra=extra)
        return None
