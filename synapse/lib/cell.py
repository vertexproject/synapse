import os
import ssl
import time
import shutil
import socket
import asyncio
import logging
import tarfile
import argparse
import datetime
import platform
import functools
import contextlib
import multiprocessing

import tornado.web as t_web

import synapse.exc as s_exc

import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.nexus as s_nexus
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.health as s_health
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.httpapi as s_httpapi
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.version as s_version
import synapse.lib.hiveauth as s_hiveauth
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.thisplat as s_thisplat

import synapse.tools.backup as s_t_backup

logger = logging.getLogger(__name__)

SLAB_MAP_SIZE = 128 * s_const.mebibyte

'''
Base classes for the synapse "cell" microservice architecture.
'''

def adminapi(log=False):
    '''
    Decorator for CellApi (and subclasses) for requiring a method to be called only by an admin user.

    Args:
        log (bool): If set to True, log the user, function and arguments.
    '''

    def decrfunc(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            if args[0].user is not None and not args[0].user.isAdmin():
                raise s_exc.AuthDeny(mesg='User is not an admin.',
                                     user=args[0].user.name)
            if log:
                logger.info('Executing [%s] as [%s] with args [%s][%s]',
                            func.__qualname__, args[0].user.name, args[1:], kwargs)

            return func(*args, **kwargs)

        wrapped.__syn_wrapped__ = 'adminapi'

        return wrapped

    return decrfunc

async def _doIterBackup(path, chunksize=1024):
    '''
    Create tarball and stream bytes.

    Args:
        path (str): Path to the backup.

    Yields:
        (bytes): File bytes
    '''
    output_filename = path + '.tar.gz'
    link0, file1 = await s_link.linkfile()

    def dowrite(fd):
        with tarfile.open(output_filename, 'w|gz', fileobj=fd) as tar:
            tar.add(path, arcname=os.path.basename(path))
        fd.close()

    coro = s_coro.executor(dowrite, file1)

    while True:
        byts = await link0.recv(chunksize)
        if not byts:
            break
        yield byts

    await coro
    await link0.fini()

async def _iterBackupWork(path, linkinfo):
    '''
    Inner setup for backup streaming.

    Args:
        path (str): Path to the backup.
        linkinfo(dict): Link info dictionary.

    Returns:
        None: Returns None.
    '''
    logger.info(f'Getting backup streaming link for [{path}].')
    link = await s_link.fromspawn(linkinfo)

    await s_daemon.t2call(link, _doIterBackup, (path,), {})
    await link.fini()

    logger.info(f'Backup streaming for [{path}] completed.')

def _iterBackupProc(path, linkinfo):
    '''
    Multiprocessing target for streaming a backup.
    '''
    # This logging call is okay to run since we're executing in
    # our own process space and no logging has been configured.
    s_common.setlogging(logger, **linkinfo.get('logconf'))

    logger.info(f'Backup streaming process for [{path}] starting.')
    asyncio.run(_iterBackupWork(path, linkinfo))

class CellApi(s_base.Base):

    async def __anit__(self, cell, link, user):
        await s_base.Base.__anit__(self)
        self.cell = cell
        self.link = link
        assert user
        self.user = user
        self.sess = self.link.get('sess')  # type: s_daemon.Sess
        self.sess.user = user
        await self.initCellApi()

    async def initCellApi(self):
        pass

    async def allowed(self, perm, default=None):
        '''
        Check if the user has the requested permission.

        Args:
            perm: permission path components to check
            default: Value returned if no value stored

        Examples:

            Form a path and check the permission from a remote proxy::

                perm = ('node', 'add', 'inet:ipv4')
                allowed = await prox.allowed(perm)
                if allowed:
                    dostuff()

        Returns:
            Optional[bool]: True if the user has permission, False if explicitly denied, None if no entry
        '''
        return self.user.allowed(perm, default=default)

    async def _reqUserAllowed(self, perm):
        '''
        Helper method that subclasses can use for user permission checking.

        Args:
            perm: permission path components to check

        Notes:
            This can be used to require a permission; and will throw an exception if the permission is not allowed.

        Examples:

            Implement an API that requires a user to have a specific permission in order to execute it::

                async def makeWidget(self, wvalu, wtype):
                    # This will throw if the user doesn't have the appropriate widget permission
                    await self._reqUserAllowed(('widget', wtype))
                    return await self.cell.makeWidget((wvalu, wtype))

        Returns:
            None: This API does not return anything. It only throws an exception on failure.

        Raises:
            s_exc.AuthDeny: If the permission is not allowed.

        '''
        if not await self.allowed(perm):
            perm = '.'.join(perm)
            mesg = f'User must have permission {perm}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.user.name)

    def getCellType(self):
        return self.cell.getCellType()

    def getCellIden(self):
        return self.cell.getCellIden()

    async def isCellActive(self):
        '''
        Returns True if the cell is an active/leader cell.
        '''
        return await self.cell.isCellActive()

    @adminapi()
    def getNexsIndx(self):
        return self.cell.getNexsIndx()

    @adminapi(log=True)
    async def cullNexsLog(self, offs):
        '''
        Remove Nexus log entries up to (and including) the given offset.

        Note:
            If there are consumers of this cell's nexus log they must
            be caught up to at least the offs argument before culling.

            Only rotated logs where the last index is less than the
            provided offset will be removed from disk.

        Args:
            offs (int): The offset to remove entries up to.

        Returns:
            bool: Whether the cull was executed
        '''
        return await self.cell.cullNexsLog(offs)

    @adminapi(log=True)
    async def rotateNexsLog(self):
        '''
        Rotate the Nexus log at the current offset.

        Returns:
            int: The starting index of the active Nexus log
        '''
        return await self.cell.rotateNexsLog()

    @adminapi(log=True)
    async def trimNexsLog(self, consumers=None, timeout=60):
        '''
        Rotate and cull the Nexus log (and those of any consumers) at the current offset.

        Note:
            If the consumers argument is provided they will first be checked
            if online before rotating and raise otherwise.
            After rotation, all consumers must catch-up to the offset to cull
            at before executing the cull, and will raise otherwise.

        Args:
            consumers (list or None): Optional list of telepath URLs for downstream Nexus log consumers.
            timeout (int): Time in seconds to wait for downstream consumers to be caught up.

        Returns:
            int: The offset that the Nexus log was culled up to and including.
        '''
        return await self.cell.trimNexsLog(consumers=consumers, timeout=timeout)

    @adminapi()
    async def waitNexsOffs(self, offs, timeout=None):
        '''
        Wait for the Nexus log to write an offset.

        Args:
            offs (int): The offset to wait for.
            timeout (int or None): An optional timeout in seconds.

        Returns:
            bool: True if the offset was written, False if it timed out.
        '''
        return await self.cell.waitNexsOffs(offs, timeout=timeout)

    @adminapi()
    async def promote(self):
        return await self.cell.promote()

    def getCellUser(self):
        return self.user.pack()

    async def getCellInfo(self):
        return await self.cell.getCellInfo()

    @adminapi()
    async def getSystemInfo(self):
        '''
        Get info about the system in which the cell is running

        Returns:
            A dictionary with the following keys.  All size values are in bytes:
                - volsize - Volume where cell is running total space
                - volfree - Volume where cell is running free space
                - backupvolsize - Backup directory volume total space
                - backupvolfree - Backup directory volume free space
                - celluptime - Cell uptime in milliseconds
                - cellrealdisk - Cell's use of disk, equivalent to du
                - cellapprdisk - Cell's apparent use of disk, equivalent to ls -l
                - osversion - OS version/architecture
                - pyversion - Python version
                - totalmem - Total memory in the system
                - availmem - Available memory in the system
        '''
        return await self.cell.getSystemInfo()

    def setCellUser(self, iden):
        '''
        Switch to another user (admin only).

        This API allows remote admin/service accounts
        to impersonate a user.  Used mostly by services
        that manage their own authentication/sessions.
        '''
        if not self.user.isAdmin():
            mesg = 'setCellUser() caller must be admin.'
            raise s_exc.AuthDeny(mesg=mesg)

        user = self.cell.auth.user(iden)
        if user is None:
            raise s_exc.NoSuchUser(iden=iden)

        self.user = user
        self.link.get('sess').user = user
        return True

    async def ps(self):
        return await self.cell.ps(self.user)

    async def kill(self, iden):
        return await self.cell.kill(self.user, iden)

    @adminapi(log=True)
    async def addUser(self, name, passwd=None, email=None, iden=None):
        return await self.cell.addUser(name, passwd=passwd, email=email, iden=iden)

    @adminapi(log=True)
    async def delUser(self, iden):
        return await self.cell.delUser(iden)

    @adminapi(log=True)
    async def addRole(self, name):
        return await self.cell.addRole(name)

    @adminapi(log=True)
    async def delRole(self, iden):
        return await self.cell.delRole(iden)

    @adminapi()
    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.cell.dyncall(iden, todo, gatekeys=gatekeys)

    @adminapi()
    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.cell.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    @adminapi()
    async def issue(self, nexsiden: str, event: str, args, kwargs, meta=None):
        '''
        Note:  this swallows exceptions and return values.  It is expected that the nexus _followerLoop would be the
        return path
        '''
        try:
            await self.cell.nexsroot.issue(nexsiden, event, args, kwargs, meta)
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise
        except Exception:
            pass

    @adminapi(log=True)
    async def delAuthUser(self, name):
        await self.cell.auth.delUser(name)
        await self.cell.fire('user:mod', act='deluser', name=name)

    @adminapi(log=True)
    async def addAuthRole(self, name):
        role = await self.cell.auth.addRole(name)
        await self.cell.fire('user:mod', act='addrole', name=name)
        return role.pack()

    @adminapi(log=True)
    async def delAuthRole(self, name):
        await self.cell.auth.delRole(name)
        await self.cell.fire('user:mod', act='delrole', name=name)

    @adminapi()
    async def getAuthUsers(self, archived=False):
        '''
        Args:
            archived (bool):  If true, list all users, else list non-archived users
        '''
        return await self.cell.getAuthUsers(archived=archived)

    @adminapi()
    async def getAuthRoles(self):
        return await self.cell.getAuthRoles()

    @adminapi(log=True)
    async def addUserRule(self, iden, rule, indx=None, gateiden=None):
        return await self.cell.addUserRule(iden, rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def setUserRules(self, iden, rules, gateiden=None):
        return await self.cell.setUserRules(iden, rules, gateiden=gateiden)

    @adminapi(log=True)
    async def setRoleRules(self, iden, rules, gateiden=None):
        return await self.cell.setRoleRules(iden, rules, gateiden=gateiden)

    @adminapi(log=True)
    async def addRoleRule(self, iden, rule, indx=None, gateiden=None):
        return await self.cell.addRoleRule(iden, rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def delUserRule(self, iden, rule, gateiden=None):
        return await self.cell.delUserRule(iden, rule, gateiden=gateiden)

    @adminapi(log=True)
    async def delRoleRule(self, iden, rule, gateiden=None):
        return await self.cell.delRoleRule(iden, rule, gateiden=gateiden)

    @adminapi(log=True)
    async def setUserAdmin(self, iden, admin, gateiden=None):
        return await self.cell.setUserAdmin(iden, admin, gateiden=gateiden)

    @adminapi()
    async def getAuthInfo(self, name):
        s_common.deprecated('getAuthInfo')
        user = await self.cell.auth.getUserByName(name)
        if user is not None:
            info = user.pack()
            info['roles'] = [self.cell.auth.role(r).name for r in info['roles']]
            return info

        role = await self.cell.auth.getRoleByName(name)
        if role is not None:
            return role.pack()

        raise s_exc.NoSuchName(name=name)

    @adminapi(log=True)
    async def addAuthRule(self, name, rule, indx=None, gateiden=None):
        s_common.deprecated('addAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.addRule(rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def delAuthRule(self, name, rule, gateiden=None):
        s_common.deprecated('delAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.delRule(rule, gateiden=gateiden)

    @adminapi(log=True)
    async def setAuthAdmin(self, name, isadmin):
        s_common.deprecated('setAuthAdmin')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.setAdmin(isadmin)

    async def setUserPasswd(self, iden, passwd):

        await self.cell.auth.reqUser(iden)

        if self.user.iden == iden:
            self.user.confirm(('auth', 'self', 'set', 'passwd'), default=True)
            return await self.cell.setUserPasswd(iden, passwd)

        self.user.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.cell.setUserPasswd(iden, passwd)

    @adminapi(log=True)
    async def setUserLocked(self, useriden, locked):
        return await self.cell.setUserLocked(useriden, locked)

    @adminapi(log=True)
    async def setUserArchived(self, useriden, archived):
        return await self.cell.setUserArchived(useriden, archived)

    @adminapi(log=True)
    async def setUserEmail(self, useriden, email):
        return await self.cell.setUserEmail(useriden, email)

    @adminapi(log=True)
    async def addUserRole(self, useriden, roleiden):
        return await self.cell.addUserRole(useriden, roleiden)

    @adminapi(log=True)
    async def setUserRoles(self, useriden, roleidens):
        return await self.cell.setUserRoles(useriden, roleidens)

    @adminapi(log=True)
    async def delUserRole(self, useriden, roleiden):
        return await self.cell.delUserRole(useriden, roleiden)

    async def getUserInfo(self, name):
        user = await self.cell.auth.reqUserByName(name)
        if self.user.isAdmin() or self.user.iden == user.iden:
            info = user.pack()
            info['roles'] = [self.cell.auth.role(r).name for r in info['roles']]
            return info

        mesg = 'getUserInfo denied for non-admin and non-self'
        raise s_exc.AuthDeny(mesg=mesg)

    async def getRoleInfo(self, name):
        role = await self.cell.auth.reqRoleByName(name)
        if self.user.isAdmin() or role.iden in self.user.info.get('roles', ()):
            return role.pack()

        mesg = 'getRoleInfo denied for non-admin and non-member'
        raise s_exc.AuthDeny(mesg=mesg)

    @adminapi()
    async def getUserDef(self, iden):
        return await self.cell.getUserDef(iden)

    @adminapi()
    async def getAuthGate(self, iden):
        return await self.cell.getAuthGate(iden)

    @adminapi()
    async def getAuthGates(self):
        return await self.cell.getAuthGates()

    @adminapi()
    async def getRoleDef(self, iden):
        return await self.cell.getRoleDef(iden)

    @adminapi()
    async def getUserDefByName(self, name):
        return await self.cell.getUserDefByName(name)

    @adminapi()
    async def getRoleDefByName(self, name):
        return await self.cell.getRoleDefByName(name)

    @adminapi()
    async def getUserDefs(self):
        return await self.cell.getUserDefs()

    @adminapi()
    async def getRoleDefs(self):
        return await self.cell.getRoleDefs()

    @adminapi()
    async def isUserAllowed(self, iden, perm, gateiden=None):
        return await self.cell.isUserAllowed(iden, perm, gateiden=gateiden)

    @adminapi()
    async def tryUserPasswd(self, name, passwd):
        return await self.cell.tryUserPasswd(name, passwd)

    @adminapi()
    async def getUserProfile(self, iden):
        return await self.cell.getUserProfile(iden)

    @adminapi()
    async def getUserProfInfo(self, iden, name):
        return await self.cell.getUserProfInfo(iden, name)

    @adminapi()
    async def setUserProfInfo(self, iden, name, valu):
        return await self.cell.setUserProfInfo(iden, name, valu)

    async def getHealthCheck(self):
        await self._reqUserAllowed(('health',))
        return await self.cell.getHealthCheck()

    @adminapi()
    async def getDmonSessions(self):
        return await self.cell.getDmonSessions()

    @adminapi()
    async def listHiveKey(self, path=None):
        return await self.cell.listHiveKey(path=path)

    @adminapi()
    async def getHiveKeys(self, path):
        return await self.cell.getHiveKeys(path)

    @adminapi()
    async def getHiveKey(self, path):
        return await self.cell.getHiveKey(path)

    @adminapi(log=True)
    async def setHiveKey(self, path, valu):
        return await self.cell.setHiveKey(path, valu)

    @adminapi(log=True)
    async def popHiveKey(self, path):
        return await self.cell.popHiveKey(path)

    @adminapi(log=True)
    async def saveHiveTree(self, path=()):
        return await self.cell.saveHiveTree(path=path)

    @adminapi()
    async def getNexusChanges(self, offs):
        async for item in self.cell.getNexusChanges(offs):
            yield item

    @adminapi()
    async def runBackup(self, name=None, wait=True):
        '''
        Run a new backup.

        Args:
            name (str): The optional name of the backup.
            wait (bool): On True, wait for backup to complete before returning.

        Returns:
            str: The name of the newly created backup.
        '''
        return await self.cell.runBackup(name=name, wait=wait)

    @adminapi()
    async def getBackupInfo(self):
        '''
        Get information about recent backup activity.

        Returns:
            (dict) It has the following keys:
                - currduration - If backup currently running, time in ms since backup started, otherwise None
                - laststart - Last time (in epoch milliseconds) a backup started
                - lastend - Last time (in epoch milliseconds) a backup ended
                - lastduration - How long last backup took in ms
                - lastsize - Disk usage of last backup completed
                - lastupload - Time a backup was last completed being uploaded via iter(New)BackupArchive
                - lastexception - Tuple of exception information if last backup failed, otherwise None

        Note:  these statistics are not persistent, i.e. they are not preserved between cell restarts.
        '''
        return await self.cell.getBackupInfo()

    @adminapi()
    async def getBackups(self):
        '''
        Retrieve a list of backups.

        Returns:
            list[str]: A list of backup names.
        '''
        return await self.cell.getBackups()

    @adminapi()
    async def delBackup(self, name):
        '''
        Delete a backup by name.

        Args:
            name (str): The name of the backup to delete.
        '''
        return await self.cell.delBackup(name)

    @adminapi()
    async def iterBackupArchive(self, name):
        '''
        Retrieve a backup by name as a compressed stream of bytes.

        Note: Compression and streaming will occur from a separate process.

        Args:
            name (str): The name of the backup to retrieve.
        '''
        await self.cell.iterBackupArchive(name, user=self.user)

        # Make this a generator
        if False: # pragma: no cover
            yield

    @adminapi()
    async def iterNewBackupArchive(self, name=None, remove=False):
        '''
        Run a new backup and return it as a compressed stream of bytes.

        Note: Compression and streaming will occur from a separate process.

        Args:
            name (str): The name of the backup to retrieve.
            remove (bool): Delete the backup after streaming.
        '''
        await self.cell.iterNewBackupArchive(user=self.user, name=name, remove=remove)

        # Make this a generator
        if False: # pragma: no cover
            yield

    @adminapi()
    async def getDiagInfo(self):
        return {
            'slabs': await s_lmdbslab.Slab.getSlabStats(),
        }

class Cell(s_nexus.Pusher, s_telepath.Aware):
    '''
    A Cell() implements a synapse micro-service.

    A Cell has 5 phases of startup:
        1. Universal cell data structures
        2. Service specific storage/data (pre-nexs)
        3. Nexus subsystem initialization
        4. Service specific startup (with nexus)
        5. Networking and mirror services

    '''
    cellapi = CellApi

    confdefs = {}  # type: ignore  # This should be a JSONSchema properties list for an object.
    confbase = {
        'cell:guid': {
            'description': 'An optional hard-coded GUID to store as the permanent GUID for the cell.',
            'type': 'string',
        },
        'cell:ctor': {
            'description': 'An optional python path to the Cell class.  Used by stemcell.',
            'type': 'string',
        },
        'mirror': {
            'description': 'A telepath URL for our upstream mirror (we must be a backup!).',
            'type': 'string',
        },
        'auth:passwd': {
            'description': 'Set to <passwd> (local only) to bootstrap the root user password.',
            'type': 'string',
        },
        'auth:anon': {
            'description': 'Allow anonymous telepath access by mapping to the given user name.',
            'type': 'string',
        },
        'auth:ctor': {
            'description': 'Allow the construction of the cell auth object to be hooked at runtime.',
            'type': 'string',
            'hideconf': True,
        },
        'auth:conf': {
            'description': 'Extended configuration to be used by an alternate auth constructor.',
            'type': 'object',
            'hideconf': True,
        },
        'nexslog:en': {
            'default': False,
            'description': 'Record all changes to the cell.  Required for mirroring (on both sides).',
            'type': 'boolean',
        },
        'nexslog:async': {
            'default': False,
            'description': '(Experimental) Map the nexus log LMDB instance with map_async=True.',
            'type': 'boolean',
        },
        'dmon:listen': {
            'description': 'A config-driven way to specify the telepath bind URL.',
            'type': ['string', 'null'],
        },
        'https:port': {
            'description': 'A config-driven way to specify the HTTPS port.',
            'type': ['integer', 'null'],
        },
        'https:headers': {
            'description': 'Headers to add to all HTTPS server responses.',
            'type': 'object',
            'hidecmdl': True,
        },
        'backup:dir': {
            'description': 'A directory outside the service directory where backups will be saved.',
            'type': 'string',
        },
        'aha:name': {
            'description': 'The name of the cell service in the aha service registry.',
            'type': 'string',
        },
        'aha:leader': {
            'description': 'The AHA service name to claim as the active instance of a storm service.',
            'type': 'string',
        },
        'aha:network': {
            'description': 'The AHA service network. This makes aha:name/aha:leader relative names.',
            'type': 'string',
        },
        'aha:registry': {
            'description': 'The telepath URL of the aha service registry.',
            'type': ['string', 'array'],
            'items': {'type': 'string'},
        },
        'aha:admin': {
            'description': 'An AHA client certificate CN to register as a local admin user.',
            'type': 'string',
        },
        'aha:svcinfo': {
            'description': 'An AHA svcinfo object. If set, this overrides self discovered Aha service information.',
            'type': 'object',
            'properties': {
                'urlinfo': {
                    'type': 'object',
                    'properties': {
                        'host': {'type': 'string'},
                        'port': {'type': 'integer'},
                        'schema': {'type': 'string'}
                    },
                    'required': ('host', 'port', 'scheme', )
                }
            },
            'required': ('urlinfo', ),
        },
        '_log_conf': {
            'description': 'Opaque structure used for logging by spawned processes.',
            'type': 'object',
            'hideconf': True
        }
    }

    BACKUP_SPAWN_TIMEOUT = 60.0

    COMMIT = s_version.commit
    VERSION = s_version.version
    VERSTRING = s_version.verstring

    async def __anit__(self, dirn, conf=None, readonly=False):

        # phase 1
        if conf is None:
            conf = {}

        self.starttime = time.monotonic()  # Used for uptime calc
        self.startms = s_common.now()      # Used to report start time
        s_telepath.Aware.__init__(self)
        self.dirn = s_common.gendir(dirn)

        self.auth = None
        self.sessions = {}
        self.isactive = False
        self.inaugural = False
        self.activecoros = {}

        self.conf = self._initCellConf(conf)

        # each cell has a guid
        path = s_common.genpath(self.dirn, 'cell.guid')

        # generate a guid file if needed
        if not os.path.isfile(path):

            self.inaugural = True

            guid = conf.get('cell:guid')
            if guid is None:
                guid = s_common.guid()

            with open(path, 'w') as fd:
                fd.write(guid)

        # read our guid file
        with open(path, 'r') as fd:
            self.iden = fd.read().strip()

        self.donexslog = self.conf.get('nexslog:en')

        backdirn = self.conf.get('backup:dir')
        if backdirn is not None:
            backdirn = s_common.genpath(backdirn)
            if backdirn.startswith(self.dirn):
                mesg = 'backup:dir must not be within the service directory'
                raise s_exc.BadConfValu(mesg=mesg)

            backdirn = s_common.gendir(backdirn)

        self.backdirn = backdirn
        self.backuprunning = False  # Whether a backup is currently running
        self.backmonostart = None  # If a backup is running, when did it start (monotonic timer)
        self.backstartdt = None  # Last backup start time
        self.backenddt = None  # Last backup end time
        self.backlasttook = None  # Last backup duration
        self.backlastsize = None  # Last backup size
        self.backlastuploaddt = None  # Last time backup completed uploading via iter{New,}BackupArchive
        self.backlastexc = None  # err, errmsg, errtrace of last backup

        if self.conf.get('mirror') and not self.conf.get('nexslog:en'):
            mesg = 'Mirror mode requires nexslog:en=True'
            raise s_exc.BadConfValu(mesg=mesg)

        # construct our nexsroot instance ( but do not start it )
        await s_nexus.Pusher.__anit__(self, self.iden)

        root = await self._ctorNexsRoot()

        # mutually assured destruction with our nexs root
        self.onfini(root.fini)
        root.onfini(self.fini)

        self.setNexsRoot(root)

        await self._initCellSlab(readonly=readonly)

        self.hive = await self._initCellHive()

        # self.cellinfo, a HiveDict for general purpose persistent storage
        node = await self.hive.open(('cellinfo',))
        self.cellinfo = await node.dict()
        self.onfini(node)

        node = await self.hive.open(('cellvers',))
        self.cellvers = await node.dict(nexs=True)

        if self.inaugural:
            await self.cellinfo.set('synapse:version', s_version.version)

        synvers = self.cellinfo.get('synapse:version')

        if synvers is None or synvers < s_version.version:
            await self.cellinfo.set('synapse:version', s_version.version)

        self.auth = await self._initCellAuth()

        auth_passwd = self.conf.get('auth:passwd')
        if auth_passwd is not None:
            user = await self.auth.getUserByName('root')

            if not await user.tryPasswd(auth_passwd):
                await user.setPasswd(auth_passwd, nexs=False)

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        self.dynitems = {
            'auth': self.auth,
            'cell': self
        }

        # a tuple of (vers, func) tuples
        # it is expected that this is set by
        # initServiceStorage
        self.cellupdaters = ()

        # initialize web app and callback data structures
        self._health_funcs = []
        self.addHealthFunc(self._cellHealth)

        # initialize network backend infrastructure
        await self._initCertDir()
        await self._initAhaRegistry()

        # initialize network daemons (but do not listen yet)
        # to allow registration of callbacks and shared objects
        # within phase 2/4.
        await self._initCellHttp()
        await self._initCellDmon()

        # phase 2 - service storage
        await self.initServiceStorage()
        # phase 3 - nexus subsystem
        await self.initNexusSubsystem()
        # phase 4 - service logic
        await self.initServiceRuntime()
        # phase 5 - service networking
        await self.initServiceNetwork()

    async def _execCellUpdates(self):
        # implement to apply updates to a fully initialized active cell
        # ( and do so using _bumpCellVers )
        pass

    async def _bumpCellVers(self, name, updates):

        if self.inaugural:
            await self.cellvers.set(name, updates[-1][0])
            return

        curv = self.cellvers.get(name, 0)

        for vers, callback in updates:

            if vers <= curv:
                continue

            await callback()

            await self.cellvers.set(name, vers)

            curv = vers

    async def _initAhaRegistry(self):

        self.ahainfo = None
        self.ahaclient = None

        ahaurl = self.conf.get('aha:registry')
        if ahaurl is not None:

            info = await s_telepath.addAhaUrl(ahaurl)
            self.ahaclient = info.get('client')
            if self.ahaclient is None:
                self.ahaclient = await s_telepath.Client.anit(info.get('url'))
                self.ahaclient._fini_atexit = True
                info['client'] = self.ahaclient

            async def finiaha():
                await s_telepath.delAhaUrl(ahaurl)

            self.onfini(finiaha)

        ahaadmin = self.conf.get('aha:admin')
        if ahaadmin is not None:
            # add the user in a pre-nexus compatible way
            user = await self.auth.getUserByName(ahaadmin)

            if user is None:
                iden = s_common.guid(ahaadmin)
                await self.auth._addUser(iden, ahaadmin)
                user = await self.auth.getUserByName(ahaadmin)

            if not user.isAdmin():
                await user.setAdmin(True, logged=False)

            if user.isLocked():
                await user.setLocked(False, logged=False)

    async def initServiceStorage(self):
        pass

    async def initNexusSubsystem(self):
        mirror = self.conf.get('mirror')
        await self.nexsroot.startup(mirror, celliden=self.iden)
        await self.setCellActive(mirror is None)

    async def initServiceNetwork(self):

        # start a unix local socket daemon listener
        sockpath = os.path.join(self.dirn, 'sock')
        sockurl = f'unix://{sockpath}'

        try:
            await self.dmon.listen(sockurl)
        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise
        except OSError as e:
            logger.error(f'Failed to listen on unix socket at: [{sockpath}][{e}]')
            logger.error('LOCAL UNIX SOCKET WILL BE UNAVAILABLE')
        except Exception:  # pragma: no cover
            logging.exception('Unknown dmon listen error.')
            raise

        self.sockaddr = None

        turl = self.conf.get('dmon:listen')
        if turl is not None:
            self.sockaddr = await self.dmon.listen(turl)
            logger.info(f'dmon listening: {turl}')

        await self._initAhaService()

        port = self.conf.get('https:port')
        if port is not None:
            await self.addHttpsPort(port)
            logger.info(f'https listening: {port}')

    async def _initAhaService(self):

        if self.ahaclient is None:
            return

        turl = self.conf.get('dmon:listen')
        ahaname = self.conf.get('aha:name')
        if ahaname is None:
            return

        ahalead = self.conf.get('aha:leader')
        ahanetw = self.conf.get('aha:network')

        ahainfo = self.conf.get('aha:svcinfo')
        if ahainfo is None and turl is not None:

            urlinfo = s_telepath.chopurl(turl)

            urlinfo.pop('host', None)
            urlinfo['port'] = self.sockaddr[1]

            ahainfo = {
                'urlinfo': urlinfo,
            }

        if ahainfo is None:
            return

        self.ahainfo = ahainfo

        async def onlink(proxy):
            await proxy.addAhaSvc(ahaname, self.ahainfo, network=ahanetw)
            if self.isactive and ahalead is not None:
                await proxy.addAhaSvc(ahalead, self.ahainfo, network=ahanetw)

        async def fini():
            await self.ahaclient.offlink(onlink)

        await self.ahaclient.onlink(onlink)
        self.onfini(fini)

    async def initServiceRuntime(self):
        pass

    async def _ctorNexsRoot(self):
        '''
        Initialize a NexsRoot to use for the cell.
        '''
        map_async = self.conf.get('nexslog:async')
        return await s_nexus.NexsRoot.anit(self.dirn, donexslog=self.donexslog, map_async=map_async)

    async def getNexsIndx(self):
        return await self.nexsroot.index()

    async def cullNexsLog(self, offs):
        if self.backuprunning:
            raise s_exc.SlabInUse(mesg='Cannot cull Nexus log while a backup is running')
        return await self._push('nexslog:cull', offs)

    @s_nexus.Pusher.onPush('nexslog:cull')
    async def _cullNexsLog(self, offs):
        return await self.nexsroot.cull(offs)

    async def rotateNexsLog(self):
        if self.backuprunning:
            raise s_exc.SlabInUse(mesg='Cannot rotate Nexus log while a backup is running')
        return await self._push('nexslog:rotate')

    @s_nexus.Pusher.onPush('nexslog:rotate')
    async def _rotateNexsLog(self):
        return await self.nexsroot.rotate()

    async def waitNexsOffs(self, offs, timeout=None):
        return await self.nexsroot.waitOffs(offs, timeout=timeout)

    async def trimNexsLog(self, consumers=None, timeout=30):

        if not self.donexslog:
            mesg = 'trimNexsLog requires nexslog:en=True'
            raise s_exc.BadConfValu(mesg=mesg)

        async with await s_base.Base.anit() as base:

            if consumers is not None:
                cons_opened = []
                for turl in consumers:
                    prox = await s_telepath.openurl(turl)
                    base.onfini(prox.fini)
                    cons_opened.append((s_urlhelp.sanitizeUrl(turl), prox))

            offs = await self.rotateNexsLog()
            cullat = offs - 1

            # wait for all consumers to catch up and raise otherwise
            if consumers is not None:

                async def waitFor(turl_sani, prox_):
                    logger.debug('trimNexsLog waiting for consumer %s to write offset %d', turl_sani, cullat)
                    if not await prox_.waitNexsOffs(cullat, timeout=timeout):
                        mesg_ = 'trimNexsLog timed out waiting for consumer to write rotation offset'
                        raise s_exc.SynErr(mesg=mesg_, offs=cullat, timeout=timeout, url=turl_sani)
                    logger.info('trimNexsLog consumer %s successfully wrote offset', turl_sani)

                await asyncio.gather(*[waitFor(*cons) for cons in cons_opened])

            if not await self.cullNexsLog(cullat):
                mesg = 'trimNexsLog did not execute cull at the rotated offset'
                raise s_exc.SynErr(mesg=mesg, offs=cullat)

            return cullat

    @s_nexus.Pusher.onPushAuto('nexslog:setindex')
    async def setNexsIndx(self, indx):
        return await self.nexsroot.setindex(indx)

    async def promote(self):
        '''
        Transform this cell from a passive follower to
        an active cell that writes changes locally.
        '''
        if self.conf.get('mirror') is None:
            mesg = 'promote() called on non-mirror'
            raise s_exc.BadConfValu(mesg=mesg)

        await self.nexsroot.promote()
        await self.setCellActive(True)

    async def _setAhaActive(self):

        if self.ahaclient is None:
            return

        if self.ahainfo is None:
            return

        ahalead = self.conf.get('aha:leader')
        if ahalead is None:
            return

        try:

            proxy = await self.ahaclient.proxy(timeout=2)

        except TimeoutError: # pragma: no cover
            return None

        # if we went inactive, bump the aha proxy
        if not self.isactive:
            await proxy.fini()
            return

        ahanetw = self.conf.get('aha:network')
        try:
            await proxy.addAhaSvc(ahalead, self.ahainfo, network=ahanetw)
        except asyncio.CancelledError: # pragma: no cover
            raise
        except Exception as e: # pragma: no cover
            logger.warning(f'_setAhaActive failed: {e}')

    def addActiveCoro(self, func, iden=None, base=None):
        '''
        Add a function callback to be run as a coroutine when the Cell is active.

        Args:
            func (coroutine function): The function run as a coroutine.
            iden (str): The iden to use for the coroutine.
            base (Optional[Base]):  if present, this active coro will be fini'd
                                    when the base is fini'd


        Returns:
            str: A GUID string that identifies the coroutine for delActiveCoro()

        NOTE:
            This will re-fire the coroutine if it exits and the Cell is still active.
        '''
        if base and base.isfini:
            raise s_exc.IsFini()

        if iden is None:
            iden = s_common.guid()

        cdef = {'func': func, 'base': base}
        self.activecoros[iden] = cdef

        if base:
            async def fini():
                await self.delActiveCoro(iden)
            base.onfini(fini)

        if self.isactive:
            self._fireActiveCoro(iden, cdef)

        return iden

    async def delActiveCoro(self, iden):
        '''
        Remove an Active coroutine previously added with addActiveCoro().

        Args:
            iden (str): The iden returned by addActiveCoro()
        '''
        cdef = self.activecoros.pop(iden, None)
        if cdef is None:
            return

        await self._killActiveCoro(cdef)

    def _fireActiveCoros(self):
        for iden, cdef in self.activecoros.items():
            self._fireActiveCoro(iden, cdef)

    def _fireActiveCoro(self, iden, cdef):

        func = cdef.get('func')

        async def wrap():
            while not self.isfini:
                try:
                    await func()
                except asyncio.CancelledError:
                    raise
                except Exception:  # pragma no cover
                    logger.exception(f'activeCoro Error: {func}')
                    await asyncio.sleep(1)

        cdef['task'] = self.schedCoro(wrap())

    async def _killActiveCoros(self):
        for cdef in self.activecoros.values():
            await self._killActiveCoro(cdef)

    async def _killActiveCoro(self, cdef):
        task = cdef.pop('task', None)
        if task is not None:
            task.cancel()
            await asyncio.sleep(0)

    async def isCellActive(self):
        return self.isactive

    async def setCellActive(self, active):
        self.isactive = active

        if self.isactive:
            self._fireActiveCoros()
            await self._execCellUpdates()
            await self.initServiceActive()
        else:
            await self._killActiveCoros()
            await self.initServicePassive()

        await self._setAhaActive()

    async def initServiceActive(self): # pragma: no cover
        pass

    async def initServicePassive(self): # pragma: no cover
        pass

    async def getNexusChanges(self, offs):
        async for item in self.nexsroot.iter(offs):
            yield item

    def _reqBackDirn(self, name):

        self._reqBackConf()

        path = s_common.genpath(self.backdirn, name)
        if not path.startswith(self.backdirn):
            mesg = 'Directory traversal detected'
            raise s_exc.BadArg(mesg=mesg)

        return path

    async def runBackup(self, name=None, wait=True):

        if self.backuprunning:
            raise s_exc.BackupAlreadyRunning(mesg='Another backup is already running')

        try:
            task = None

            backupstartdt = datetime.datetime.now()

            if name is None:
                name = time.strftime('%Y%m%d%H%M%S', backupstartdt.timetuple())

            path = self._reqBackDirn(name)
            if os.path.isdir(path):
                mesg = 'Backup with name already exists'
                raise s_exc.BadArg(mesg=mesg)

            self.backuprunning = True
            self.backlastexc = None
            self.backmonostart = time.monotonic()
            self.backstartdt = backupstartdt

            task = self.schedCoro(self._execBackupTask(path))

            def done(self, task):
                try:
                    self.backlastsize, _ = s_common.getDirSize(path)
                except s_exc.NoSuchDir:
                    pass
                self.backlasttook = time.monotonic() - self.backmonostart
                self.backenddt = datetime.datetime.now()
                self.backmonostart = None

                try:
                    exc = task.exception()
                except asyncio.CancelledError as e:
                    exc = e
                if exc:
                    self.backlastexc = s_common.excinfo(exc)
                    self.backlastsize = None
                else:
                    self.backlastexc = None
                    try:
                        self.backlastsize, _ = s_common.getDirSize(path)
                    except Exception:
                        self.backlastsize = None

                self.backuprunning = False

                phrase = f'with exception {self.backlastexc["errmsg"]}' if self.backlastexc else 'successfully'
                logger.info(f'Backup {name} completed {phrase}.  Took {self.backlasttook / 1000} s')

            task.add_done_callback(functools.partial(done, self))

            if wait:
                logger.info(f'Waiting for backup task to complete [{name}]')
                await task

            return name

        except (asyncio.CancelledError, Exception):
            if task is not None:
                task.cancel()
            raise

    async def getBackupInfo(self):
        '''
        Gets information about recent backup activity
        '''
        running = int(time.monotonic() - self.backmonostart * 1000) if self.backmonostart else None

        def epochmillis(dtornone):
            if dtornone is None:
                return None
            return int(dtornone.timestamp() * 1000)

        retn = {
            'currduration': running,
            'laststart': int(self.backstartdt.timestamp() * 1000) if self.backstartdt else None,
            'lastend': int(self.backenddt.timestamp() * 1000) if self.backenddt else None,
            'lastduration': int(self.backlasttook * 1000) if self.backlasttook else None,
            'lastsize': self.backlastsize,
            'lastupload': int(self.backlastuploaddt.timestamp() * 1000) if self.backlastuploaddt else None,
            'lastexception': self.backlastexc,
        }

        return retn

    async def _execBackupTask(self, dirn):
        '''
        A task that backs up the cell to the target directory
        '''
        logger.info(f'Starting backup to [{dirn}]')

        await self.boss.promote('backup', self.auth.rootuser)
        slabs = s_lmdbslab.Slab.getSlabsInDir(self.dirn)
        assert slabs

        ctx = multiprocessing.get_context('spawn')

        mypipe, child_pipe = ctx.Pipe()
        paths = [str(slab.path) for slab in slabs]
        logconf = await self._getSpawnLogConf()
        proc = None

        try:

            async with self.nexsroot.applylock:

                logger.debug('Syncing LMDB Slabs')

                while True:
                    await s_lmdbslab.Slab.syncLoopOnce()
                    if not any(slab.dirty for slab in slabs):
                        break

                logger.debug('Starting backup process')

                args = (child_pipe, self.dirn, dirn, paths, logconf)

                def waitforproc1():
                    nonlocal proc
                    proc = ctx.Process(target=self._backupProc, args=args)
                    proc.start()
                    hasdata = mypipe.poll(timeout=self.BACKUP_SPAWN_TIMEOUT)
                    if not hasdata:
                        raise s_exc.SynErr(mesg='backup subprocess start timed out')
                    data = mypipe.recv()
                    assert data == 'captured'

                await s_coro.executor(waitforproc1)

            def waitforproc2():
                proc.join()
                if proc.exitcode:
                    raise s_exc.SpawnExit(code=proc.exitcode)

            await s_coro.executor(waitforproc2)
            proc = None

            logger.info(f'Backup completed to [{dirn}]')
            return

        except (asyncio.CancelledError, Exception):
            logger.exception(f'Error performing backup to [{dirn}]')
            raise

        finally:
            if proc:
                proc.terminate()

    @staticmethod
    def _backupProc(pipe, srcdir, dstdir, lmdbpaths, logconf):
        '''
        (In a separate process) Actually do the backup
        '''
        # This is a new process: configure logging
        s_common.setlogging(logger, **logconf)

        with s_t_backup.capturelmdbs(srcdir) as lmdbinfo:
            pipe.send('captured')
            logger.debug('Acquired LMDB transactions')
            s_t_backup.txnbackup(lmdbinfo, srcdir, dstdir)

        logger.debug('Backup process completed')

    def _reqBackConf(self):
        if self.backdirn is None:
            mesg = 'Backup APIs require the backup:dir config option is set'
            raise s_exc.NeedConfValu(mesg=mesg)

    async def delBackup(self, name):

        self._reqBackConf()
        path = self._reqBackDirn(name)

        cellguid = os.path.join(path, 'cell.guid')
        if not os.path.isfile(cellguid):
            mesg = 'Specified backup path has no cell.guid file.'
            raise s_exc.BadArg(mesg=mesg)
        logger.info(f'Removing backup for [{path}]')
        await s_coro.executor(shutil.rmtree, path, ignore_errors=True)
        logger.info(f'Backup removed from [{path}]')

    async def getBackups(self):
        self._reqBackConf()
        backups = []

        def walkpath(path):

            for name in os.listdir(path):

                full = os.path.join(path, name)
                cellguid = os.path.join(full, 'cell.guid')

                if os.path.isfile(cellguid):
                    backups.append(os.path.relpath(full, self.backdirn))
                    continue

                if os.path.isdir(full):
                    walkpath(full)

        walkpath(self.backdirn)
        return backups

    async def iterBackupArchive(self, name, user):

        success = False

        path = self._reqBackDirn(name)
        cellguid = os.path.join(path, 'cell.guid')
        if not os.path.isfile(cellguid):
            mesg = 'Specified backup path has no cell.guid file.'
            raise s_exc.BadArg(mesg=mesg, arg='path', valu=path)

        link = s_scope.get('link')
        linkinfo = await link.getSpawnInfo()
        linkinfo['logconf'] = await self._getSpawnLogConf()

        await self.boss.promote('backup:stream', user=user, info={'name': name})

        ctx = multiprocessing.get_context('spawn')

        proc = None
        mesg = 'Streaming complete'

        def getproc():
            proc = ctx.Process(target=_iterBackupProc, args=(path, linkinfo))
            proc.start()
            return proc

        try:
            proc = await s_coro.executor(getproc)

            await s_coro.executor(proc.join)

        except (asyncio.CancelledError, Exception) as e:

            if not isinstance(e, asyncio.CancelledError):
                logger.exception('Error during backup streaming.')

            if proc:
                proc.terminate()

            mesg = repr(e)
            raise

        else:
            success = True
            self.backlastuploaddt = datetime.datetime.now()

        finally:
            phrase = 'successfully' if success else 'with failure'
            logger.debug(f'iterBackupArchive completed {phrase} for {name}')
            raise s_exc.DmonSpawn(mesg=mesg)

    async def iterNewBackupArchive(self, user, name=None, remove=False):

        success = False

        if name is None:
            name = time.strftime('%Y%m%d%H%M%S', datetime.datetime.now().timetuple())

        path = self._reqBackDirn(name)
        if os.path.isdir(path):
            mesg = 'Backup with name already exists'
            raise s_exc.BadArg(mesg=mesg)

        link = s_scope.get('link')
        linkinfo = await link.getSpawnInfo()
        linkinfo['logconf'] = await self._getSpawnLogConf()

        try:
            await self.runBackup(name)
        except Exception:
            if remove:
                logger.debug(f'Removing {path}')
                await s_coro.executor(shutil.rmtree, path, ignore_errors=True)
                logger.debug(f'Removed {path}')
            raise

        await self.boss.promote('backup:stream', user=user, info={'name': name})

        ctx = multiprocessing.get_context('spawn')

        proc = None
        mesg = 'Streaming complete'

        def getproc():
            proc = ctx.Process(target=_iterBackupProc, args=(path, linkinfo))
            proc.start()
            return proc

        try:
            proc = await s_coro.executor(getproc)

            await s_coro.executor(proc.join)

        except (asyncio.CancelledError, Exception) as e:

            if not isinstance(e, asyncio.CancelledError):
                logger.exception('Error during backup streaming.')

            if proc:
                proc.terminate()

            mesg = repr(e)
            raise

        else:
            success = True
            self.backlastuploaddt = datetime.datetime.now()

        finally:
            if remove:
                logger.debug(f'Removing {path}')
                await s_coro.executor(shutil.rmtree, path, ignore_errors=True)
                logger.debug(f'Removed {path}')

            phrase = 'successfully' if success else 'with failure'
            logger.debug(f'iterNewBackupArchive completed {phrase} for {name}')
            raise s_exc.DmonSpawn(mesg=mesg)

    async def isUserAllowed(self, iden, perm, gateiden=None):
        user = self.auth.user(iden)
        if user is None:
            return False

        return user.allowed(perm, gateiden=gateiden)

    async def tryUserPasswd(self, name, passwd):
        user = await self.auth.getUserByName(name)
        if user is None:
            return None

        if not await user.tryPasswd(passwd):
            return None

        return user.pack()

    async def getUserProfile(self, iden):
        user = await self.auth.reqUser(iden)
        return user.profile.pack()

    async def getUserProfInfo(self, iden, name):
        user = await self.auth.reqUser(iden)
        return user.profile.get(name)

    async def setUserProfInfo(self, iden, name, valu):
        user = await self.auth.reqUser(iden)
        return await user.profile.set(name, valu)

    async def addUserRule(self, iden, rule, indx=None, gateiden=None):
        user = await self.auth.reqUser(iden)
        retn = await user.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    async def addRoleRule(self, iden, rule, indx=None, gateiden=None):
        role = await self.auth.reqRole(iden)
        retn = await role.addRule(rule, indx=indx, gateiden=gateiden)
        return retn

    async def delUserRule(self, iden, rule, gateiden=None):
        user = await self.auth.reqUser(iden)
        return await user.delRule(rule, gateiden=gateiden)

    async def delRoleRule(self, iden, rule, gateiden=None):
        role = await self.auth.reqRole(iden)
        return await role.delRule(rule, gateiden=gateiden)

    async def setUserRules(self, iden, rules, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setRules(rules, gateiden=gateiden)

    async def setRoleRules(self, iden, rules, gateiden=None):
        role = await self.auth.reqRole(iden)
        await role.setRules(rules, gateiden=gateiden)

    async def setRoleName(self, iden, name):
        role = await self.auth.reqRole(iden)
        await role.setName(name)

    async def setUserAdmin(self, iden, admin, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setAdmin(admin, gateiden=gateiden)

    async def addUserRole(self, useriden, roleiden):
        user = await self.auth.reqUser(useriden)
        await user.grant(roleiden)
        await self.fire('user:mod', act='grant', user=useriden, role=roleiden)

    async def setUserRoles(self, useriden, roleidens):
        user = await self.auth.reqUser(useriden)
        await user.setRoles(roleidens)
        await self.fire('user:mod', act='setroles', user=useriden, roles=roleidens)

    async def delUserRole(self, useriden, roleiden):
        user = await self.auth.reqUser(useriden)
        await user.revoke(roleiden)

        await self.fire('user:mod', act='revoke', user=useriden, role=roleiden)

    async def addUser(self, name, passwd=None, email=None, iden=None):
        user = await self.auth.addUser(name, passwd=passwd, email=email, iden=iden)
        await self.fire('user:mod', act='adduser', name=name)
        return user.pack(packroles=True)

    async def delUser(self, iden):
        await self.auth.delUser(iden)
        await self.fire('user:mod', act='deluser', user=iden)

    async def addRole(self, name):
        role = await self.auth.addRole(name)
        return role.pack()

    async def delRole(self, iden):
        await self.auth.delRole(iden)

    async def setUserEmail(self, useriden, email):
        await self.auth.setUserInfo(useriden, 'email', email)

    async def setUserName(self, useriden, name):
        user = await self.auth.reqUser(useriden)
        await user.setName(name)

    async def setUserPasswd(self, iden, passwd):
        user = await self.auth.reqUser(iden)
        await user.setPasswd(passwd)
        await self.fire('user:mod', act='setpasswd', user=iden)

    async def setUserLocked(self, iden, locked):
        user = await self.auth.reqUser(iden)
        await user.setLocked(locked)
        await self.fire('user:mod', act='locked', user=iden, locked=locked)

    async def setUserArchived(self, iden, archived):
        user = await self.auth.reqUser(iden)
        await user.setArchived(archived)
        await self.fire('user:mod', act='archived', user=iden, archived=archived)

    async def getUserDef(self, iden):
        user = self.auth.user(iden)
        if user is not None:
            return user.pack(packroles=True)

    async def getAuthGate(self, iden):
        gate = self.auth.getAuthGate(iden)
        if gate is None:
            return None
        return gate.pack()

    async def getAuthGates(self):
        return [g.pack() for g in self.auth.getAuthGates()]

    async def getRoleDef(self, iden):
        role = self.auth.role(iden)
        if role is not None:
            return role.pack()

    async def getUserDefByName(self, name):
        user = await self.auth.getUserByName(name)
        if user is not None:
            return user.pack(packroles=True)

    async def getRoleDefByName(self, name):
        role = await self.auth.getRoleByName(name)
        if role is not None:
            return role.pack()

    async def getUserDefs(self):
        return [u.pack(packroles=True) for u in self.auth.users()]

    async def getRoleDefs(self):
        return [r.pack() for r in self.auth.roles()]

    async def getAuthUsers(self, archived=False):
        return [u.pack() for u in self.auth.users() if archived or not u.info.get('archived')]

    async def getAuthRoles(self):
        return [r.pack() for r in self.auth.roles()]

    async def dyniter(self, iden, todo, gatekeys=()):

        for useriden, perm, gateiden in gatekeys:
            (await self.auth.reqUser(useriden)).confirm(perm, gateiden=gateiden)

        item = self.dynitems.get(iden)
        name, args, kwargs = todo

        meth = getattr(item, name)
        async for item in meth(*args, **kwargs):
            yield item

    async def dyncall(self, iden, todo, gatekeys=()):

        for useriden, perm, gateiden in gatekeys:
            (await self.auth.reqUser(useriden)).confirm(perm, gateiden=gateiden)

        item = self.dynitems.get(iden)
        if item is None:
            raise s_exc.NoSuchIden(mesg=iden)

        name, args, kwargs = todo
        meth = getattr(item, name)

        return await s_coro.ornot(meth, *args, **kwargs)

    async def getConfOpt(self, name):
        return self.conf.get(name)

    def _getSessInfo(self, iden):
        return self.sessstor.gen(iden)

    def getUserName(self, iden, defv='<unknown>'):
        '''
        Translate the user iden to a user name.
        '''
        # since this pattern is so common, utilitizing...
        user = self.auth.user(iden)
        if user is None:
            return defv
        return user.name

    async def genHttpSess(self, iden):

        # TODO age out http sessions
        sess = self.sessions.get(iden)
        if sess is not None:
            return sess

        sess = await s_httpapi.Sess.anit(self, iden)
        self.sessions[iden] = sess

        return sess

    async def addHttpsPort(self, port, host='0.0.0.0', sslctx=None):

        addr = socket.gethostbyname(host)

        if sslctx is None:

            pkeypath = os.path.join(self.dirn, 'sslkey.pem')
            certpath = os.path.join(self.dirn, 'sslcert.pem')

            if not os.path.isfile(certpath):
                logger.warning('NO CERTIFICATE FOUND! generating self-signed certificate.')
                with s_common.getTempDir() as dirn:
                    cdir = s_certdir.CertDir(path=(dirn,))
                    pkey, cert = cdir.genHostCert(self.getCellType())
                    cdir.savePkeyPem(pkey, pkeypath)
                    cdir.saveCertPem(cert, certpath)

            sslctx = self.initSslCtx(certpath, pkeypath)

        serv = self.wapp.listen(port, address=addr, ssl_options=sslctx)
        self.httpds.append(serv)
        return list(serv._sockets.values())[0].getsockname()

    def initSslCtx(self, certpath, keypath):

        sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sslctx.minimum_version = ssl.TLSVersion.TLSv1_2

        if not os.path.isfile(keypath):
            raise s_exc.NoSuchFile(name=keypath)

        if not os.path.isfile(certpath):
            raise s_exc.NoSuchFile(name=certpath)

        sslctx.load_cert_chain(certpath, keypath)
        return sslctx

    async def _initCellHttp(self):

        self.httpds = []
        self.sessstor = s_lmdbslab.GuidStor(self.slab, 'http:sess')

        async def fini():
            [await s.fini() for s in self.sessions.values()]
            for http in self.httpds:
                http.stop()

        self.onfini(fini)

        # Generate/Load a Cookie Secret
        secpath = os.path.join(self.dirn, 'cookie.secret')
        if not os.path.isfile(secpath):
            with s_common.genfile(secpath) as fd:
                fd.write(s_common.guid().encode('utf8'))

        with s_common.getfile(secpath) as fd:
            secret = fd.read().decode('utf8')

        opts = {
            'cookie_secret': secret,
            'websocket_ping_interval': 10
        }

        self.wapp = t_web.Application(**opts)
        self._initCellHttpApis()

    def _initCellHttpApis(self):

        self.addHttpApi('/robots.txt', s_httpapi.RobotHandler, {'cell': self})
        self.addHttpApi('/api/v1/login', s_httpapi.LoginV1, {'cell': self})
        self.addHttpApi('/api/v1/active', s_httpapi.ActiveV1, {'cell': self})
        self.addHttpApi('/api/v1/healthcheck', s_httpapi.HealthCheckV1, {'cell': self})

        self.addHttpApi('/api/v1/auth/users', s_httpapi.AuthUsersV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/roles', s_httpapi.AuthRolesV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/adduser', s_httpapi.AuthAddUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/addrole', s_httpapi.AuthAddRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/delrole', s_httpapi.AuthDelRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/user/(.*)', s_httpapi.AuthUserV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/role/(.*)', s_httpapi.AuthRoleV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/password/(.*)', s_httpapi.AuthUserPasswdV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/grant', s_httpapi.AuthGrantV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/revoke', s_httpapi.AuthRevokeV1, {'cell': self})
        self.addHttpApi('/api/v1/auth/onepass/issue', s_httpapi.OnePassIssueV1, {'cell': self})

    def addHttpApi(self, path, ctor, info):
        self.wapp.add_handlers('.*', (
            (path, ctor, info),
        ))

    async def _initCertDir(self):

        certpath = s_common.gendir(self.dirn, 'certs')

        # add our cert path to the global resolver
        s_certdir.addCertPath(certpath)

        async def fini():
            s_certdir.delCertPath(certpath)
        self.onfini(fini)

        # our certdir is *only* the cell certs dir
        self.certdir = s_certdir.CertDir(path=(certpath,))

    async def _initCellDmon(self):

        self.dmon = await s_daemon.Daemon.anit()
        self.dmon.share('*', self)

        self.onfini(self.dmon.fini)

    async def _initCellHive(self):
        isnew = not self.slab.dbexists('hive')

        db = self.slab.initdb('hive')
        hive = await s_hive.SlabHive.anit(self.slab, db=db, nexsroot=self.nexsroot)
        self.onfini(hive)

        if isnew:
            path = os.path.join(self.dirn, 'hiveboot.yaml')
            if os.path.isfile(path):
                logger.debug(f'Loading cell hive from {path}')
                tree = s_common.yamlload(path)
                if tree is not None:
                    # Pack and unpack the tree to avoid tuple/list issues
                    # for in-memory structures.
                    tree = s_common.tuplify(tree)
                    await hive.loadHiveTree(tree)

        return hive

    async def _initCellSlab(self, readonly=False):

        s_common.gendir(self.dirn, 'slabs')

        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        if not os.path.exists(path) and readonly:
            logger.warning('Creating a slab for a readonly cell.')
            _slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE)
            _slab.initdb('hive')
            await _slab.fini()

        self.slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE, readonly=readonly)
        self.onfini(self.slab.fini)

    async def _initCellAuth(self):

        authctor = self.conf.get('auth:ctor')
        if authctor is not None:
            ctor = s_dyndeps.getDynLocal(authctor)
            return await ctor(self)

        return await self._initCellHiveAuth()

    async def _initCellHiveAuth(self):

        node = await self.hive.open(('auth',))
        auth = await s_hiveauth.Auth.anit(node, nexsroot=self.nexsroot)

        self.onfini(auth.fini)
        return auth

    @contextlib.asynccontextmanager
    async def getLocalProxy(self, share='*', user='root'):
        url = self.getLocalUrl(share=share, user=user)
        prox = await s_telepath.openurl(url)
        yield prox

    def getLocalUrl(self, share='*', user='root'):
        return f'cell://{user}@{self.dirn}:{share}'

    def _initCellConf(self, conf):
        if isinstance(conf, dict):
            conf = s_config.Config.getConfFromCell(self, conf=conf)
        for k, v in self._loadCellYaml('cell.yaml').items():
            conf.setdefault(k, v)
        conf.reqConfValid()
        return conf

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    async def getTeleApi(self, link, mesg, path):

        # if auth is disabled or it's a unix socket, they're root.
        if link.get('unix'):
            name = 'root'
            auth = mesg[1].get('auth')
            if auth is not None:
                name, info = auth

            user = await self.auth.getUserByName(name)
            if user is None:
                raise s_exc.NoSuchUser(name=name)

        else:
            user = await self._getCellUser(link, mesg)

        return await self.getCellApi(link, user, path)

    async def getCellApi(self, link, user, path):
        return await self.cellapi.anit(self, link, user)

    async def getLogExtra(self, **kwargs):
        '''
        Get an extra dictionary for structured logging which can be used as a extra argument for loggers.

        Args:
            **kwargs: Additional key/value items to add to the log.

        Returns:
            Dict: A dictionary
        '''
        extra = {**kwargs}
        sess = s_scope.get('sess')
        if sess and sess.user:
            extra['user'] = sess.user.iden
            extra['username'] = sess.user.name
        return {'synapse': extra}

    async def _getSpawnLogConf(self):
        conf = self.conf.get('_log_conf')
        if conf:
            return conf
        return s_common._getLogConfFromEnv()

    @classmethod
    def getCellType(cls):
        return cls.__name__.lower()

    @classmethod
    def getEnvPrefix(cls):
        return f'SYN_{cls.__name__.upper()}'

    def getCellIden(self):
        return self.iden

    @classmethod
    def initCellConf(cls):
        '''
        Create a Config object for the Cell.

        Notes:
            The Config object has a ``envar_prefix`` set according to the results of ``cls.getEnvPrefix()``.

        Returns:
            s_config.Config: A Config helper object.
        '''
        prefix = cls.getEnvPrefix()
        schema = s_config.getJsSchema(cls.confbase, cls.confdefs)
        return s_config.Config(schema, envar_prefix=prefix)

    @classmethod
    def getArgParser(cls, conf=None):
        '''
        Get an ``argparse.ArgumentParser`` for the Cell.

        Args:
            conf (s_config.Config): Optional, a Config object which

        Notes:
            Boot time configuration data is placed in the argument group called ``config``.
            This adds default ``dirn``, ``--telepath``, ``--https`` and ``--name`` arguements to the argparser instance.
            Configuration values which have the ``hideconf`` or ``hidecmdl`` value set to True are not added to the
            argparser instance.

        Returns:
            argparse.ArgumentParser: A ArgumentParser for the Cell.
        '''

        name = cls.getCellType()
        prefix = cls.getEnvPrefix()

        pars = argparse.ArgumentParser(prog=name)
        pars.add_argument('dirn', help=f'The storage directory for the {name} service.')

        pars.add_argument('--log-level', default='INFO', choices=list(s_const.LOG_LEVEL_CHOICES.keys()),
                          help='Specify the Python logging log level.', type=str.upper)
        pars.add_argument('--structured-logging', default=False, action='store_true',
                          help='Use structured logging.')

        telendef = None
        telepdef = 'tcp://0.0.0.0:27492'
        httpsdef = 4443
        telenvar = '_'.join((prefix, 'NAME'))
        telepvar = '_'.join((prefix, 'TELEPATH'))
        httpsvar = '_'.join((prefix, 'HTTPS'))
        telen = os.getenv(telenvar, telendef)
        telep = os.getenv(telepvar, telepdef)
        https = os.getenv(httpsvar, httpsdef)

        pars.add_argument('--telepath', default=telep, type=str,
                          help=f'The telepath URL to listen on. This defaults to {telepdef}, and may be '
                               f'also be overridden by the {telepvar} environment variable.')
        pars.add_argument('--https', default=https, type=int,
                          help=f'The port to bind for the HTTPS/REST API. This defaults to {httpsdef}, '
                               f'and may be also be overridden by the {httpsvar} environment variable.')
        pars.add_argument('--name', type=str, default=telen,
                          help=f'The (optional) additional name to share the {name} as. This defaults to '
                               f'{telendef}, and may be also be overridden by the {telenvar} environment'
                               f' variable.')

        if conf is not None:
            args = conf.getArgParseArgs()
            if args:
                pgrp = pars.add_argument_group('config', 'Configuration arguments.')
                for (argname, arginfo) in args:
                    pgrp.add_argument(argname, **arginfo)

        return pars

    @classmethod
    async def initFromArgv(cls, argv, outp=None):
        '''
        Cell launcher which does automatic argument parsing, environment variable resolution and Cell creation.

        Args:
            argv (list): A list of command line arguments to launch the Cell with.
            outp (s_ouput.OutPut): Optional, an output object. No longer used in the default implementation.

        Notes:
            This does the following items:
                - Create a Config object from the Cell class.
                - Creates an Argument Parser from the Cell class and Config object.
                - Parses the provided arguments.
                - Loads configuration data from the parsed options and environment variables.
                - Sets logging for the process.
                - Creates the Cell from the Cell Ctor.
                - Adds a Telepath listener, HTTPs port listeners and Telepath share names.
                - Returns the Cell.

        Returns:
            Cell: This returns an instance of the Cell.
        '''

        conf = cls.initCellConf()
        pars = cls.getArgParser(conf=conf)

        opts = pars.parse_args(argv)

        logconf = s_common.setlogging(logger, defval=opts.log_level,
                                      structlog=opts.structured_logging)
        conf.setdefault('_log_conf', logconf)
        conf.setConfFromOpts(opts)
        conf.setConfFromEnvs()

        s_coro.set_pool_logging(logger, logconf=conf['_log_conf'])

        cell = await cls.anit(opts.dirn, conf=conf)

        try:

            if 'dmon:listen' not in cell.conf:
                await cell.dmon.listen(opts.telepath)
                logger.info(f'...{cell.getCellType()} API (telepath): {opts.telepath}')
            else:
                lisn = cell.conf.get('dmon:listen')
                if lisn is None:
                    lisn = cell.getLocalUrl()

                logger.info(f'...{cell.getCellType()} API (telepath): {lisn}')

            if 'https:port' not in cell.conf:
                await cell.addHttpsPort(opts.https)
                logger.info(f'...{cell.getCellType()} API (https): {opts.https}')
            else:
                port = cell.conf.get('https:port')
                if port is None:
                    logger.info(f'...{cell.getCellType()} API (https): disabled')
                else:
                    logger.info(f'...{cell.getCellType()} API (https): {port}')

            if opts.name is not None:
                cell.dmon.share(opts.name, cell)
                logger.info(f'...{cell.getCellType()} API (telepath name): {opts.name}')

        except (asyncio.CancelledError, Exception):
            await cell.fini()
            raise

        return cell

    @classmethod
    async def execmain(cls, argv, outp=None):
        '''
        The main entry point for running the Cell as an application.

        Args:
            argv (list): A list of command line arguments to launch the Cell with.
            outp (s_ouput.OutPut): Optional, an output object. No longer used in the default implementation.

        Notes:
            This coroutine waits until the Cell is fini'd or a SIGINT/SIGTERM signal is sent to the process.

        Returns:
            None.
        '''

        if outp is None:
            outp = s_output.stdout

        cell = await cls.initFromArgv(argv, outp=outp)

        await cell.main()

    async def _getCellUser(self, link, mesg):

        # check for a TLS client cert
        username = link.getTlsPeerCn()
        if username is not None:
            user = await self.auth.getUserByName(username)
            if user is not None:
                return user

            logger.warning(f'TLS Client Cert User NOT FOUND: {username}')

        auth = mesg[1].get('auth')
        if auth is None:

            anonuser = self.conf.get('auth:anon')
            if anonuser is None:
                raise s_exc.AuthDeny(mesg='Unable to find cell user')

            user = await self.auth.getUserByName(anonuser)
            if user is None:
                raise s_exc.AuthDeny(mesg=f'Anon user ({anonuser}) is not found.')

            if user.isLocked():
                raise s_exc.AuthDeny(mesg=f'Anon user ({anonuser}) is locked.')

            return user

        name, info = auth

        user = await self.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(name=name, mesg=f'No such user: {name}.')

        # passwd None always fails...
        passwd = info.get('passwd')

        if not await user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', user=user.name)

        return user

    async def getHealthCheck(self):
        health = s_health.HealthCheck(self.getCellIden())
        for func in self._health_funcs:
            await func(health)
        return health.pack()

    def addHealthFunc(self, func):
        '''Register a callback function to get a HealthCheck object.'''
        self._health_funcs.append(func)

    async def _cellHealth(self, health):
        pass

    async def getDmonSessions(self):
        return await self.dmon.getSessInfo()

    # ----- Change distributed Auth methods ----

    async def listHiveKey(self, path=None):
        if path is None:
            path = ()
        items = self.hive.dir(path)
        if items is None:
            return None
        return [item[0] for item in items]

    async def getHiveKeys(self, path):
        '''
        Return a list of (name, value) tuples for nodes under the path.
        '''
        items = self.hive.dir(path)
        if items is None:
            return ()

        return [(i[0], i[1]) for i in items]

    async def getHiveKey(self, path):
        '''
        Get the value of a key in the cell default hive
        '''
        return await self.hive.get(path)

    async def setHiveKey(self, path, valu):
        '''
        Set or change the value of a key in the cell default hive
        '''
        return await self.hive.set(path, valu, nexs=True)

    async def popHiveKey(self, path):
        '''
        Remove and return the value of a key in the cell default hive.

        Note:  this is for expert emergency use only.
        '''
        return await self.hive.pop(path, nexs=True)

    async def saveHiveTree(self, path=()):
        return await self.hive.saveHiveTree(path=path)

    async def loadHiveTree(self, tree, path=(), trim=False):
        '''
        Note:  this is for expert emergency use only.
        '''
        return await self._push('hive:loadtree', tree, path, trim)

    @s_nexus.Pusher.onPush('hive:loadtree')
    async def _onLoadHiveTree(self, tree, path, trim):
        return await self.hive.loadHiveTree(tree, path=path, trim=trim)

    @s_nexus.Pusher.onPushAuto('sync')
    async def sync(self):
        '''
        no-op mutable for testing purposes.  If I am follower, when this returns, I have received and applied all
        the writes that occurred on the leader before this call.
        '''
        return

    async def ps(self, user):
        isallowed = await self.isUserAllowed(user.iden, ('task', 'get'))

        retn = []
        for task in self.boss.ps():
            if (task.user.iden == user.iden) or isallowed:
                retn.append(task.pack())

        return retn

    async def kill(self, user, iden):
        perm = ('task', 'del')
        isallowed = await self.isUserAllowed(user.iden, perm)

        logger.info(f'User [{user.name}] Requesting task kill: {iden}')
        task = self.boss.get(iden)
        if task is None:
            logger.info(f'Task does not exist: {iden}')
            return False

        if (task.user.iden == user.iden) or isallowed:
            logger.info(f'Killing task: {iden}')
            await task.kill()
            logger.info(f'Task killed: {iden}')
            return True

        perm = '.'.join(perm)
        raise s_exc.AuthDeny(mesg=f'User must have permission {perm} or own the task',
                             task=iden, user=str(user), perm=perm)

    async def getCellInfo(self):
        '''
        Return metadata specific for the Cell.

        Notes:
            By default, this function returns information about the base Cell
            implementation, which reflects the base information in the Synapse
            Cell.

            It is expected that implementers override the following Class
            attributes in order to provide meaningful version information:

            ``COMMIT``  - A Git Commit
            ``VERSION`` - A Version tuple.
            ``VERSTRING`` - A Version string.

        Returns:
            Dict: A Dictionary of metadata.
        '''
        ret = {
            'synapse': {
                'commit': s_version.commit,
                'version': s_version.version,
                'verstring': s_version.verstring,
            },
            'cell': {
                'type': self.getCellType(),
                'iden': self.getCellIden(),
                'active': self.isactive,
                'commit': self.COMMIT,
                'version': self.VERSION,
                'verstring': self.VERSTRING,
                'cellvers': dict(self.cellvers.items()),
            }
        }
        return ret

    async def getSystemInfo(self):
        '''
        Get info about the system in which the cell is running

        Returns:
            A dictionary with the following keys.  All size values are in bytes:
                - volsize - Volume where cell is running total space
                - volfree - Volume where cell is running free space
                - backupvolsize - Backup directory volume total space
                - backupvolfree - Backup directory volume free space
                - cellstarttime - Cell start time in epoch milliseconds
                - celluptime - Cell uptime in milliseconds
                - cellrealdisk - Cell's use of disk, equivalent to du
                - cellapprdisk - Cell's apparent use of disk, equivalent to ls -l
                - osversion - OS version/architecture
                - pyversion - Python version
                - totalmem - Total memory in the system
                - availmem - Available memory in the system
                - cpucount - Number of CPUs on system
        '''
        uptime = int((time.monotonic() - self.starttime) * 1000)
        disk = shutil.disk_usage(self.dirn)

        if self.backdirn:
            backupdisk = shutil.disk_usage(self.backdirn)
            backupvolsize, backupvolfree = backupdisk.total, backupdisk.free
        else:
            backupvolsize, backupvolfree = 0, 0

        myusage, myappusage = s_common.getDirSize(self.dirn)
        totalmem = s_thisplat.getTotalMemory()
        availmem = s_thisplat.getAvailableMemory()
        pyversion = platform.python_version()
        cpucount = multiprocessing.cpu_count()

        retn = {
            'volsize': disk.total,             # Volume where cell is running total bytes
            'volfree': disk.free,              # Volume where cell is running free bytes
            'backupvolsize': backupvolsize,    # Cell's backup directory volume total bytes
            'backupvolfree': backupvolfree,    # Cell's backup directory volume free bytes
            'cellstarttime': self.startms,     # cell start time in epoch millis
            'celluptime': uptime,              # cell uptime in ms
            'cellrealdisk': myusage,           # Cell's use of disk, equivalent to du
            'cellapprdisk': myappusage,        # Cell's apparent use of disk, equivalent to ls -l
            'osversion': platform.platform(),  # OS version/architecture
            'pyversion': pyversion,            # Python version
            'totalmem': totalmem,              # Total memory in the system
            'availmem': availmem,              # Available memory in the system
            'cpucount': cpucount,              # Number of CPUs on system
        }

        return retn
