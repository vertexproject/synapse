import os

import synapse.dyndeps as s_dyndeps
import synapse.lib.socket as s_socket

from synapse.links.common import *

paramiko = s_dyndeps.getDynMod('paramiko')

class SshRelay(LinkRelay):
    '''
    Implements the SSH link protocol for synapse.

    ssh://[user[:passwd]@]<host>[:port]/<name>?forward=<host:port>[&keyfile=<path>]

    '''
    proto = 'ssh'

    def _reqValidLink(self):

        if paramiko is None:
            raise Exception('paramiko module not installed')

        if self.link[1].get('port') is None:
            self.link[1]['port'] = 22

        host = self.link[1].get('host')
        if host is None:
            raise s_common.PropNotFound('host')

        fwdstr = self.link[1].get('forward')
        if fwdstr is None:
            raise s_common.PropNotFound('forward=<host:port>')

        keyfile = self.link[1].get('keyfile')
        if keyfile is not None and not os.path.isfile(keyfile):
            raise Exception('keyfile not found: %s' % (keyfile,))

        fwdhost, fwdport = fwdstr.split(':')
        try:
            fwdport = int(fwdport, 0)
        except ValueError as e:
            raise Exception('Bad Forward Port: %r' % (fwdport,))

        self.link[1]['fwdhost'] = fwdhost
        self.link[1]['fwdport'] = fwdport

    def _listen(self):
        raise Exception('Synapse Link: SSH Listen Not Supported (yet)')

    def _connect(self):

        host = self.link[1].get('host')
        user = self.link[1].get('user')
        port = self.link[1].get('port')
        passwd = self.link[1].get('passwd')
        keyfile = self.link[1].get('keyfile')
        timeout = self.link[1].get('timeout')

        try:

            ssh = paramiko.client.SSHClient()
            ssh.load_system_host_keys()

            ssh.connect(host, port=port, username=user, password=passwd, key_filename=keyfile, timeout=timeout, allow_agent=True)

            trns = ssh.get_transport()

            fwdhost = self.link[1].get('fwdhost')
            fwdport = self.link[1].get('fwdport')

            s = trns.open_channel('direct-tcpip', (fwdhost, fwdport), ('127.0.0.1', 0))

            return s_socket.Socket(s, ssh=ssh)

        except s_common.sockerrs as e:
            raiseSockError(self.link, e)

        except Exception as e:
            ssh.close()
            raise
