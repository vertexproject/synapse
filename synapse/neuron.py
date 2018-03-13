import os
import logging

import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

defport = 65521 # the default neuron port

class Neuron(s_cell.Cell):
    '''
    A neuron node is the "master cell" for a neuron cluster.
    '''
    def postCell(self):

        self.cells = self.getCellDict('cells')

        path = self._path('admin.auth')

        if not os.path.exists(path):
            auth = self.genCellAuth('admin')
            s_msgpack.dumpfile(auth, path)

    def handlers(self):
        return {
            'cell:get': self._onCellGet,
            'cell:reg': self._onCellReg,
            'cell:init': self._onCellInit,
            'cell:list': self._onCellList,
        }

    def _genCellName(self, name):
        host = self.getConfOpt('host')
        return '%s@%s' % (name, host)

    def _onCellGet(self, chan, mesg):
        name = mesg[1].get('name')
        info = self.cells.get(name)
        chan.txfini((True, info))

    @s_glob.inpool
    def _onCellReg(self, chan, mesg):

        peer = chan.getLinkProp('cell:peer')
        if peer is None:
            enfo = ('NoCellPeer', {})
            chan.tx((False, enfo))
            return

        info = mesg[1]

        self.cells.set(peer, info)
        self.fire('cell:reg', name=peer, info=info)

        logger.info('cell registered: %s %r', peer, info)

        chan.txfini((True, True))
        return

    def _onCellList(self, chan, mesg):
        cells = self.cells.items()
        chan.tx((True, cells))

    @s_glob.inpool
    def _onCellInit(self, chan, mesg):

        # for now, only let admin provision...
        root = 'admin@%s' % (self.getConfOpt('host'),)

        peer = chan.getLinkProp('cell:peer')
        if peer != root:
            logger.warning('cell:init not allowed for: %s' % (peer,))
            return chan.tx((False, None))

        name = mesg[1].get('name').split('@')[0]
        auth = self.genCellAuth(name)
        chan.tx((True, auth))

    def getCellInfo(self, name):
        '''
        Return the info dict for a given cell by name.
        '''
        return self.cells.get(name)

    def getCellList(self):
        '''
        Return a list of (name, info) tuples for the known cells.
        '''
        return self.cells.items()

    def genCellAuth(self, name):
        '''
        Generate or retrieve an auth/provision blob for a cell.

        Args:
            name (str): The unqualified cell name (ex. "axon00")
        '''
        host = self.getConfOpt('host')
        full = '%s@%s' % (name, host)

        auth = self.vault.genUserAuth(full)

        auth[1]['neuron'] = self.getCellAddr()

        return auth

    def initConfDefs(self):
        s_cell.Cell.initConfDefs(self)
        self.addConfDefs((
            ('port', {'defval': defport, 'req': 1,
                'doc': 'The TCP port the Neuron binds to (defaults to %d)' % defport}),
        ))

class NeuronClient:

    def __init__(self, sess):
        self.sess = sess

    def genCellAuth(self, name, timeout=None):
        '''
        Generate a new cell auth file.
        '''
        mesg = ('cell:init', {'name': name})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)
