import socket
import struct
import asyncio
import hashlib
import logging

import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.tinfoil as s_tinfoil

logger = logging.getLogger(__name__)

# Env vars ( used directly by both AHA and provisioning services ):
#   SYN_PROVISION_SECRET   - shared secret key material which enables auto-provisioning.
#   SYN_PROVISION_HOST     - optional AHA host/address to unicast discovery to when a
#                            service does not share a broadcast domain with AHA.
#   SYN_PROVISION_FOLLOWER - assume a leader of our service type already exists and
#                            deploy ( clone ) from it rather than booting fresh.

# Well known, organization-local ( RFC 2365 ) multicast group and port used for
# AHA provisioning discovery. The port intentionally matches the default AHA
# provisioning listener port; UDP and TCP do not conflict on the same number.
DEFAULT_MCAST_GROUP = '239.192.0.1'
DEFAULT_MCAST_PORT = 27272

# Keep discovery traffic on the local subnet by default.
MCAST_TTL = 1

# Number of discovery request attempts and the per-attempt response timeout ( seconds ).
MCAST_ATTEMPTS = 3
MCAST_TIMEOUT = 2.0

# Fixed application salt + work factor for deriving an AES-256 key from the
# shared secret. Both ends derive the same key deterministically.
PBKDF2_SALT = b'synapse.provision.discovery.v1'
PBKDF2_ITERATIONS = 310000

# Messages are enveloped as {'type': <msgtype>, 'data': <type-specific-data>}.
# The request/response JSON schemas and validators live in synapse.lib.schemas
# ( reqValidProvRequest / reqValidProvResponse ).

def deriveKey(secret):
    '''
    Derive a 32 byte AES key from shared secret key material.

    Args:
        secret (str): The shared secret.

    Returns:
        bytes: A 32 byte key suitable for use with TinFoilHat.
    '''
    return hashlib.pbkdf2_hmac('sha256', secret.encode(), PBKDF2_SALT, PBKDF2_ITERATIONS, dklen=32)

class _ProvProto(asyncio.DatagramProtocol):

    def __init__(self, cast):
        self.cast = cast

    def datagram_received(self, data, addr):
        self.cast._onDatagram(data, addr)

class ProvCast(s_base.Base):
    '''
    An encrypted datagram transceiver for AHA provisioning discovery.

    Messages are msgpack serialized and encrypted with a shared-secret derived
    AES-GCM key. Datagrams which fail to decrypt ( foreign / corrupt ) are
    silently dropped.

    A listener ( listen=True ) binds the well known discovery port. Multicast group
    membership is NOT taken at construction: the caller controls it with joinGroup()
    and dropGroup(), so a socket which has dropped membership stops receiving group
    addressed requests while unicast to its port still arrives.
    '''
    async def __anit__(self, key, port, group=DEFAULT_MCAST_GROUP, listen=False):

        await s_base.Base.__anit__(self)

        self.tinf = s_tinfoil.TinFoilHat(key)

        self.port = port

        # normalize so a non-canonical but valid form such as 239.192.1 still
        # produces the canonical mreq and send address.
        self.group = socket.inet_ntoa(socket.inet_aton(group))

        # packed form for the mreq in joinGroup()/dropGroup(); send() uses the
        # string form above as the sendto address.
        self.groupbytes = socket.inet_aton(self.group)

        self.joined = False

        self.rxq = asyncio.Queue()

        loop = asyncio.get_running_loop()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MCAST_TTL)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

        if listen:
            # bind the well known group port to receive requests. Group
            # membership is joined later by the caller, via joinGroup().
            sock.bind(('', port))
        else:
            # bind an ephemeral port to send requests and receive unicast replies.
            sock.bind(('', 0))

        self.sock = sock

        self.transport, self.protocol = await loop.create_datagram_endpoint(lambda: _ProvProto(self), sock=sock)

        async def fini():
            # closing the socket drops any group membership and emits the IGMP
            # leave, so dropGroup() here would be redundant.
            self.transport.close()

        self.onfini(fini)

    def joinGroup(self):
        '''
        Join the multicast discovery group ( idempotent ).

        setsockopt on the live fd works even though the socket is owned by an
        asyncio datagram transport.
        '''
        if self.joined:
            return

        # exactly sizeof( ip_mreq ) so BSD/macOS accept it, not the 16 bytes '4sl' packs.
        mreq = struct.pack('=4sI', self.groupbytes, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.joined = True

    def dropGroup(self):
        '''
        Drop the multicast discovery group ( idempotent ).
        '''
        if not self.joined:
            return

        # exactly sizeof( ip_mreq ) so BSD/macOS accept it, not the 16 bytes '4sl' packs.
        mreq = struct.pack('=4sI', self.groupbytes, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
        self.joined = False

    def _onDatagram(self, data, addr):

        # unauthenticated input reaches here, and tinfoil.dec raises ( not merely
        # returns None ) on a non-dict or non-msgpack envelope -- it only returns
        # None for a valid envelope it cannot decrypt -- so this guard is what
        # keeps a garbage datagram from escaping into the event loop.
        try:
            byts = self.tinf.dec(data)
        except Exception:
            logger.warning('Error decrypting provision datagram')
            return

        if byts is None:
            return

        try:
            mesg = s_msgpack.un(byts)
        except Exception:
            logger.exception('Error unpacking provision datagram')
            return

        self.rxq.put_nowait((mesg, addr))

    def send(self, mesg, addr=None):
        '''
        Encrypt and send a message. Defaults to multicasting to the discovery
        group; pass addr=( host, port ) to unicast to a specific address.
        '''
        if addr is None:
            addr = (self.group, self.port)

        self.transport.sendto(self.tinf.enc(s_msgpack.en(mesg)), addr)

    async def recv(self, timeout=None):
        '''
        Wait for the next decrypted ( mesg, addr ) tuple or None on timeout.
        '''
        try:
            return await asyncio.wait_for(self.rxq.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
