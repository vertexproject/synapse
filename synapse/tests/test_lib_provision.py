import socket
import unittest.mock as mock

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

        async with await s_provision.ProvCast.anit(key, port, group=group, listen=True) as srv:

            # a listener must join the group to receive group traffic; do it here.
            srv.joinGroup()

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

                # a request addressed directly to the listener's port also arrives.
                cli.send({'type': 'service', 'data': {'type': 'axon'}}, ('127.0.0.1', port))

                item = await srv.recv(timeout=10)
                self.nn(item)
                mesg, addr = item
                self.eq(mesg['data'].get('type'), 'axon')

                # a datagram encrypted with a different key is silently dropped
                otherkey = s_provision.deriveKey('other')
                othertinf = s_tinfoil.TinFoilHat(otherkey)
                srv.sock.sendto(othertinf.enc(s_common.buid()), (group, port))
                self.none(await srv.recv(timeout=0.5))

                # a corrupt ( non-msgpack ) but validly encrypted datagram is dropped
                srv.sock.sendto(srv.tinf.enc(b'\xff\xff\xff'), (group, port))
                self.none(await srv.recv(timeout=0.5))

    async def test_provision_join_drop(self):

        # membership is controlled by the caller: joinGroup / dropGroup toggle the
        # socket's group membership and are idempotent.
        key = s_provision.deriveKey('sekret')
        port = freeport()
        group = '239.192.9.7'

        async with await s_provision.ProvCast.anit(key, port, group=group, listen=True) as srv:

            self.false(srv.joined)

            calls = []
            realsetsockopt = socket.socket.setsockopt

            def track(self, level, optname, *args):
                if optname in (socket.IP_ADD_MEMBERSHIP, socket.IP_DROP_MEMBERSHIP):
                    calls.append(optname)
                return realsetsockopt(self, level, optname, *args)

            with mock.patch.object(socket.socket, 'setsockopt', track):

                srv.joinGroup()
                self.true(srv.joined)

                # idempotent: a second join issues no further setsockopt
                srv.joinGroup()

                srv.dropGroup()
                self.false(srv.joined)

                # idempotent: a second drop issues no further setsockopt
                srv.dropGroup()

            self.eq(calls, [socket.IP_ADD_MEMBERSHIP, socket.IP_DROP_MEMBERSHIP])

    async def test_provision_transceiver_hostile(self):

        # the datagram is unauthenticated at the point it is decrypted, so a
        # malformed envelope must be dropped rather than escape the reader.
        key = s_provision.deriveKey('sekret')
        port = freeport()
        group = '239.192.9.4'

        async with await s_provision.ProvCast.anit(key, port, group=group, listen=True) as srv:

            hostile = (
                b'\xc0\xc0',          # not msgpack
                b'\x01',              # a bare int
                b'\x92\x01\x02',      # a bare list
                b'\x82\xa2iv',        # a truncated map
                b'',                  # empty
                b'\xd4\x7f\x00',      # an unknown msgpack ext
            )

            with self.getLoggerStream('synapse.lib.provision') as stream:

                for byts in hostile:
                    srv._onDatagram(byts, ('127.0.0.1', 1234))

                self.true(srv.rxq.empty())

            stream.seek(0)
            self.isin('Error decrypting provision datagram', stream.read())

            # and the listener still serves a legitimate request afterwards
            async with await s_provision.ProvCast.anit(key, port, group=group) as cli:

                cli.send({'type': 'service', 'data': {'type': 'cortex'}}, ('127.0.0.1', port))

                item = await srv.recv(timeout=10)
                self.nn(item)
                self.eq('cortex', item[0]['data'].get('type'))

    async def test_provision_group_normalized(self):

        # a valid but non-canonical group is normalized to the canonical form
        # used to build the membership mreq and the send address.
        key = s_provision.deriveKey('sekret')
        port = freeport()

        self.eq(socket.inet_aton('239.192.9.6'), socket.inet_aton('239.192.2310'))

        async with await s_provision.ProvCast.anit(key, port, group='239.192.2310', listen=True) as srv:
            self.eq('239.192.9.6', srv.group)
