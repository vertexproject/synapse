import socket
import tempfile

import synapse.lib.socket as s_socket

from synapse.common import *
from synapse.links.common import *

class LocalRelay(LinkRelay):
    '''
    Implements the PF_UNIX/PF_LOCAL protocol for synapse.
    ( and named pipes on windows platforms )

    local://<name>/

    '''
    proto = 'local'

    def _reqValidLink(self):
        # we use the "host" part as the local name
        host = self.link[1].get('host')
        if not host:
            raise BadUrl('local://<name>/<path>')

    def _getTempPath(self):
        host = self.link[1].get('host')
        # use the host part to generate a local path
        tdir = tempfile.gettempdir()
        return os.path.join(tdir,host)

    def _listen(self):

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        path = self._getTempPath()
        if os.path.exists(path):
            os.unlink(path)

        s.bind(path)
        s.listen(120)

        return s_socket.Socket(s, listen=True)

    def _connect(self):
        path = self._getTempPath()
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(path)
        return s_socket.Socket(s)

