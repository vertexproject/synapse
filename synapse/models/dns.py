import synapse.exc as s_exc

import synapse.lib.types as s_types

class DnsName(s_types.Str):

    def postTypeInit(self):

        s_types.Str.postTypeInit(self)
        self.inarpa = '.in-addr.arpa'
        self.inarpa6 = '.ip6.arpa'

        self.iptype = self.modl.type('inet:ip')
        self.fqdntype = self.modl.type('inet:fqdn')

        self.setNormFunc(str, self._normPyStr)

    async def _normPyStr(self, valu, view=None):
        # Backwards compatible
        norm = valu.lower()
        norm = norm.strip()  # type: str
        # Break out fqdn / ipv4 / ipv6 subs :D
        subs = {}
        # ipv4
        if norm.isnumeric():
            # do-nothing for integer only strs
            pass
        elif norm.endswith(self.inarpa):
            # Strip, reverse, check if ipv4
            temp = norm[:-len(self.inarpa)]
            temp = '.'.join(temp.split('.')[::-1])
            try:
                ipv4norm, info = await self.iptype.norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipv4norm, info)
        elif norm.endswith(self.inarpa6):
            parts = [c for c in norm[:-len(self.inarpa6)][::-1] if c != '.']
            try:
                if len(parts) != 32:
                    raise s_exc.BadTypeValu(mesg='Invalid number of ipv6 parts')
                temp = (6, int(''.join(parts), 16))
                ipv6norm, info = await self.iptype.norm(temp)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipv6norm, info)
        else:
            # Try fallbacks to parse out possible ipv4/ipv6 garbage queries
            try:
                ipnorm, info = await self.iptype.norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['ip'] = (self.iptype.typehash, ipnorm, info)
                return norm, {'subs': subs}

            # Lastly, try give the norm'd valu a shot as an inet:fqdn
            try:
                fqdnnorm, info = await self.fqdntype.norm(norm)
            except s_exc.BadTypeValu as e:
                pass
            else:
                subs['fqdn'] = (self.fqdntype.typehash, fqdnnorm, info)

        return norm, {'subs': subs}
