import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.schemas as s_schemas
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibInput(s_stormtypes.Lib):
    '''
    A Storm Library for requesting input from the caller of a Storm query.
    '''
    _storm_locals = (
        {'name': 'request',
         'desc': '''
            Request input from the caller of the Storm query and wait for the reply.

            Emits an `input` message containing the `iden`, `type`, and `info` of the request.
            The caller answers by running `$lib.input.send()` with the `iden` from the message.
            Only the requesting user or an admin may reply.

            The request expires after `timeout` seconds, which defaults to 300 (5 minutes)
            and may not exceed 86400 (one day).
            If no reply arrives before then, the request raises a `TimeOut` error.

            The query must have a caller that reads its `input` messages, such as `storm()`
            without a message filter or the Storm CLI. The `view.exec` and `runas` commands
            forward `input` messages from the query they run. A request made where nothing
            reads the `input` message, such as from `callStorm()`, a cron job, or a trigger,
            waits until it expires. In a synchronous trigger, the wait also blocks the edit
            which fired the trigger.

            The only supported type is `text`, which requests a line of text. Its `info` must
            contain a non-empty `prompt` string, which may be markdown, and no other keys.
            The reply is a dictionary in the form `{"text": <str>}`.

            Example:
                Ask the caller for their name::

                    $reply = $lib.input.request(text, ({"prompt": "What is your **name**?"}))
                    $lib.print(`Hello {$reply.text}`)
         ''',
         'type': {'type': 'function', '_funcname': '_methRequest',
                  'args': (
                      {'name': 'type', 'type': 'str', 'desc': 'The type of input to request.'},
                      {'name': 'info', 'type': 'dict', 'desc': 'The type specific details of the request.'},
                      {'name': 'timeout', 'type': 'int', 'default': s_const.STORM_INPUT_TIMEOUT,
                       'desc': 'The number of seconds to wait for a reply before the request expires, up to 86400.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The reply sent by `$lib.input.send()`.'}}},
        {'name': 'send',
         'desc': '''
            Send a reply to a pending input request.

            The reply must match the schema for the type of the request. For a `text`
            request, the reply is a dictionary in the form `{"text": <str>}`.

            Example:
                Reply to a text input request::

                    $lib.input.send($iden, ({"text": "visi"}))
         ''',
         'type': {'type': 'function', '_funcname': '_methSend',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden from the `input` message.'},
                      {'name': 'info', 'type': 'dict', 'desc': 'The reply to the input request.'},
                  ),
                  'returns': {'type': 'null'}}},
    )
    _storm_lib_path = ('input',)

    def getObjLocals(self):
        return {
            'send': self._methSend,
            'request': self._methRequest,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRequest(self, type, info, timeout=s_const.STORM_INPUT_TIMEOUT):

        type = await s_stormtypes.tostr(type)
        info = await s_stormtypes.toprim(info)
        timeout = await s_stormtypes.toint(timeout, noneok=True)

        if timeout is None or timeout <= 0:
            mesg = f'The timeout must be a positive number of seconds, not {timeout}.'
            raise s_exc.BadArg(mesg=mesg, timeout=timeout)

        validator = s_schemas.stormInputValidators.get(type)
        if validator is None:
            types = ', '.join(sorted(s_schemas.stormInputValidators))
            mesg = f'Unsupported Storm input type: {type}. Supported types: {types}'
            raise s_exc.BadArg(mesg=mesg, type=type)

        validator(info)

        core = self.runt.view.core

        iden = s_common.guid()
        await core.addStormInput(iden, self.runt.user.iden, type, timeout=timeout)

        try:
            await self.runt.bus.fire('input', iden=iden, type=type, info=info)
        except BaseException:
            await core.delStormInput(iden)
            raise

        return await core.waitStormInput(iden)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSend(self, iden, info):

        iden = await s_stormtypes.tostr(iden)
        info = await s_stormtypes.toprim(info)
        s_json.reqjsonsafe(info)

        await self.runt.view.core.sendStormInput(iden, self.runt.user.iden, info)
