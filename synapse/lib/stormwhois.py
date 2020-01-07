
import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

class LibWhois(s_stormtypes.Lib):
    '''
    WHOIS / Registration Data client for Storm.
    '''

    def addLibFuncs(self):
        self.locls.update({
            'guid': self._whoisGuid,
            'parse': self._whoisParse,
        })

    async def _whoisGuid(self, props, form):
        '''
        Provides standard patterns for creating guids for certain inet:whois forms.

        Args:
            props (dict): Dictionary of properties used to create the form
            form (str): The inet:whois form to create the guid for

        Returns:
            (str): A guid from synapse.common

        Raises:
            StormRuntimeError: If form is not supported in this method
        '''

        if form == 'iprec':
            guid_props = (
                props.get('net4'),
                props.get('net6'),
                props.get('asof'),
                props.get('id'),
                props.get('updated'),
            )
        elif form == 'ipcontact':
            guid_props = (
                props.get('contact'),
                props.get('asof'),
                props.get('id'),
                props.get('updated'),
            )
        elif form == 'ipquery':
            guid_props = (
                props.get('time'),
                props.get('fqdn'),
                props.get('url'),
                props.get('ipv4'),
                props.get('ipv6'),
            )
        else:
            raise s_exc.StormRuntimeError(mesg=f'No guid helpers available for inet:whois:{form}.')

        return s_common.guid(sorted(str(i) for i in guid_props if i is not None))

    async def _whoisParse(self, data, rectype):
        # TODO: Consider adding a light parser here
        pass
