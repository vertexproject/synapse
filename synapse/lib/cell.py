import os
import yaml
import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

logger = logging.getLogger(__name__)

'''
Base classes for the synapse "cell" microservice architecture.
'''
class CellApi:

    def __init__(self, cell, link):
        self.cell = cell
        self.link = link

    def runCellCmd(self, name, line):
        '''
        Execute a cell cmdline
        '''
        func = self.cell.cmds.get(name)
        if func is None:
            raise s_exc.NoSuchName(name=name, mesg='no such cell command')

defconf = '''
# auth:en: False
# auth:url: null

'''

class Cell(s_eventbus.EventBus, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.
    '''
    cellapi = CellApi

    celltype = 'cell'   # this should match synapse.cells

    # mirror these if you want the cell base features...
    confdefs = (
        ('auth:en', {'defval': False,
            'doc': 'Set to True to enable auth for this cortex.'}),
        ('auth:url', {'defval': None,
            'doc': 'Set to a telepath URL to use a remote Auth Cell.'}),
        ('auth:admin', {'defval': None,
            'doc': 'Set to <user>:<passwd> (local only) to bootstrap an admin.'}),
    )

    def __init__(self, dirn):

        s_eventbus.EventBus.__init__(self)

        self.dirn = s_common.gendir(dirn)

        self.auth = None

        conf = self._loadCellYaml()
        self.conf = s_common.config(conf, self.confdefs)

        self.cmds = {}

    def _loadCellYaml(self):

        path = os.path.join(self.dirn, 'cell.yaml')

        if os.path.isfile(path):
            with open(path, 'rb') as fd:
                text = fd.read().decode('utf8')
                return yaml.load(text)

        logger.warning('config not found: %r' % (path,))

        return {}

    #@endpoint

    @staticmethod
    def deploy(dirn):
        '''
        Initialize default Cell in the given dir.
        '''
        dirn = s_common.gendir(dirn)

    def getTeleApi(self, link, mesg):

        # handle unified cell auth here
        #if self.auth is not None:
            #await

        return self.cellapi(self, link)

    def initCellAuth(self):

        valu = self.conf.get('auth:en')
        if not valu:
            return

        url = self.conf.get('auth:url')
        if url is not None:
            self.auth = s_telepath.openurl(url)
            return

        # setup local auth

        dirn = s_common.gendir(self.dirn, 'auth')

        self.auth = s_auth.Auth(dirn)

        # let them hard code an initial admin user:passwd
        admin = self.conf.get('auth:admin')
        if admin is not None:
            name, passwd = admin.split(':', 1)

            user = self.auth.getUser(name)
            if user is None:
                user = self.auth.addUser(name)

            user.setAdmin(True)
            user.setPasswd(passwd)

    def addCellCmd(self, name, func):
        '''
        Add a Cmdr() command to the cell.
        '''
        self.cmds[name] = func

    #def getCellDir(
    #def getCellPath(

    #def runCellCmd(self, name, line):
        ##func = self.cmds.get(name)
        #if func is None:
            ##raise s_exc.NoSuchName(name=name, mesg='no such cell command')

        #return func(line)
