import socket

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.schemas as s_schemas
import synapse.lib.provision as s_provision
import synapse.lib.crypto.tinfoil as s_tinfoil

import synapse.tests.utils as s_test

def freeport():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

class ProvisionTest(s_test.SynTest):

    def test_provision_derivekey(self):

        # the same secret derives the same 32 byte key deterministically.
        k0 = s_provision.deriveKey('sekret')
        k1 = s_provision.deriveKey('sekret')

        self.eq(k0, k1)
        self.len(32, k0)

        # different secrets derive different keys.
        self.ne(k0, s_provision.deriveKey('other'))

    def test_provision_schemas(self):

        s_schemas.reqValidProvRequest({'type': 'service', 'data': {'type': 'cortex'}})

        # the response data is an ( ok, data ) retn tuple and is unconstrained
        s_schemas.reqValidProvResponse({'type': 'retn', 'data': (True, {'url': 'ssl://a/b'})})
        s_schemas.reqValidProvResponse({'type': 'retn', 'data': (False, ('BadArg', {'mesg': 'boom'}))})

        # unexpected data field
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidProvRequest({'type': 'service', 'data': {'type': 'cortex', 'provinfo': {}}})

        # missing service type
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidProvRequest({'type': 'service', 'data': {}})

        # missing data
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidProvResponse({'type': 'retn'})

        # wrong message type
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidProvResponse({'type': 'service', 'data': None})

    async def test_provision_transceiver(self):

        key = s_provision.deriveKey('sekret')
        port = freeport()
        group = '239.192.9.1'

        async with await s_provision.ProvCast.anit(key, port, group=group, join=True) as srv:
            async with await s_provision.ProvCast.anit(key, port, group=group) as cli:

                cli.send({'type': 'service', 'data': {'type': 'cortex'}})

                item = await srv.recv(timeout=10)
                self.nn(item)

                mesg, addr = item
                self.eq(mesg['data'].get('type'), 'cortex')

                # unicast the reply back to the requester
                srv.send({'type': 'retn', 'data': (True, {'url': 'ssl://a/b'})}, addr)

                item = await cli.recv(timeout=10)
                self.nn(item)
                self.eq(s_common.result(item[0]['data']).get('url'), 'ssl://a/b')

                # a datagram encrypted with a different key is silently dropped
                otherkey = s_provision.deriveKey('other')
                othertinf = s_tinfoil.TinFoilHat(otherkey)
                srv.transport.sendto(othertinf.enc(s_common.buid()), (group, port))
                self.none(await srv.recv(timeout=0.5))

                # a corrupt ( non-msgpack ) but validly encrypted datagram is dropped
                srv.transport.sendto(srv.tinf.enc(b'\xff\xff\xff'), (group, port))
                self.none(await srv.recv(timeout=0.5))
