
import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibWhois(s_stormtypes.Lib):
    '''
    A Storm Library for providing a consistent way to generate guids for WHOIS / Registration Data in Storm.
    '''
    _storm_locals = (
        {'name': 'guid',
         'desc': '''
        Provides standard patterns for creating guids for certain inet:whois forms.

        Raises:
            StormRuntimeError: If form is not supported in this method.''',
         'type': {'type': 'function', '_funcname': '_whoisGuid',
                  'args': (
                      {'name': 'props', 'type': 'dict', 'desc': 'Dictionary of properties used to create the form.', },
                      {'name': 'form', 'type': 'str', 'desc': 'The ``inet:whois`` form to create the guid for.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'A guid for creating a the node for.', }}},
    )
    _storm_lib_path = ('inet', 'whois')

    def getObjLocals(self):
        return {
             'guid': self._whoisGuid,
         }

    async def _whoisGuid(self, props, form):
        form = await s_stormtypes.tostr(form)
        props = await s_stormtypes.toprim(props)
        if form == 'iprec':
            guid_props = ('net4', 'net6', 'asof', 'id')
        elif form == 'ipcontact':
            guid_props = ('contact', 'asof', 'id', 'updated')
        elif form == 'ipquery':
            guid_props = ('time', 'fqdn', 'url', 'ipv4', 'ipv6')
        else:
            mesg = f'No guid helpers available for this inet:whois form'
            raise s_exc.StormRuntimeError(mesg=mesg, form=form)

        guid_vals = []
        try:
            for prop in guid_props:
                val = props.get(prop)
                if val is not None:
                    guid_vals.append(str(val))
        except AttributeError as e:
            mesg = f'Failed to iterate over props {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if len(guid_vals) <= 1:
            await self.runt.snap.warn(f'Insufficient guid vals identified, using random guid: {guid_vals}')
            return s_common.guid()

        return s_common.guid(sorted(guid_vals))
