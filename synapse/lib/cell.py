import gc
import os
import ssl
import copy
import time
import fcntl
import shutil
import signal
import socket
import asyncio
import logging
import tarfile
import argparse
import datetime
import platform
import tempfile
import functools
import contextlib
import multiprocessing

import aiohttp
import tornado.web as t_web
import tornado.log as t_log

import synapse.exc as s_exc

import synapse.data as s_data
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.auth as s_auth
import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.link as s_link
import synapse.lib.task as s_task
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.drive as s_drive
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config
import synapse.lib.health as s_health
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.spooled as s_spooled
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.version as s_version
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.thisplat as s_thisplat

import synapse.lib.crypto.passwd as s_passwd

import synapse.tools.backup as s_t_backup

logger = logging.getLogger(__name__)

NEXUS_VERSION = (2, 198)

SLAB_MAP_SIZE = 128 * s_const.mebibyte
SSLCTX_CACHE_SIZE = 64

'''
Base classes for the synapse "cell" microservice architecture.
'''

PERM_DENY = 0
PERM_READ = 1
PERM_EDIT = 2
PERM_ADMIN = 3

permnames = {
    PERM_DENY: 'deny',
    PERM_READ: 'read',
    PERM_EDIT: 'edit',
    PERM_ADMIN: 'admin',
}

feat_aha_callpeers_v1 = ('callpeers', 1)

diskspace = "Insufficient free space on disk."

def adminapi(log=False):
    '''
    Decorator for CellApi (and subclasses) for requiring a method to be called only by an admin user.

    Args:
        log (bool): If set to True, log the user, function and arguments.
    '''

    def decrfunc(func):

        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):

            if self.user is not None and not self.user.isAdmin():
                raise s_exc.AuthDeny(mesg=f'User is not an admin [{self.user.name}]',
                                     user=self.user.iden, username=self.user.name)
            if log:
                logger.info(f'Executing [{func.__qualname__}] as [{self.user.name}] with args [{args}[{kwargs}]',
                            extra={'synapse': {'wrapped_func': func.__qualname__}})

            return func(self, *args, **kwargs)

        wrapped.__syn_wrapped__ = 'adminapi'

        return wrapped

    return decrfunc

def from_leader(func):
    '''
    Decorator used to indicate that the decorated method must call up to the
    leader to perform it's work.

    This only works on Cell classes and subclasses. The decorated method name
    MUST be the same as the telepath API name.
    '''
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.isactive:
            proxy = await self.nexsroot.client.proxy()
            api = getattr(proxy, func.__name__)
            return await api(*args, **kwargs)

        return await func(self, *args, **kwargs)

    return wrapper

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
        # TODO: When we are 3.12+ convert this back to w|gz - see https://github.com/python/cpython/pull/2962
        with tarfile.open(output_filename, 'w:gz', fileobj=fd, compresslevel=1) as tar:
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

    @adminapi(log=True)
    async def freeze(self, timeout=30):
        return await self.cell.freeze(timeout=timeout)

    @adminapi(log=True)
    async def resume(self):
        return await self.cell.resume()

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
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, username=self.user.name, user=self.user.iden)

    def getCellType(self):
        return self.cell.getCellType()

    def getCellIden(self):
        return self.cell.getCellIden()

    async def getCellRunId(self):
        return await self.cell.getCellRunId()

    async def isCellActive(self):
        '''
        Returns True if the cell is an active/leader cell.
        '''
        return await self.cell.isCellActive()

    def getPermDef(self, perm):
        '''
        Return a specific permission definition.
        '''
        return self.cell.getPermDef(perm)

    def getPermDefs(self):
        '''
        Return a non-comprehensive list of perm definitions.
        '''
        return self.cell.getPermDefs()

    @adminapi()
    def getNexsIndx(self):
        return self.cell.getNexsIndx()

    @adminapi()
    async def readyToMirror(self):
        return await self.cell.readyToMirror()

    @adminapi()
    async def getMirrorUrls(self):
        return await self.cell.getMirrorUrls()

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

    @adminapi(log=True)
    async def promote(self, graceful=False):
        return await self.cell.promote(graceful=graceful)

    @adminapi(log=True)
    async def handoff(self, turl, timeout=30):
        return await self.cell.handoff(turl, timeout=timeout)

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
            raise s_exc.AuthDeny(mesg=mesg, user=self.user.iden, username=self.user.name)

        user = self.cell.auth.user(iden)
        if user is None:
            raise s_exc.NoSuchUser(mesg=f'Unable to set cell user iden to {iden}', user=iden)

        if user.isLocked():
            raise s_exc.AuthDeny(mesg=f'User ({user.name}) is locked.', user=user.iden, username=user.name)

        self.user = user
        self.link.get('sess').user = user
        return True

    async def ps(self):
        return await self.cell.ps(self.user)

    async def kill(self, iden):
        return await self.cell.kill(self.user, iden)

    @adminapi()
    async def getTasks(self, peers=True, timeout=None):
        async for task in self.cell.getTasks(peers=peers, timeout=timeout):
            yield task

    @adminapi()
    async def getTask(self, iden, peers=True, timeout=None):
        return await self.cell.getTask(iden, peers=peers, timeout=timeout)

    @adminapi()
    async def killTask(self, iden, peers=True, timeout=None):
        return await self.cell.killTask(iden, peers=peers, timeout=timeout)

    @adminapi(log=True)
    async def behold(self):
        '''
        Yield Cell system messages
        '''
        async for mesg in self.cell.behold():
            yield mesg

    @adminapi(log=True)
    async def addUser(self, name, passwd=None, email=None, iden=None):
        return await self.cell.addUser(name, passwd=passwd, email=email, iden=iden)

    @adminapi(log=True)
    async def delUser(self, iden):
        return await self.cell.delUser(iden)

    @adminapi(log=True)
    async def addRole(self, name, iden=None):
        return await self.cell.addRole(name, iden=iden)

    @adminapi(log=True)
    async def delRole(self, iden):
        return await self.cell.delRole(iden)

    async def addUserApiKey(self, name, duration=None, useriden=None):
        if useriden is None:
            useriden = self.user.iden

        if self.user.iden == useriden:
            self.user.confirm(('auth', 'self', 'set', 'apikey'), default=True)
        else:
            self.user.confirm(('auth', 'user', 'set', 'apikey'))

        return await self.cell.addUserApiKey(useriden, name, duration=duration)

    async def listUserApiKeys(self, useriden=None):
        if useriden is None:
            useriden = self.user.iden

        if self.user.iden == useriden:
            self.user.confirm(('auth', 'self', 'set', 'apikey'), default=True)
        else:
            self.user.confirm(('auth', 'user', 'set', 'apikey'))

        return await self.cell.listUserApiKeys(useriden)

    async def delUserApiKey(self, iden):
        apikey = await self.cell.getUserApiKey(iden)
        if apikey is None:
            mesg = f'User API key with {iden=} does not exist.'
            raise s_exc.NoSuchIden(mesg=mesg, iden=iden)

        useriden = apikey.get('user')

        if self.user.iden == useriden:
            self.user.confirm(('auth', 'self', 'set', 'apikey'), default=True)
        else:
            self.user.confirm(('auth', 'user', 'set', 'apikey'))

        return await self.cell.delUserApiKey(iden)

    @adminapi()
    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.cell.dyncall(iden, todo, gatekeys=gatekeys)

    @adminapi()
    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.cell.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    @adminapi()
    async def issue(self, nexsiden: str, event: str, args, kwargs, meta=None):
        return await self.cell.nexsroot.issue(nexsiden, event, args, kwargs, meta)

    @adminapi(log=True)
    async def delAuthUser(self, name):
        await self.cell.auth.delUser(name)

    @adminapi(log=True)
    async def addAuthRole(self, name):
        role = await self.cell.auth.addRole(name)
        return role.pack()

    @adminapi(log=True)
    async def delAuthRole(self, name):
        await self.cell.auth.delRole(name)

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
        '''This API is deprecated.'''
        s_common.deprecated('CellApi.getAuthInfo')
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
        '''This API is deprecated.'''
        s_common.deprecated('CellApi.addAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.addRule(rule, indx=indx, gateiden=gateiden)

    @adminapi(log=True)
    async def delAuthRule(self, name, rule, gateiden=None):
        '''This API is deprecated.'''
        s_common.deprecated('CellApi.delAuthRule')
        item = await self.cell.auth.getUserByName(name)
        if item is None:
            item = await self.cell.auth.getRoleByName(name)
        await item.delRule(rule, gateiden=gateiden)

    @adminapi(log=True)
    async def setAuthAdmin(self, name, isadmin):
        '''This API is deprecated.'''
        s_common.deprecated('CellApi.setAuthAdmin')
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

    @adminapi()
    async def genUserOnepass(self, iden, duration=60000):
        return await self.cell.genUserOnepass(iden, duration)

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
    async def addUserRole(self, useriden, roleiden, indx=None):
        return await self.cell.addUserRole(useriden, roleiden, indx=indx)

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
        raise s_exc.AuthDeny(mesg=mesg, user=self.user.iden, username=self.user.name)

    async def getRoleInfo(self, name):
        role = await self.cell.auth.reqRoleByName(name)
        if self.user.isAdmin() or role.iden in self.user.info.get('roles', ()):
            return role.pack()

        mesg = 'getRoleInfo denied for non-admin and non-member'
        raise s_exc.AuthDeny(mesg=mesg, user=self.user.iden, username=self.user.name)

    @adminapi()
    async def getUserDef(self, iden, packroles=True):
        return await self.cell.getUserDef(iden, packroles=packroles)

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
    async def isUserAllowed(self, iden, perm, gateiden=None, default=False):
        return await self.cell.isUserAllowed(iden, perm, gateiden=gateiden, default=default)

    @adminapi()
    async def isRoleAllowed(self, iden, perm, gateiden=None):
        return await self.cell.isRoleAllowed(iden, perm, gateiden=gateiden)

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

    @adminapi()
    async def popUserProfInfo(self, iden, name, default=None):
        return await self.cell.popUserProfInfo(iden, name, default=default)

    @adminapi()
    async def checkUserApiKey(self, key):
        return await self.cell.checkUserApiKey(key)

    async def getHealthCheck(self):
        await self._reqUserAllowed(('health',))
        return await self.cell.getHealthCheck()

    @adminapi()
    async def getDmonSessions(self):
        return await self.cell.getDmonSessions()

    @adminapi()
    async def listHiveKey(self, path=None):
        s_common.deprecated('CellApi.listHiveKey', curv='2.167.0')
        return await self.cell.listHiveKey(path=path)

    @adminapi(log=True)
    async def getHiveKeys(self, path):
        s_common.deprecated('CellApi.getHiveKeys', curv='2.167.0')
        return await self.cell.getHiveKeys(path)

    @adminapi(log=True)
    async def getHiveKey(self, path):
        s_common.deprecated('CellApi.getHiveKey', curv='2.167.0')
        return await self.cell.getHiveKey(path)

    @adminapi(log=True)
    async def setHiveKey(self, path, valu):
        s_common.deprecated('CellApi.setHiveKey', curv='2.167.0')
        return await self.cell.setHiveKey(path, valu)

    @adminapi(log=True)
    async def popHiveKey(self, path):
        s_common.deprecated('CellApi.popHiveKey', curv='2.167.0')
        return await self.cell.popHiveKey(path)

    @adminapi(log=True)
    async def saveHiveTree(self, path=()):
        s_common.deprecated('CellApi.saveHiveTree', curv='2.167.0')
        return await self.cell.saveHiveTree(path=path)

    @adminapi()
    async def getNexusChanges(self, offs, tellready=False, wait=True):
        async for item in self.cell.getNexusChanges(offs, tellready=tellready, wait=wait):
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
        if False:  # pragma: no cover
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
        if False:  # pragma: no cover
            yield

    @adminapi()
    async def getDiagInfo(self):
        return {
            'slabs': await s_lmdbslab.Slab.getSlabStats(),
        }

    @adminapi()
    async def runGcCollect(self, generation=2):
        '''
        For diagnostic purposes only!

        NOTE: This API is *not* supported and can be removed at any time!
        '''
        return gc.collect(generation=generation)

    @adminapi()
    async def getGcInfo(self):
        '''
        For diagnostic purposes only!

        NOTE: This API is *not* supported and can be removed at any time!
        '''
        return {
            'stats': gc.get_stats(),
            'threshold': gc.get_threshold(),
        }

    @adminapi()
    async def getReloadableSystems(self):
        return self.cell.getReloadableSystems()

    @adminapi(log=True)
    async def reload(self, subsystem=None):
        return await self.cell.reload(subsystem=subsystem)

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
            'description': 'An optional hard-coded GUID to store as the permanent GUID for the service.',
            'type': 'string',
            'hideconf': True,
        },
        'cell:ctor': {
            'description': 'An optional python path to the Cell class.  Used by stemcell.',
            'type': 'string',
            'hideconf': True,
        },
        'mirror': {
            'description': 'A telepath URL for our upstream mirror (we must be a backup!).',
            'type': ['string', 'null'],
            'hidedocs': True,
            'hidecmdl': True,
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
        'auth:passwd:policy': {
            'description': 'Specify password policy/complexity requirements.',
            'type': 'object',
        },
        'max:users': {
            'default': 0,
            'description': 'Maximum number of users allowed on system, not including root or locked/archived users (0 is no limit).',
            'type': 'integer',
            'minimum': 0
        },
        'nexslog:en': {
            'default': False,
            'description': 'Record all changes to a stream file on disk.  Required for mirroring (on both sides).',
            'type': 'boolean',
        },
        'nexslog:async': {
            'default': True,
            'description': 'Deprecated. This option ignored.',
            'type': 'boolean',
            'hidedocs': True,
            'hidecmdl': True,
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
        'https:parse:proxy:remoteip': {
            'description': 'Enable the HTTPS server to parse X-Forwarded-For and X-Real-IP headers to determine requester IP addresses.',
            'type': 'boolean',
            'default': False,
        },
        'backup:dir': {
            'description': 'A directory outside the service directory where backups will be saved. Defaults to ./backups in the service storage directory.',
            'type': 'string',
        },
        'onboot:optimize': {
            'default': False,
            'description': 'Delay startup to optimize LMDB databases during boot to recover free space and increase performance. This may take a while.',
            'type': 'boolean',
        },
        'limit:disk:free': {
            'default': 5,
            'description': 'Minimum disk free space percentage before setting the cell read-only.',
            'type': ['integer', 'null'],
            'minimum': 0,
            'maximum': 100,
        },
        'health:sysctl:checks': {
            'default': True,
            'description': 'Enable sysctl parameter checks and warn if values are not optimal.',
            'type': 'boolean',
        },
        'aha:name': {
            'description': 'The name of the cell service in the aha service registry.',
            'type': 'string',
        },
        'aha:user': {
            'description': 'The username of this service when connecting to others.',
            'type': 'string',
        },
        'aha:leader': {
            'description': 'The AHA service name to claim as the active instance of a storm service.',
            'type': 'string',
        },
        'aha:network': {
            'description': 'The AHA service network.',
            'type': 'string',
        },
        'aha:registry': {
            'description': 'The telepath URL of the aha service registry.',
            'type': ['string', 'array'],
            'items': {'type': 'string'},
        },
        'aha:provision': {
            'description': 'The telepath URL of the aha provisioning service.',
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
            'hidedocs': True,
            'hidecmdl': True,
        },
        'inaugural': {
            'description': 'Data used to drive configuration of the service upon first startup.',
            'type': 'object',
            'properties': {
                'roles': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string',
                                     'pattern': '^(?!all$).+$',
                                     },
                            'rules': {
                                'type': 'array',
                                'items': {
                                    'type': 'array',
                                    'items': [
                                        {'type': 'boolean'},
                                        {'type': 'array', 'items': {'type': 'string'}, },
                                    ],
                                    'minItems': 2,
                                    'maxItems': 2,
                                },
                            }
                        },
                        'required': ['name', ],
                        'additionalProperties': False,
                    }
                },
                'users': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string',
                                     'pattern': '^(?!root$).+$',
                                     },
                            'admin': {'type': 'boolean', 'default': False, },
                            'email': {'type': 'string', },
                            'roles': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'rules': {
                                'type': 'array',
                                'items': {
                                    'type': 'array',
                                    'items': [
                                        {'type': 'boolean'},
                                        {'type': 'array', 'items': {'type': 'string'}, },
                                    ],
                                    'minItems': 2,
                                    'maxItems': 2,
                                },
                            },
                        },
                        'required': ['name', ],
                        'additionalProperties': False,
                    }
                }
            },
            'hidedocs': True,
        },
        '_log_conf': {
            'description': 'Opaque structure used for logging by spawned processes.',
            'type': 'object',
            'hideconf': True
        }
    }

    BACKUP_SPAWN_TIMEOUT = 60.0
    FREE_SPACE_CHECK_FREQ = 60.0

    COMMIT = s_version.commit
    VERSION = s_version.version
    VERSTRING = s_version.verstring

    SYSCTL_VALS = {
        'vm.dirty_expire_centisecs': 20,
        'vm.dirty_writeback_centisecs': 20,
    }
    SYSCTL_CHECK_FREQ = 60.0

    LOGGED_HTTPAPI_HEADERS = ('User-Agent',)

    async def __anit__(self, dirn, conf=None, readonly=False, parent=None):

        # phase 1
        if conf is None:
            conf = {}

        self.starttime = time.monotonic()  # Used for uptime calc
        self.startms = s_common.now()      # Used to report start time
        s_telepath.Aware.__init__(self)

        self.dirn = s_common.gendir(dirn)
        self.runid = s_common.guid()

        self.auth = None
        self.cellparent = parent
        self.sessions = {}
        self.paused = False
        self.isactive = False
        self.activebase = None
        self.inaugural = False
        self.activecoros = {}
        self.sockaddr = None  # Default value...
        self.https_listeners = []
        self.ahaclient = None
        self._checkspace = s_coro.Event()
        self._reloadfuncs = {}  # name -> func

        self.nexslock = asyncio.Lock()
        self.netready = asyncio.Event()

        self.conf = self._initCellConf(conf)
        self.features = {
            'tellready': 1,
            'dynmirror': 1,
            'tasks': 1,
        }

        self.minfree = self.conf.get('limit:disk:free')
        if self.minfree is not None:
            self.minfree = self.minfree / 100

            disk = shutil.disk_usage(self.dirn)
            if (disk.free / disk.total) <= self.minfree:
                free = disk.free / disk.total * 100
                mesg = f'Free space on {self.dirn} below minimum threshold (currently {free:.2f}%)'
                raise s_exc.LowSpace(mesg=mesg, dirn=self.dirn)

        self._delTmpFiles()

        if self.conf.get('onboot:optimize'):
            await self._onBootOptimize()

        await self._initCellBoot()

        # we need to know this pretty early...
        self.ahasvcname = None
        ahaname = self.conf.get('aha:name')
        ahanetw = self.conf.get('aha:network')
        if ahaname is not None and ahanetw is not None:
            self.ahasvcname = f'{ahaname}.{ahanetw}'

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

        # read & lock our guid file
        self._cellguidfd = s_common.genfile(path)
        self.iden = self._cellguidfd.read().decode().strip()
        self._getCellLock()

        backdirn = self.conf.get('backup:dir')
        if backdirn is not None:
            backdirn = s_common.genpath(backdirn)
            if backdirn.startswith(self.dirn):
                mesg = 'backup:dir must not be within the service directory'
                raise s_exc.BadConfValu(mesg=mesg)

        else:
            backdirn = s_common.genpath(self.dirn, 'backups')

        backdirn = s_common.gendir(backdirn)

        self.backdirn = backdirn
        self.backuprunning = False  # Whether a backup is currently running
        self.backupstreaming = False  # Whether a temporary new backup is currently streaming
        self.backmonostart = None  # If a backup is running, when did it start (monotonic timer)
        self.backstartdt = None  # Last backup start time
        self.backenddt = None  # Last backup end time
        self.backlasttook = None  # Last backup duration
        self.backlastsize = None  # Last backup size
        self.backlastuploaddt = None  # Last time backup completed uploading via iter{New,}BackupArchive
        self.backlastexc = None  # err, errmsg, errtrace of last backup

        if self.conf.get('mirror') and not self.conf.get('nexslog:en'):
            self.modCellConf({'nexslog:en': True})

        await s_nexus.Pusher.__anit__(self, self.iden)

        self._initCertDir()

        await self.enter_context(s_telepath.loadTeleCell(self.dirn))

        await self._initCellSlab(readonly=readonly)

        # initialize network daemons (but do not listen yet)
        # to allow registration of callbacks and shared objects
        await self._initCellHttp()
        await self._initCellDmon()

        await self.initServiceEarly()

        nexsroot = await self._ctorNexsRoot()

        self.setNexsRoot(nexsroot)

        async def fini():
            await self.nexsroot.fini()

        self.onfini(fini)

        self.apikeydb = self.slab.initdb('user:apikeys')  # apikey -> useriden
        self.usermetadb = self.slab.initdb('user:meta')  # useriden + <valu> -> dict valu
        self.rolemetadb = self.slab.initdb('role:meta')  # roleiden + <valu> -> dict valu

        # for runtime cell configuration values
        self.slab.initdb('cell:conf')

        self._sslctx_cache = s_cache.FixedCache(self._makeCachedSslCtx, size=SSLCTX_CACHE_SIZE)

        self.hive = await self._initCellHive()

        self.cellinfo = self.slab.getSafeKeyVal('cell:info')
        self.cellvers = self.slab.getSafeKeyVal('cell:vers')

        await self._bumpCellVers('cell:storage', (
            (1, self._storCellHiveMigration),
        ), nexs=False)

        if self.inaugural:
            self.cellinfo.set('nexus:version', NEXUS_VERSION)

        # Check the cell version didn't regress
        if (lastver := self.cellinfo.get('cell:version')) is not None and self.VERSION < lastver:
            mesg = f'Cell version regression ({self.getCellType()}) is not allowed! Stored version: {lastver}, current version: {self.VERSION}.'
            logger.error(mesg)
            raise s_exc.BadVersion(mesg=mesg, currver=self.VERSION, lastver=lastver)

        self.cellinfo.set('cell:version', self.VERSION)

        # Check the synapse version didn't regress
        if (lastver := self.cellinfo.get('synapse:version')) is not None and s_version.version < lastver:
            mesg = f'Synapse version regression ({self.getCellType()}) is not allowed! Stored version: {lastver}, current version: {s_version.version}.'
            logger.error(mesg)
            raise s_exc.BadVersion(mesg=mesg, currver=s_version.version, lastver=lastver)

        self.cellinfo.set('synapse:version', s_version.version)

        self.nexsvers = self.cellinfo.get('nexus:version', (0, 0))
        self.nexspatches = ()

        await self._bumpCellVers('cell:storage', (
            (2, self._storCellAuthMigration),
        ), nexs=False)

        self.auth = await self._initCellAuth()

        auth_passwd = self.conf.get('auth:passwd')
        if auth_passwd is not None:
            user = await self.auth.getUserByName('root')

            if not await user.tryPasswd(auth_passwd, nexs=False, enforce_policy=False):
                await user.setPasswd(auth_passwd, nexs=False, enforce_policy=False)

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss)

        self.dynitems = {
            'auth': self.auth,
            'cell': self
        }

        self.permdefs = None
        self.permlook = None

        # initialize web app and callback data structures
        self._health_funcs = []
        self.addHealthFunc(self._cellHealth)

        if self.conf.get('health:sysctl:checks'):
            self.schedCoro(self._runSysctlLoop())

        # initialize network backend infrastructure
        await self._initAhaRegistry()

        # phase 2 - service storage
        await self.initCellStorage()
        await self.initServiceStorage()

        # phase 3 - nexus subsystem
        await self.initNexusSubsystem()

        await self.configNexsVers()

        # We can now do nexus-safe operations
        await self._initInauguralConfig()

        # phase 4 - service logic
        await self.initServiceRuntime()
        # phase 5 - service networking
        await self.initServiceNetwork()

    async def _storCellHiveMigration(self):
        logger.warning(f'migrating Cell ({self.getCellType()}) info out of hive')

        async with await self.hive.open(('cellvers',)) as versnode:
            versdict = await versnode.dict()
            for key, valu in versdict.items():
                self.cellvers.set(key, valu)

        async with await self.hive.open(('cellinfo',)) as infonode:
            infodict = await infonode.dict()
            for key, valu in infodict.items():
                self.cellinfo.set(key, valu)

        logger.warning(f'...Cell ({self.getCellType()}) info migration complete!')

    async def _storCellAuthMigration(self):
        if self.conf.get('auth:ctor') is not None:
            return

        logger.warning(f'migrating Cell ({self.getCellType()}) auth out of hive')

        authkv = self.slab.getSafeKeyVal('auth')

        async with await self.hive.open(('auth',)) as rootnode:

            rolekv = authkv.getSubKeyVal('role:info:')
            rolenamekv = authkv.getSubKeyVal('role:name:')

            async with await rootnode.open(('roles',)) as roles:
                for iden, node in roles:
                    roledict = await node.dict()
                    roleinfo = roledict.pack()

                    roleinfo['iden'] = iden
                    roleinfo['name'] = node.valu
                    roleinfo['authgates'] = {}
                    roleinfo.setdefault('admin', False)
                    roleinfo.setdefault('rules', ())

                    rolekv.set(iden, roleinfo)
                    rolenamekv.set(node.valu, iden)

            userkv = authkv.getSubKeyVal('user:info:')
            usernamekv = authkv.getSubKeyVal('user:name:')

            async with await rootnode.open(('users',)) as users:
                for iden, node in users:
                    userdict = await node.dict()
                    userinfo = userdict.pack()

                    userinfo['iden'] = iden
                    userinfo['name'] = node.valu
                    userinfo['authgates'] = {}
                    userinfo.setdefault('admin', False)
                    userinfo.setdefault('rules', ())
                    userinfo.setdefault('locked', False)
                    userinfo.setdefault('passwd', None)
                    userinfo.setdefault('archived', False)

                    realroles = []
                    for userrole in userinfo.get('roles', ()):
                        if rolekv.get(userrole) is None:
                            mesg = f'Unknown role {userrole} on user {iden} during migration, ignoring.'
                            logger.warning(mesg)
                            continue

                        realroles.append(userrole)

                    userinfo['roles'] = tuple(realroles)

                    userkv.set(iden, userinfo)
                    usernamekv.set(node.valu, iden)

                    varskv = authkv.getSubKeyVal(f'user:{iden}:vars:')
                    async with await node.open(('vars',)) as varnodes:
                        for name, varnode in varnodes:
                            varskv.set(name, varnode.valu)

                    profkv = authkv.getSubKeyVal(f'user:{iden}:profile:')
                    async with await node.open(('profile',)) as profnodes:
                        for name, profnode in profnodes:
                            profkv.set(name, profnode.valu)

            gatekv = authkv.getSubKeyVal('gate:info:')
            async with await rootnode.open(('authgates',)) as authgates:
                for gateiden, node in authgates:
                    gateinfo = {
                        'iden': gateiden,
                        'type': node.valu
                    }
                    gatekv.set(gateiden, gateinfo)

                    async with await node.open(('users',)) as usernodes:
                        for useriden, usernode in usernodes:
                            if (user := userkv.get(useriden)) is None:
                                mesg = f'Unknown user {useriden} on gate {gateiden} during migration, ignoring.'
                                logger.warning(mesg)
                                continue

                            userinfo = await usernode.dict()
                            userdict = userinfo.pack()
                            authkv.set(f'gate:{gateiden}:user:{useriden}', userdict)

                            user['authgates'][gateiden] = userdict
                            userkv.set(useriden, user)

                    async with await node.open(('roles',)) as rolenodes:
                        for roleiden, rolenode in rolenodes:
                            if (role := rolekv.get(roleiden)) is None:
                                mesg = f'Unknown role {roleiden} on gate {gateiden} during migration, ignoring.'
                                logger.warning(mesg)
                                continue

                            roleinfo = await rolenode.dict()
                            roledict = roleinfo.pack()
                            authkv.set(f'gate:{gateiden}:role:{roleiden}', roledict)

                            role['authgates'][gateiden] = roledict
                            rolekv.set(roleiden, role)

        logger.warning(f'...Cell ({self.getCellType()}) auth migration complete!')

    def getPermDef(self, perm):
        perm = tuple(perm)
        if self.permlook is None:
            self.permlook = {pdef['perm']: pdef for pdef in self.getPermDefs()}
        return self.permlook.get(perm)

    def getPermDefs(self):
        if self.permdefs is None:
            self.permdefs = self._getPermDefs()
        return self.permdefs

    def _getPermDefs(self):
        return ()

    def _clearPermDefs(self):
        self.permdefs = None
        self.permlook = None

    def getDmonUser(self):
        '''
        Return the user IDEN of a telepath caller who invoked the current task.
        ( defaults to returning current root user )
        '''
        sess = s_scope.get('sess', None)
        if sess is None:
            return self.auth.rootuser.iden

        if sess.user is None: # pragma: no cover
            return self.auth.rootuser.iden

        return sess.user.iden

    async def fini(self):
        '''Fini override that ensures locking teardown order.'''
        # we inherit from Pusher to make the Cell a Base subclass
        retn = await s_nexus.Pusher.fini(self)
        if retn == 0:
            self._onFiniCellGuid()
        return retn

    def _onFiniCellGuid(self):
        fcntl.lockf(self._cellguidfd, fcntl.LOCK_UN)
        self._cellguidfd.close()

    def _getCellLock(self):
        cmd = fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.lockf(self._cellguidfd, cmd)
        except BlockingIOError:
            # Raised when the a lock is unable to be obtained on cell.guid file.
            ctyp = self.getCellType()
            mesg = f'Cannot start the {ctyp}, another process is already running it.'
            raise s_exc.FatalErr(mesg=mesg) from None

    async def _onBootOptimize(self):

        bdir = s_common.genpath(self.dirn, 'backups')
        tdir = s_common.gendir(self.dirn, 'tmp')
        tdev = os.stat(tdir).st_dev

        logger.warning('Collecting LMDB files for onboot optimization.')

        lmdbs = []
        for (root, dirs, files) in os.walk(self.dirn):
            for dirname in dirs:
                filepath = os.path.join(root, dirname, 'data.mdb')
                if os.path.isfile(filepath):
                    if filepath.startswith(bdir):
                        logger.debug(f'Skipping backup file {filepath}')
                        continue
                    if os.stat(filepath).st_dev != tdev:
                        logger.warning(f'Unable to run onboot:optimize, {filepath} is not on the same volume as {tdir}')
                        return

                    lmdbs.append(os.path.join(root, dirname))

        if not lmdbs: # pragma: no cover
            return

        logger.warning('Beginning onboot optimization (this could take a while)...')

        size = len(lmdbs)

        try:

            for i, lmdbpath in enumerate(lmdbs):

                logger.warning(f'... {i+1}/{size} {lmdbpath}')

                with self.getTempDir() as backpath:

                    async with await s_lmdbslab.LmdbBackup.anit(lmdbpath) as backup:
                        await backup.saveto(backpath)

                    srcpath = os.path.join(lmdbpath, 'data.mdb')
                    dstpath = os.path.join(backpath, 'data.mdb')

                    os.rename(dstpath, srcpath)

            logger.warning('... onboot optimization complete!')

        except Exception as e: # pragma: no cover
            logger.exception('...aborting onboot optimization and resuming boot (everything is fine).')

    def _delTmpFiles(self):

        tdir = s_common.gendir(self.dirn, 'tmp')

        names = os.listdir(tdir)
        if not names:
            return

        logger.warning(f'Removing {len(names)} temporary files/folders in: {tdir}')

        for name in names:

            path = os.path.join(tdir, name)

            if os.path.isfile(path):
                os.unlink(path)
                continue

            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                continue

    async def _execCellUpdates(self):
        # implement to apply updates to a fully initialized active cell
        # ( and do so using _bumpCellVers )
        pass

    async def setNexsVers(self, vers):
        if self.nexsvers < vers:
            await self._push('nexs:vers:set', vers)

    @s_nexus.Pusher.onPush('nexs:vers:set')
    async def _setNexsVers(self, vers):
        if vers > self.nexsvers:
            await self._migrNexsVers(vers)
            self.cellinfo.set('nexus:version', vers)
            self.nexsvers = vers
            await self.configNexsVers()

    async def _migrNexsVers(self, newvers):
        if self.nexsvers < (2, 198) and newvers >= (2, 198) and self.conf.get('auth:ctor') is None:
            # This "migration" will lock all archived users. Once the nexus version is bumped to
            # >=2.198, then the bottom-half nexus handler for user:info (Auth._setUserInfo()) will
            # begin rejecting unlock requests for archived users.

            authkv = self.slab.getSafeKeyVal('auth')
            userkv = authkv.getSubKeyVal('user:info:')

            for iden, info in userkv.items():
                if info.get('archived') and not info.get('locked'):
                    info['locked'] = True
                    userkv.set(iden, info)

            # Clear the auth caches so the changes get picked up by the already running auth subsystem
            self.auth.clearAuthCache()

    async def configNexsVers(self):
        for meth, orig in self.nexspatches:
            setattr(self, meth, orig)

        if self.nexsvers == NEXUS_VERSION:
            return

        patches = []
        if self.nexsvers < (2, 177):
            patches.extend([
                ('popUserVarValu', self._popUserVarValuV0),
                ('setUserVarValu', self._setUserVarValuV0),
                ('popUserProfInfo', self._popUserProfInfoV0),
                ('setUserProfInfo', self._setUserProfInfoV0),
            ])

        self.nexspatches = []
        for meth, repl in patches:
            self.nexspatches.append((meth, getattr(self, meth)))
            setattr(self, meth, repl)

    async def setCellVers(self, name, vers, nexs=True):
        if nexs:
            await self._push('cell:vers:set', name, vers)
        else:
            await self._setCellVers(name, vers)

    @s_nexus.Pusher.onPush('cell:vers:set')
    async def _setCellVers(self, name, vers):
        self.cellvers.set(name, vers)

    async def _bumpCellVers(self, name, updates, nexs=True):

        if self.inaugural:
            await self.setCellVers(name, updates[-1][0], nexs=nexs)
            return

        curv = self.cellvers.get(name, 0)

        for vers, callback in updates:

            if vers <= curv:
                continue

            await callback()

            await self.setCellVers(name, vers, nexs=nexs)

            curv = vers

    def checkFreeSpace(self):
        self._checkspace.set()

    async def _runFreeSpaceLoop(self):

        while not self.isfini:

            nexsroot = self.getCellNexsRoot()

            self._checkspace.clear()

            disk = shutil.disk_usage(self.dirn)

            if (disk.free / disk.total) <= self.minfree:

                await nexsroot.addWriteHold(diskspace)

                mesg = f'Free space on {self.dirn} below minimum threshold (currently ' \
                       f'{disk.free / disk.total * 100:.2f}%), setting Cell to read-only.'
                logger.error(mesg)

            elif nexsroot.readonly and await nexsroot.delWriteHold(diskspace):

                mesg = f'Free space on {self.dirn} above minimum threshold (currently ' \
                       f'{disk.free / disk.total * 100:.2f}%), removing free space write hold.'
                logger.error(mesg)

            await self._checkspace.timewait(timeout=self.FREE_SPACE_CHECK_FREQ)

    async def _runSysctlLoop(self):
        while not self.isfini:
            fixvals = []
            sysctls = s_thisplat.getSysctls()

            for name, valu in self.SYSCTL_VALS.items():
                if (sysval := sysctls.get(name)) != valu:
                    fixvals.append({'name': name, 'expected': valu, 'actual': sysval})

            if not fixvals:
                # All sysctl parameters have been set to recommended values, no
                # need to keep checking.
                break

            fixnames = [k['name'] for k in fixvals]
            mesg = f'Sysctl values different than expected: {", ".join(fixnames)}. '
            mesg += 'See https://synapse.docs.vertex.link/en/latest/synapse/devopsguide.html#performance-tuning '
            mesg += 'for information about these sysctl parameters.'

            extra = await self.getLogExtra(sysctls=fixvals)
            logger.warning(mesg, extra=extra)

            await self.waitfini(self.SYSCTL_CHECK_FREQ)

    async def _initAhaRegistry(self):

        ahaurls = self.conf.get('aha:registry')
        if ahaurls is not None:

            await s_telepath.addAhaUrl(ahaurls)
            if self.ahaclient is not None:
                await self.ahaclient.fini()

            async def onlink(proxy):
                ahauser = self.conf.get('aha:user', 'root')
                newurls = await proxy.getAhaUrls(user=ahauser)
                oldurls = self.conf.get('aha:registry')
                if isinstance(oldurls, str):
                    oldurls = (oldurls,)
                elif isinstance(oldurls, list):
                    oldurls = tuple(oldurls)
                if newurls and newurls != oldurls:
                    if oldurls[0].startswith('tcp://'):
                        s_common.deprecated('aha:registry: tcp:// client values.')
                        logger.warning('tcp:// based aha:registry options are deprecated and will be removed in Synapse v3.0.0')
                        return

                    self.modCellConf({'aha:registry': newurls})
                    self.ahaclient.setBootUrls(newurls)

            self.ahaclient = await s_telepath.Client.anit(ahaurls, onlink=onlink)
            self.onfini(self.ahaclient)

            async def fini():
                await s_telepath.delAhaUrl(ahaurls)

            self.ahaclient.onfini(fini)

        ahaadmin = self.conf.get('aha:admin')
        ahauser = self.conf.get('aha:user')

        if ahaadmin is not None:
            await self._addAdminUser(ahaadmin)

        if ahauser is not None:
            await self._addAdminUser(ahauser)

    def _getDmonListen(self):

        lisn = self.conf.get('dmon:listen', s_common.novalu)
        if lisn is not s_common.novalu:
            return lisn

        ahaname = self.conf.get('aha:name')
        ahanetw = self.conf.get('aha:network')
        if ahaname is not None and ahanetw is not None:
            hostname = f'{ahaname}.{ahanetw}'
            return f'ssl://0.0.0.0:0?hostname={hostname}&ca={ahanetw}'

    async def _addAdminUser(self, username):
        # add the user in a pre-nexus compatible way
        user = await self.auth.getUserByName(username)

        if user is None:
            iden = s_common.guid(username)
            await self.auth._addUser(iden, username)
            user = await self.auth.getUserByName(username)

        if not user.isAdmin():
            await user.setAdmin(True, logged=False)

        if user.isLocked():
            await user.setLocked(False, logged=False)

    async def initServiceEarly(self):
        pass

    async def initCellStorage(self):
        self.drive = await s_drive.Drive.anit(self.slab, 'celldrive')
        self.onfini(self.drive.fini)

    async def addDriveItem(self, info, path=None, reldir=s_drive.rootdir):

        iden = info.get('iden')
        if iden is None:
            info['iden'] = s_common.guid()

        info.setdefault('created', s_common.now())
        info.setdefault('creator', self.auth.rootuser.iden)

        return await self._push('drive:add', info, path=path, reldir=reldir)

    @s_nexus.Pusher.onPush('drive:add')
    async def _addDriveItem(self, info, path=None, reldir=s_drive.rootdir):

        # replay safety...
        iden = info.get('iden')
        if self.drive.hasItemInfo(iden): # pragma: no cover
            return await self.drive.getItemPath(iden)

        return await self.drive.addItemInfo(info, path=path, reldir=reldir)

    async def getDriveInfo(self, iden, typename=None):
        return self.drive.getItemInfo(iden, typename=typename)

    def reqDriveInfo(self, iden, typename=None):
        return self.drive.reqItemInfo(iden, typename=typename)

    async def getDrivePath(self, path, reldir=s_drive.rootdir):
        '''
        Return a list of drive info elements for each step in path.

        This may be used as a sort of "open" which returns all the
        path info entries. You may then operate directly on drive iden
        entries and/or check easyperm entries on them before you do...
        '''
        return await self.drive.getPathInfo(path, reldir=reldir)

    async def addDrivePath(self, path, perm=None, reldir=s_drive.rootdir):
        '''
        Create the given path using the specified permissions.

        The specified permissions are only used when creating new directories.

        NOTE: We must do this outside the Drive class to allow us to generate
              iden and tick but remain nexus compatible.
        '''
        tick = s_common.now()
        user = self.auth.rootuser.iden
        path = self.drive.getPathNorm(path)

        if perm is None:
            perm = {'users': {}, 'roles': {}}

        for name in path:

            info = self.drive.getStepInfo(reldir, name)
            await asyncio.sleep(0)

            if info is not None:
                reldir = info.get('iden')
                continue

            info = {
                'name': name,
                'perm': perm,
                'iden': s_common.guid(),
                'created': tick,
                'creator': user,
            }
            pathinfo = await self.addDriveItem(info, reldir=reldir)
            reldir = pathinfo[-1].get('iden')

        return await self.drive.getItemPath(reldir)

    async def getDriveData(self, iden, vers=None):
        '''
        Return the data associated with the drive item by iden.
        If vers is specified, return that specific version.
        '''
        return self.drive.getItemData(iden, vers=vers)

    async def getDriveDataVersions(self, iden):
        async for item in self.drive.getItemDataVersions(iden):
            yield item

    @s_nexus.Pusher.onPushAuto('drive:del')
    async def delDriveInfo(self, iden):
        if self.drive.getItemInfo(iden) is not None:
            await self.drive.delItemInfo(iden)

    @s_nexus.Pusher.onPushAuto('drive:set:perm')
    async def setDriveInfoPerm(self, iden, perm):
        return self.drive.setItemPerm(iden, perm)

    @s_nexus.Pusher.onPushAuto('drive:set:path')
    async def setDriveInfoPath(self, iden, path):

        path = self.drive.getPathNorm(path)
        pathinfo = await self.drive.getItemPath(iden)
        if path == [p.get('name') for p in pathinfo]:
            return pathinfo

        return await self.drive.setItemPath(iden, path)

    @s_nexus.Pusher.onPushAuto('drive:data:set')
    async def setDriveData(self, iden, versinfo, data):
        return await self.drive.setItemData(iden, versinfo, data)

    async def delDriveData(self, iden, vers=None):
        if vers is None:
            info = self.drive.reqItemInfo(iden)
            vers = info.get('version')
        return await self._push('drive:data:del', iden, vers)

    @s_nexus.Pusher.onPush('drive:data:del')
    async def _delDriveData(self, iden, vers):
        return self.drive.delItemData(iden, vers)

    async def getDriveKids(self, iden):
        async for info in self.drive.getItemKids(iden):
            yield info

    async def initServiceStorage(self):
        pass

    async def initNexusSubsystem(self):
        if self.cellparent is None:
            await self.nexsroot.recover()
            await self.nexsroot.startup()
            await self.setCellActive(self.conf.get('mirror') is None)

            if self.minfree is not None:
                self.schedCoro(self._runFreeSpaceLoop())

    async def _bindDmonListen(self):

        # functionalized so downstream code can bind early.
        if self.sockaddr is not None:
            return

        # start a unix local socket daemon listener
        sockpath = os.path.join(self.dirn, 'sock')
        sockurl = f'unix://{sockpath}'

        try:
            await self.dmon.listen(sockurl)
        except OSError as e:
            logger.error(f'Failed to listen on unix socket at: [{sockpath}][{e}]')
            logger.error('LOCAL UNIX SOCKET WILL BE UNAVAILABLE')
        except Exception:  # pragma: no cover
            logging.exception('Unknown dmon listen error.')

        turl = self._getDmonListen()
        if turl is not None:
            logger.info(f'dmon listening: {turl}')
            self.sockaddr = await self.dmon.listen(turl)

    async def initServiceNetwork(self):

        await self._bindDmonListen()

        await self._initAhaService()

        self.netready.set()

        port = self.conf.get('https:port')
        if port is not None:
            await self.addHttpsPort(port)
            logger.info(f'https listening: {port}')

    async def getAhaInfo(self):

        # Default to static information
        ahainfo = self.conf.get('aha:svcinfo')
        if ahainfo is not None:
            return ahainfo

        # If we have not setup our dmon listener yet, do not generate ahainfo
        if self.sockaddr is None:
            return None

        turl = self.conf.get('dmon:listen')

        # Dynamically generate the aha info based on config and runtime data.
        urlinfo = s_telepath.chopurl(turl)

        urlinfo.pop('host', None)
        if isinstance(self.sockaddr, tuple):
            urlinfo['port'] = self.sockaddr[1]

        celliden = self.getCellIden()
        runiden = await self.getCellRunId()
        ahalead = self.conf.get('aha:leader')

        # If we are active, then we are ready by definition.
        # If we are not active, then we have to check the nexsroot
        # and see if the nexsroot is marked as ready or not. This
        # status is set on mirrors when they have entered into the
        # real-time change window.
        if self.isactive:
            ready = True
        else:
            ready = await self.nexsroot.isNexsReady()

        ahainfo = {
            'run': runiden,
            'iden': celliden,
            'leader': ahalead,
            'urlinfo': urlinfo,
            'ready': ready,
        }

        return ahainfo

    async def _initAhaService(self):

        if self.ahaclient is None:
            return

        ahaname = self.conf.get('aha:name')
        if ahaname is None:
            return

        ahanetw = self.conf.get('aha:network')
        if ahanetw is None:
            return

        ahainfo = await self.getAhaInfo()
        if ahainfo is None:
            return

        ahalead = self.conf.get('aha:leader')

        self.ahasvcname = f'{ahaname}.{ahanetw}'

        async def _runAhaRegLoop():

            while not self.isfini:

                try:
                    proxy = await self.ahaclient.proxy()

                    info = await self.getAhaInfo()
                    await proxy.addAhaSvc(ahaname, info, network=ahanetw)
                    if self.isactive and ahalead is not None:
                        await proxy.addAhaSvc(ahalead, info, network=ahanetw)

                except Exception as e:
                    logger.exception(f'Error registering service {self.ahasvcname} with AHA: {e}')
                    await self.waitfini(1)

                else:
                    await proxy.waitfini()

        self.schedCoro(_runAhaRegLoop())

    async def initServiceRuntime(self):
        pass

    async def _ctorNexsRoot(self):
        '''
        Initialize a NexsRoot to use for the cell.
        '''
        if self.cellparent:
            return self.cellparent.nexsroot
        return await s_nexus.NexsRoot.anit(self)

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

        if not self.conf.get('nexslog:en'):
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

    def getMyUrl(self, user='root'):
        host = self.conf.req('aha:name')
        network = self.conf.req('aha:network')
        return f'aha://{host}.{network}'

    async def promote(self, graceful=False):
        '''
        Transform this cell from a passive follower to
        an active cell that writes changes locally.
        '''
        mirurl = self.conf.get('mirror')
        if mirurl is None:
            mesg = 'promote() called on non-mirror'
            raise s_exc.BadConfValu(mesg=mesg)

        _dispname = f' ahaname={self.conf.get("aha:name")}' if self.conf.get('aha:name') else ''
        logger.warning(f'PROMOTION: Performing leadership promotion graceful={graceful}{_dispname}.')

        if graceful:

            myurl = self.getMyUrl()

            logger.debug(f'PROMOTION: Connecting to {mirurl} to request leadership handoff{_dispname}.')
            async with await s_telepath.openurl(mirurl) as lead:
                await lead.handoff(myurl)
                logger.warning(f'PROMOTION: Completed leadership handoff to {myurl}{_dispname}')
                return

        logger.debug(f'PROMOTION: Clearing mirror configuration{_dispname}.')
        self.modCellConf({'mirror': None})

        logger.debug(f'PROMOTION: Promoting the nexus root{_dispname}.')
        await self.nexsroot.promote()

        logger.debug(f'PROMOTION: Setting the cell as active{_dispname}.')
        await self.setCellActive(True)

        logger.warning(f'PROMOTION: Finished leadership promotion{_dispname}.')

    async def handoff(self, turl, timeout=30):
        '''
        Hand off leadership to a mirror in a transactional fashion.
        '''
        _dispname = f' ahaname={self.conf.get("aha:name")}' if self.conf.get('aha:name') else ''

        if not self.isactive:
            mesg = f'HANDOFF: {_dispname} is not the current leader and cannot handoff leadership to' \
                   f' {s_urlhelp.sanitizeUrl(turl)}.'
            logger.error(mesg)
            raise s_exc.BadState(mesg=mesg, turl=turl, cursvc=_dispname)

        logger.warning(f'HANDOFF: Performing leadership handoff to {s_urlhelp.sanitizeUrl(turl)}{_dispname}.')
        async with await s_telepath.openurl(turl) as cell:

            logger.debug(f'HANDOFF: Connected to {s_urlhelp.sanitizeUrl(turl)}{_dispname}.')

            if self.iden != await cell.getCellIden(): # pragma: no cover
                mesg = 'Mirror handoff remote cell iden does not match!'
                raise s_exc.BadArg(mesg=mesg)

            if self.runid == await cell.getCellRunId(): # pragma: no cover
                mesg = 'Cannot handoff mirror leadership to myself!'
                raise s_exc.BadArg(mesg=mesg)

            logger.debug(f'HANDOFF: Obtaining nexus lock{_dispname}.')

            async with self.nexslock:

                logger.debug(f'HANDOFF: Obtained nexus lock{_dispname}.')
                indx = await self.getNexsIndx()

                logger.debug(f'HANDOFF: Waiting {timeout} seconds for mirror to reach {indx=}{_dispname}.')
                if not await cell.waitNexsOffs(indx - 1, timeout=timeout): # pragma: no cover
                    mndx = await cell.getNexsIndx()
                    mesg = f'Remote mirror did not catch up in time: {mndx}/{indx}.'
                    raise s_exc.NotReady(mesg=mesg)

                logger.debug(f'HANDOFF: Mirror has caught up to the current leader, performing promotion{_dispname}.')
                await cell.promote()

                logger.debug(f'HANDOFF: Setting the service as inactive{_dispname}.')
                await self.setCellActive(False)

                logger.debug(f'HANDOFF: Configuring service to sync from new leader{_dispname}.')
                self.modCellConf({'mirror': turl})

                logger.debug(f'HANDOFF: Restarting the nexus{_dispname}.')
                await self.nexsroot.startup()

            logger.debug(f'HANDOFF: Released nexus lock{_dispname}.')

        logger.warning(f'HANDOFF: Done performing the leadership handoff with {s_urlhelp.sanitizeUrl(turl)}{_dispname}.')

    async def reqAhaProxy(self, timeout=None):
        if self.ahaclient is None:
            mesg = 'AHA is not configured on this service.'
            raise s_exc.NeedConfValu(mesg=mesg)
        return await self.ahaclient.proxy(timeout=timeout)

    async def _setAhaActive(self):

        if self.ahaclient is None:
            return

        ahainfo = await self.getAhaInfo()
        if ahainfo is None:
            return

        ahalead = self.conf.get('aha:leader')
        if ahalead is None:
            return

        try:

            proxy = await self.ahaclient.proxy(timeout=2)

        except TimeoutError:  # pragma: no cover
            return None

        # if we went inactive, bump the aha proxy
        if not self.isactive:
            await proxy.fini()
            return

        ahanetw = self.conf.req('aha:network')
        try:
            await proxy.addAhaSvc(ahalead, ahainfo, network=ahanetw)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:  # pragma: no cover
            logger.warning(f'_setAhaActive failed: {e}')

    def isActiveCoro(self, iden):
        return self.activecoros.get(iden) is not None

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
            while not self.isfini and self.isActiveCoro(iden):
                try:
                    await func()
                except Exception:  # pragma no cover
                    logger.exception(f'activeCoro Error: {func}')
                    await self.waitfini(1)

        cdef['task'] = self.schedCoro(wrap())

    async def _killActiveCoros(self):
        coros = [self._killActiveCoro(cdef) for cdef in self.activecoros.values()]
        await asyncio.gather(*coros, return_exceptions=True)

    async def _killActiveCoro(self, cdef):
        task = cdef.pop('task', None)
        if task is not None:
            task.cancel()
            try:
                retn = await asyncio.gather(task, return_exceptions=True)
                if isinstance(retn[0], Exception):
                    raise retn[0]
            except asyncio.CancelledError:
                pass
            except Exception:  # pragma: no cover
                logger.exception(f'Error tearing down activecoro for {task}')

    async def isCellActive(self):
        return self.isactive

    async def setCellActive(self, active):

        if active == self.isactive:
            return

        self.isactive = active

        if self.isactive:
            self.activebase = await s_base.Base.anit()
            self.onfini(self.activebase)
            self._fireActiveCoros()
            await self._execCellUpdates()
            await self.setNexsVers(NEXUS_VERSION)
            await self.initServiceActive()
        else:
            await self._killActiveCoros()
            await self.activebase.fini()
            self.activebase = None
            await self.initServicePassive()

        await self._setAhaActive()

    def runActiveTask(self, coro):
        # an API for active coroutines to use when running an
        # ephemeral task which should be automatically torn down
        # if the cell becomes inactive
        return self.activebase.schedCoro(coro)

    async def initServiceActive(self):  # pragma: no cover
        pass

    async def initServicePassive(self):  # pragma: no cover
        pass

    async def getNexusChanges(self, offs, tellready=False, wait=True):
        async for item in self.nexsroot.iter(offs, tellready=tellready, wait=wait):
            yield item

    def _reqBackDirn(self, name):

        self._reqBackConf()

        path = s_common.genpath(self.backdirn, name)
        if not path.startswith(self.backdirn):
            mesg = 'Directory traversal detected'
            raise s_exc.BadArg(mesg=mesg)

        return path

    def _reqBackupSpace(self):

        disk = shutil.disk_usage(self.backdirn)
        cellsize, _ = s_common.getDirSize(self.dirn)

        if os.stat(self.dirn).st_dev == os.stat(self.backdirn).st_dev:
            reqspace = self.minfree * disk.total + cellsize
        else:
            reqspace = cellsize

        if reqspace > disk.free:
            mesg = f'Insufficient free space on {self.backdirn} to run a backup ' \
                    f'({disk.free} bytes free, {reqspace} required)'
            raise s_exc.LowSpace(mesg=mesg, dirn=self.backdirn)

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

            self._reqBackupSpace()

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

            async with self.nexslock:

                logger.debug('Syncing LMDB Slabs')

                while True:
                    await s_lmdbslab.Slab.syncLoopOnce()
                    if not any(slab.dirty for slab in slabs):
                        break

                logger.debug('Starting backup process')

                # Copy cell.guid first to ensure the backup can be deleted
                dstdir = s_common.gendir(dirn)
                shutil.copy(os.path.join(self.dirn, 'cell.guid'), os.path.join(dstdir, 'cell.guid'))

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
        try:

            with s_t_backup.capturelmdbs(srcdir) as lmdbinfo:
                pipe.send('captured')
                logger.debug('Acquired LMDB transactions')
                s_t_backup.txnbackup(lmdbinfo, srcdir, dstdir)
        except Exception:
            logger.exception(f'Error running backup of {srcdir}')
            raise

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

    async def _streamBackupArchive(self, path, user, name):
        link = s_scope.get('link')
        if link is None:
            mesg = 'Link not found in scope. This API must be called via a CellApi.'
            raise s_exc.SynErr(mesg=mesg)

        linkinfo = await link.getSpawnInfo()
        linkinfo['logconf'] = await self._getSpawnLogConf()

        await self.boss.promote('backup:stream', user=user, info={'name': name})

        ctx = multiprocessing.get_context('spawn')

        def getproc():
            proc = ctx.Process(target=_iterBackupProc, args=(path, linkinfo))
            proc.start()
            return proc

        mesg = 'Streaming complete'
        proc = await s_coro.executor(getproc)
        cancelled = False
        try:
            await s_coro.executor(proc.join)
            self.backlastuploaddt = datetime.datetime.now()
            logger.debug(f'Backup streaming completed successfully for {name}')

        except asyncio.CancelledError:
            logger.warning('Backup streaming was cancelled.')
            cancelled = True
            raise

        except Exception as e:
            logger.exception('Error during backup streaming.')
            mesg = repr(e)
            raise

        finally:
            proc.terminate()

            if not cancelled:
                raise s_exc.DmonSpawn(mesg=mesg)

    async def iterBackupArchive(self, name, user):
        path = self._reqBackDirn(name)
        cellguid = os.path.join(path, 'cell.guid')
        if not os.path.isfile(cellguid):
            mesg = 'Specified backup path has no cell.guid file.'
            raise s_exc.BadArg(mesg=mesg, arg='path', valu=path)
        await self._streamBackupArchive(path, user, name)

    async def _removeStreamingBackup(self, path):
        logger.debug(f'Removing {path}')
        await s_coro.executor(shutil.rmtree, path, ignore_errors=True)
        logger.debug(f'Removed {path}')
        self.backupstreaming = False

    async def iterNewBackupArchive(self, user, name=None, remove=False):

        if self.backupstreaming:
            raise s_exc.BackupAlreadyRunning(mesg='Another streaming backup is already running')

        try:
            if remove:
                self.backupstreaming = True

            if name is None:
                name = time.strftime('%Y%m%d%H%M%S', datetime.datetime.now().timetuple())

            path = self._reqBackDirn(name)
            if os.path.isdir(path):
                mesg = 'Backup with name already exists'
                raise s_exc.BadArg(mesg=mesg)

            await self.runBackup(name)
            await self._streamBackupArchive(path, user, name)

        finally:
            if remove:
                self.removetask = asyncio.create_task(self._removeStreamingBackup(path))
                await asyncio.shield(self.removetask)

    async def isUserAllowed(self, iden, perm, gateiden=None, default=False):
        user = self.auth.user(iden)  # type: s_auth.User
        if user is None:
            return False

        return user.allowed(perm, default=default, gateiden=gateiden)

    async def isRoleAllowed(self, iden, perm, gateiden=None):
        role = self.auth.role(iden)
        if role is None:
            return False

        return role.allowed(perm, gateiden=gateiden)

    async def tryUserPasswd(self, name, passwd):
        user = await self.auth.getUserByName(name)
        if user is None:
            return None

        if not await user.tryPasswd(passwd):
            return None

        return user.pack()

    async def getUserProfile(self, iden):
        user = await self.auth.reqUser(iden)
        return dict(user.profile.items())

    async def getUserProfInfo(self, iden, name, default=None):
        user = await self.auth.reqUser(iden)
        return user.profile.get(name, defv=default)

    async def _setUserProfInfoV0(self, iden, name, valu):
        path = ('auth', 'users', iden, 'profile', name)
        return await self.hive._push('hive:set', path, valu)

    async def setUserProfInfo(self, iden, name, valu):
        user = await self.auth.reqUser(iden)
        return await user.setProfileValu(name, valu)

    async def _popUserProfInfoV0(self, iden, name, default=None):
        path = ('auth', 'users', iden, 'profile', name)
        return await self.hive._push('hive:pop', path)

    async def popUserProfInfo(self, iden, name, default=None):
        user = await self.auth.reqUser(iden)
        return await user.popProfileValu(name, default=default)

    async def iterUserVars(self, iden):
        user = await self.auth.reqUser(iden)
        for item in user.vars.items():
            yield item
            await asyncio.sleep(0)

    async def iterUserProfInfo(self, iden):
        user = await self.auth.reqUser(iden)
        for item in user.profile.items():
            yield item
            await asyncio.sleep(0)

    async def getUserVarValu(self, iden, name, default=None):
        user = await self.auth.reqUser(iden)
        return user.vars.get(name, defv=default)

    async def _setUserVarValuV0(self, iden, name, valu):
        path = ('auth', 'users', iden, 'vars', name)
        return await self.hive._push('hive:set', path, valu)

    async def setUserVarValu(self, iden, name, valu):
        user = await self.auth.reqUser(iden)
        return await user.setVarValu(name, valu)

    async def _popUserVarValuV0(self, iden, name, default=None):
        path = ('auth', 'users', iden, 'vars', name)
        return await self.hive._push('hive:pop', path)

    async def popUserVarValu(self, iden, name, default=None):
        user = await self.auth.reqUser(iden)
        return await user.popVarValu(name, default=default)

    async def addUserRule(self, iden, rule, indx=None, gateiden=None):
        user = await self.auth.reqUser(iden)
        retn = await user.addRule(rule, indx=indx, gateiden=gateiden)
        logger.info(f'Added rule={rule} on user {user.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 rule=rule, gateiden=gateiden, status='MODIFY'))
        return retn

    async def addRoleRule(self, iden, rule, indx=None, gateiden=None):
        role = await self.auth.reqRole(iden)
        retn = await role.addRule(rule, indx=indx, gateiden=gateiden)
        logger.info(f'Added rule={rule} on role {role.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_role=role.iden, target_rolename=role.name,
                                                 rule=rule, gateiden=gateiden, status='MODIFY'))
        return retn

    async def delUserRule(self, iden, rule, gateiden=None):
        user = await self.auth.reqUser(iden)
        logger.info(f'Removing rule={rule} on user {user.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 rule=rule, gateiden=gateiden, status='MODIFY'))
        return await user.delRule(rule, gateiden=gateiden)

    async def delRoleRule(self, iden, rule, gateiden=None):
        role = await self.auth.reqRole(iden)
        logger.info(f'Removing rule={rule} on role {role.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_role=role.iden, target_rolename=role.name,
                                                 rule=rule, gateiden=gateiden, status='MODIFY'))
        return await role.delRule(rule, gateiden=gateiden)

    async def setUserRules(self, iden, rules, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setRules(rules, gateiden=gateiden)
        logger.info(f'Set user rules = {rules} on user {user.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 rules=rules, gateiden=gateiden, status='MODIFY'))

    async def setRoleRules(self, iden, rules, gateiden=None):
        role = await self.auth.reqRole(iden)
        await role.setRules(rules, gateiden=gateiden)
        logger.info(f'Set role rules = {rules} on role {role.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_role=role.iden, target_rolename=role.name,
                                                 rules=rules, gateiden=gateiden, status='MODIFY'))

    async def setRoleName(self, iden, name):
        role = await self.auth.reqRole(iden)
        oname = role.name
        await role.setName(name)
        logger.info(f'Set name={name} from {oname} on role iden={role.iden}',
                    extra=await self.getLogExtra(target_role=role.iden, target_rolename=role.name,
                                                 status='MODIFY'))

    async def setUserAdmin(self, iden, admin, gateiden=None):
        user = await self.auth.reqUser(iden)
        await user.setAdmin(admin, gateiden=gateiden)
        logger.info(f'Set admin={admin} for {user.name} for gateiden={gateiden}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 gateiden=gateiden, status='MODIFY'))

    async def addUserRole(self, useriden, roleiden, indx=None):
        user = await self.auth.reqUser(useriden)
        role = await self.auth.reqRole(roleiden)
        await user.grant(roleiden, indx=indx)
        logger.info(f'Granted role {role.name} to user {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 target_role=role.iden, target_rolename=role.name,
                                                 status='MODIFY'))

    async def setUserRoles(self, useriden, roleidens):
        user = await self.auth.reqUser(useriden)
        await user.setRoles(roleidens)
        logger.info(f'Set roleidens={roleidens} on user {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 roleidens=roleidens, status='MODIFY'))

    async def delUserRole(self, useriden, roleiden):
        user = await self.auth.reqUser(useriden)
        role = await self.auth.reqRole(roleiden)
        await user.revoke(roleiden)
        logger.info(f'Revoked role {role.name} from user {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 target_role=role.iden, target_rolename=role.name,
                                                 status='MODIFY'))

    async def addUser(self, name, passwd=None, email=None, iden=None):
        user = await self.auth.addUser(name, passwd=passwd, email=email, iden=iden)
        logger.info(f'Added user={name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name,
                                                 status='CREATE'))
        return user.pack(packroles=True)

    async def delUser(self, iden):
        user = await self.auth.reqUser(iden)
        name = user.name
        await self.auth.delUser(iden)
        logger.info(f'Deleted user={name}',
                   extra=await self.getLogExtra(target_user=iden, target_username=name, status='DELETE'))

    async def addRole(self, name, iden=None):
        role = await self.auth.addRole(name, iden=iden)
        logger.info(f'Added role={name}',
                    extra=await self.getLogExtra(target_role=role.iden, target_rolename=role.name, status='CREATE'))
        return role.pack()

    async def delRole(self, iden):
        role = await self.auth.reqRole(iden)
        name = role.name
        await self.auth.delRole(iden)
        logger.info(f'Deleted role={name}',
                     extra=await self.getLogExtra(target_role=iden, target_rolename=name, status='DELETE'))

    async def setUserEmail(self, useriden, email):
        await self.auth.setUserInfo(useriden, 'email', email)
        user = await self.auth.reqUser(useriden)
        logger.info(f'Set email={email} for {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

    async def setUserName(self, useriden, name):
        user = await self.auth.reqUser(useriden)
        oname = user.name
        await user.setName(name)
        logger.info(f'Set name={name} from {oname} on user iden={user.iden}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

    async def setUserPasswd(self, iden, passwd):
        user = await self.auth.reqUser(iden)
        await user.setPasswd(passwd)
        logger.info(f'Set password for {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

    async def genUserOnepass(self, iden, duration=600000):
        user = await self.auth.reqUser(iden)
        passwd = s_common.guid()
        shadow = await s_passwd.getShadowV2(passwd=passwd)
        now = s_common.now()
        onepass = {'create': now, 'expires': s_common.now() + duration,
                   'shadow': shadow}
        await self.auth.setUserInfo(iden, 'onepass', onepass)

        logger.info(f'Issued one time password for {user.name}',
                     extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

        return passwd

    async def setUserLocked(self, iden, locked):
        user = await self.auth.reqUser(iden)
        await user.setLocked(locked)
        logger.info(f'Set lock={locked} for user {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

    async def setUserArchived(self, iden, archived):
        user = await self.auth.reqUser(iden)
        await user.setArchived(archived)
        logger.info(f'Set archive={archived} for user {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, status='MODIFY'))

    async def getUserDef(self, iden, packroles=True):
        user = self.auth.user(iden)
        if user is not None:
            return user.pack(packroles=packroles)

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

    async def reqGateKeys(self, gatekeys):
        for useriden, perm, gateiden in gatekeys:
            (await self.auth.reqUser(useriden)).confirm(perm, gateiden=gateiden)

    async def feedBeholder(self, name, info, gates=None, perms=None):
        '''
        Feed a named event onto the ``cell:beholder`` message bus that will sent to any listeners.

        Args:
            info (dict): An information dictionary to be sent to any consumers.
            gates (list): List of gate idens, whose details will be added to the outbound message(s).
            perms (list): List of permission names, whose details will be added to the outbound message(s).

        Returns:
            None
        '''
        kwargs = {
            'event': name,
            'offset': await self.nexsroot.index(),
            'info': copy.deepcopy(info),
        }

        if gates:
            g = []
            for gate in gates:
                authgate = await self.getAuthGate(gate)
                if authgate is not None:
                    g.append(authgate)
            kwargs['gates'] = g

        if perms:
            p = []
            for perm in perms:
                permdef = self.getPermDef(perm)
                if permdef is not None:
                    p.append(permdef)
            kwargs['perms'] = p

        await self.fire('cell:beholder', **kwargs)

    @contextlib.asynccontextmanager
    async def beholder(self):
        async with await s_queue.Window.anit(maxsize=10000) as wind:
            async def onEvent(mesg):
                await wind.put(mesg[1])

            with self.onWith('cell:beholder', onEvent):
                yield wind

    async def behold(self):
        async with self.beholder() as wind:
            async for mesg in wind:
                yield mesg

    async def dyniter(self, iden, todo, gatekeys=()):

        await self.reqGateKeys(gatekeys)

        item = self.dynitems.get(iden)
        if item is None:
            raise s_exc.NoSuchIden(mesg=f'No dynitem for iden={iden}', iden=iden)

        name, args, kwargs = todo

        meth = getattr(item, name)
        async for item in meth(*args, **kwargs):
            yield item

    async def dyncall(self, iden, todo, gatekeys=()):

        await self.reqGateKeys(gatekeys)

        item = self.dynitems.get(iden)
        if item is None:
            raise s_exc.NoSuchIden(mesg=f'No dynitem for iden={iden}', iden=iden)

        name, args, kwargs = todo
        meth = getattr(item, name)

        return await s_coro.ornot(meth, *args, **kwargs)

    async def getConfOpt(self, name):
        return self.conf.get(name)

    def getUserName(self, iden, defv='<unknown>'):
        '''
        Translate the user iden to a user name.
        '''
        # since this pattern is so common, utilitizing...
        user = self.auth.user(iden)
        if user is None:
            return defv
        return user.name

    async def hasHttpSess(self, iden):
        return self.sessstor.has(iden)

    async def genHttpSess(self, iden):

        # TODO age out http sessions
        sess = self.sessions.get(iden)
        if sess is not None:
            return sess

        info = await self.getHttpSessDict(iden)
        if info is None:
            info = await self.addHttpSess(iden, {'created': s_common.now()})

        sess = await s_httpapi.Sess.anit(self, iden, info)

        self.sessions[iden] = sess
        return sess

    async def getHttpSessDict(self, iden):
        info = await self.sessstor.dict(iden)
        if info:
            return info

    @s_nexus.Pusher.onPushAuto('http:sess:add')
    async def addHttpSess(self, iden, info):
        for name, valu in info.items():
            self.sessstor.set(iden, name, valu)
        return info

    async def delHttpSess(self, iden):
        await self._push('http:sess:del', iden)

    @s_nexus.Pusher.onPush('http:sess:del')
    async def _delHttpSess(self, iden):
        await self.sessstor.del_(iden)
        sess = self.sessions.pop(iden, None)
        if sess:
            sess.info.clear()
            self.schedCoro(sess.fini())

    @s_nexus.Pusher.onPushAuto('http:sess:set')
    async def setHttpSessInfo(self, iden, name, valu):
        self.sessstor.set(iden, name, valu)
        sess = self.sessions.get(iden)
        if sess is not None:
            sess.info[name] = valu

    @s_nexus.Pusher.onPushAuto('http:sess:update')
    async def updateHttpSessInfo(self, iden, vals: dict):
        for name, valu in vals.items():
            s_msgpack.isok(valu)
        for name, valu in vals.items():
            self.sessstor.set(iden, name, valu)
        sess = self.sessions.get(iden)
        if sess is not None:
            sess.info.update(vals)

    @contextlib.contextmanager
    def getTempDir(self):
        tdir = s_common.gendir(self.dirn, 'tmp')
        with s_common.getTempDir(dirn=tdir) as dirn:
            yield dirn

    async def addHttpsPort(self, port, host='0.0.0.0', sslctx=None):
        '''
        Add a HTTPS listener to the Cell.

        Args:
            port (int): The listening port to bind.
            host (str): The listening host.
            sslctx (ssl.SSLContext): An externally managed SSL Context.

        Note:
            If the SSL context is not provided, the Cell will assume it
            manages the SSL context it creates for a given listener and will
            add a reload handler named https:certs to enabled reloading the
            SSL certificates from disk.
        '''

        addr = socket.gethostbyname(host)

        managed_ctx = False
        if sslctx is None:

            managed_ctx = True
            pkeypath = os.path.join(self.dirn, 'sslkey.pem')
            certpath = os.path.join(self.dirn, 'sslcert.pem')

            if not os.path.isfile(certpath):
                logger.warning('NO CERTIFICATE FOUND! generating self-signed certificate.')

                tdir = s_common.gendir(self.dirn, 'tmp')
                with s_common.getTempDir(dirn=tdir) as dirn:
                    cdir = s_certdir.CertDir(path=(dirn,))
                    pkey, cert = cdir.genHostCert(self.getCellType())
                    cdir.savePkeyPem(pkey, pkeypath)
                    cdir.saveCertPem(cert, certpath)

            sslctx = self.initSslCtx(certpath, pkeypath)

        kwargs = {
            'xheaders': self.conf.req('https:parse:proxy:remoteip')
        }
        serv = self.wapp.listen(port, address=addr, ssl_options=sslctx, **kwargs)
        self.httpds.append(serv)

        lhost, lport = list(serv._sockets.values())[0].getsockname()

        if managed_ctx:
            # If the Cell is managing the SSLCtx, then we register a reload handler
            # for it which reloads the pkey / cert.
            def reload():
                sslctx.load_cert_chain(certpath, pkeypath)
                return True

            self.addReloadableSystem('https:certs', reload)

        self.https_listeners.append({'host': lhost, 'port': lport})

        return (lhost, lport)

    def initSslCtx(self, certpath, keypath):

        sslctx = s_certdir.getServerSSLContext()

        if not os.path.isfile(keypath):
            raise s_exc.NoSuchFile(mesg=f'Missing TLS keypath {keypath}', path=keypath)

        if not os.path.isfile(certpath):
            raise s_exc.NoSuchFile(mesg=f'Missing TLS certpath {certpath}', path=certpath)

        sslctx.load_cert_chain(certpath, keypath)
        return sslctx

    def _log_web_request(self, handler: s_httpapi.Handler) -> None:
        # Derived from https://github.com/tornadoweb/tornado/blob/v6.2.0/tornado/web.py#L2253
        status = handler.get_status()
        if status < 400:
            log_method = t_log.access_log.info
        elif status < 500:
            log_method = t_log.access_log.warning
        else:
            log_method = t_log.access_log.error

        request_time = 1000.0 * handler.request.request_time()

        user = None
        username = None

        uri = handler.request.uri
        remote_ip = handler.request.remote_ip
        enfo = {'http_status': status,
                'uri': uri,
                'remoteip': remote_ip,
                }

        headers = {}

        for header in self.LOGGED_HTTPAPI_HEADERS:
            if (valu := handler.request.headers.get(header)) is not None:
                headers[header.lower()] = valu

        if headers:
            enfo['headers'] = headers

        extra = {'synapse': enfo}

        # It is possible that a Cell implementor may register handlers which
        # do not derive from our Handler class, so we have to handle that.
        if hasattr(handler, 'web_useriden') and handler.web_useriden:
            user = handler.web_useriden
            enfo['user'] = user
        if hasattr(handler, 'web_username') and handler.web_username:
            username = handler.web_username
            enfo['username'] = username

        if user:
            mesg = f'{status} {handler.request.method} {uri} ({remote_ip}) user={user} ({username}) {request_time:.2f}ms'
        else:
            mesg = f'{status} {handler.request.method} {uri} ({remote_ip}) {request_time:.2f}ms'

        log_method(mesg, extra=extra)

    async def _getCellHttpOpts(self):
        # Generate/Load a Cookie Secret
        secpath = os.path.join(self.dirn, 'cookie.secret')
        if not os.path.isfile(secpath):
            with s_common.genfile(secpath) as fd:
                fd.write(s_common.guid().encode('utf8'))

        with s_common.getfile(secpath) as fd:
            secret = fd.read().decode('utf8')

        return {
            'cookie_secret': secret,
            'log_function': self._log_web_request,
            'websocket_ping_interval': 10
        }

    async def _initCellHttp(self):

        self.httpds = []
        self.sessstor = s_lmdbslab.GuidStor(self.slab, 'http:sess')

        async def fini():
            [await s.fini() for s in self.sessions.values()]
            for http in self.httpds:
                http.stop()

        self.onfini(fini)

        opts = await self._getCellHttpOpts()

        self.wapp = t_web.Application(**opts)
        self._initCellHttpApis()

    def _initCellHttpApis(self):

        self.addHttpApi('/robots.txt', s_httpapi.RobotHandler, {'cell': self})
        self.addHttpApi('/api/v1/login', s_httpapi.LoginV1, {'cell': self})
        self.addHttpApi('/api/v1/logout', s_httpapi.LogoutV1, {'cell': self})

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

        self.addHttpApi('/api/v1/behold', s_httpapi.BeholdSockV1, {'cell': self})

    def addHttpApi(self, path, ctor, info):
        self.wapp.add_handlers('.*', (
            (path, ctor, info),
        ))

    def _initCertDir(self):

        self.certpath = s_common.gendir(self.dirn, 'certs')

        # add our cert path to the global resolver
        s_certdir.addCertPath(self.certpath)

        syncerts = s_data.path('certs')
        self.certdir = s_certdir.CertDir(path=(self.certpath, syncerts))

        def fini():
            s_certdir.delCertPath(self.certpath)

        self.onfini(fini)

    async def _initCellDmon(self):

        ahainfo = {'name': self.ahasvcname}

        self.dmon = await s_daemon.Daemon.anit(ahainfo=ahainfo)
        self.dmon.share('*', self)

        self.onfini(self.dmon.fini)

    async def _initCellHive(self):
        db = self.slab.initdb('hive')
        hive = await s_hive.SlabHive.anit(self.slab, db=db, nexsroot=self.getCellNexsRoot(), cell=self)
        self.onfini(hive)

        return hive

    async def _initSlabFile(self, path, readonly=False, ephemeral=False):
        slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE, readonly=readonly)
        slab.addResizeCallback(self.checkFreeSpace)
        fini = slab.fini
        if ephemeral:
            fini = slab
        self.onfini(fini)
        return slab

    async def _initCellSlab(self, readonly=False):

        s_common.gendir(self.dirn, 'slabs')

        path = os.path.join(self.dirn, 'slabs', 'cell.lmdb')
        if not os.path.exists(path) and readonly:
            logger.warning('Creating a slab for a readonly cell.')
            _slab = await s_lmdbslab.Slab.anit(path, map_size=SLAB_MAP_SIZE)
            _slab.initdb('hive')
            await _slab.fini()

        self.slab = await self._initSlabFile(path)

    async def _initCellAuth(self):

        # Add callbacks
        self.on('user:del', self._onUserDelEvnt)
        self.on('user:lock', self._onUserLockEvnt)

        authctor = self.conf.get('auth:ctor')
        if authctor is not None:
            s_common.deprecated('auth:ctor cell config option', curv='2.157.0')
            ctor = s_dyndeps.getDynLocal(authctor)
            return await ctor(self)

        maxusers = self.conf.get('max:users')
        policy = self.conf.get('auth:passwd:policy')

        seed = s_common.guid((self.iden, 'hive', 'auth'))

        auth = await s_auth.Auth.anit(
            self.slab,
            'auth',
            seed=seed,
            nexsroot=self.getCellNexsRoot(),
            maxusers=maxusers,
            policy=policy
        )

        auth.link(self.dist)

        def finilink():
            auth.unlink(self.dist)

        self.onfini(finilink)

        self.onfini(auth.fini)
        return auth

    def getCellNexsRoot(self):
        # the "cell scope" nexusroot only exists if we are *not* embedded
        # (aka we dont have a self.cellparent)
        if self.cellparent is None:
            return self.nexsroot

    async def _initInauguralConfig(self):
        if self.inaugural:
            icfg = self.conf.get('inaugural')
            if icfg is not None:

                for rnfo in icfg.get('roles', ()):
                    name = rnfo.get('name')
                    logger.debug(f'Adding inaugural role {name}')
                    iden = s_common.guid((self.iden, 'auth', 'role', name))
                    role = await self.auth.addRole(name, iden)  # type: s_auth.Role

                    for rule in rnfo.get('rules', ()):
                        await role.addRule(rule)

                for unfo in icfg.get('users', ()):
                    name = unfo.get('name')
                    email = unfo.get('email')
                    iden = s_common.guid((self.iden, 'auth', 'user', name))
                    logger.debug(f'Adding inaugural user {name}')
                    user = await self.auth.addUser(name, email=email, iden=iden)  # type: s_auth.User

                    if unfo.get('admin'):
                        await user.setAdmin(True)

                    for rolename in unfo.get('roles', ()):
                        role = await self.auth.reqRoleByName(rolename)
                        await user.grant(role.iden)

                    for rule in unfo.get('rules', ()):
                        await user.addRule(rule)

    @contextlib.asynccontextmanager
    async def getLocalProxy(self, share='*', user='root'):
        url = self.getLocalUrl(share=share, user=user)
        prox = await s_telepath.openurl(url)
        yield prox

    def getLocalUrl(self, share='*', user='root'):
        return f'cell://{user}@{self.dirn}:{share}'

    def _initCellConf(self, conf):
        '''
        Initialize a cell config during __anit__.

        Args:
            conf (s_config.Config, dict): A config object or dictionary.

        Notes:
            This does not pull environment variables or opts.
            This only pulls cell.yaml / cell.mods.yaml data in the event
            we got a dictionary

        Returns:
            s_config.Config: A config object.
        '''
        # if they hand in a dict, assume we are not the main/only one
        if isinstance(conf, dict):
            conf = s_config.Config.getConfFromCell(self, conf=conf)
            path = s_common.genpath(self.dirn, 'cell.yaml')
            conf.setConfFromFile(path)
            mods_path = s_common.genpath(self.dirn, 'cell.mods.yaml')
            conf.setConfFromFile(mods_path, force=True)

        conf.reqConfValid()  # Populate defaults
        return conf

    def _loadCellYaml(self, *path):

        path = os.path.join(self.dirn, *path)

        if os.path.isfile(path):
            logger.debug('Loading file from [%s]', path)
            return s_common.yamlload(path)

        return {}

    def _hasEasyPerm(self, item, user, level):

        if level > PERM_ADMIN or level < PERM_DENY:
            raise s_exc.BadArg(mesg=f'Invalid permission level: {level} (must be <= 3 and >= 0)')

        if user.isAdmin():
            return True

        userlevel = item['permissions']['users'].get(user.iden)
        if userlevel is not None:
            if userlevel == 0:
                return False
            elif userlevel >= level:
                return True

        roleperms = item['permissions']['roles']
        for role in user.getRoles():
            rolelevel = roleperms.get(role.iden)
            if rolelevel is not None:
                if rolelevel == 0:
                    return False
                elif rolelevel >= level:
                    return True

        default = item['permissions'].get('default', PERM_READ)
        if level <= default:
            return True

        return False

    def _reqEasyPerm(self, item, user, level, mesg=None):
        '''
        Require the user (or an assigned role) to have the given permission
        level on the specified item. The item must implement the "easy perm"
        convention by having a key named "permissions" which adheres to the
        easyPermSchema definition.

        NOTE: By default a user will only be denied read access if they
              (or an assigned role) has PERM_DENY assigned.
        '''
        if self._hasEasyPerm(item, user, level):
            return

        if mesg is None:
            permname = permnames.get(level)
            mesg = f'User ({user.name}) has insufficient permissions (requires: {permname}).'

        raise s_exc.AuthDeny(mesg=mesg, user=user.iden, username=user.name)

    async def _setEasyPerm(self, item, scope, iden, level):
        '''
        Set a user or role permission level within an object that uses the "easy perm"
        convention. If level is None, permissions are removed.
        '''
        if scope not in ('users', 'roles'):
            raise s_exc.BadArg(mesg=f'Invalid permissions scope: {scope} (must be "users" or "roles")')

        if level is not None and (level > PERM_ADMIN or level < PERM_DENY):
            raise s_exc.BadArg(mesg=f'Invalid permission level: {level} (must be <= 3 and >= 0, or None)')

        if scope == 'users':
            await self.auth.reqUser(iden)

        elif scope == 'roles':
            await self.auth.reqRole(iden)

        perms = item['permissions'].get(scope)
        if level is None:
            perms.pop(iden, None)
        else:
            perms[iden] = level

    def _initEasyPerm(self, item, default=PERM_READ):
        '''
        Ensure that the given object has populated the "easy perm" convention.
        '''
        if default > PERM_ADMIN or default < PERM_DENY:
            mesg = f'Invalid permission level: {default} (must be <= {PERM_ADMIN} and >= {PERM_DENY})'
            raise s_exc.BadArg(mesg=mesg)

        item.setdefault('permissions', {})
        item['permissions'].setdefault('users', {})
        item['permissions'].setdefault('roles', {})
        item['permissions'].setdefault('default', default)

    async def getTeleApi(self, link, mesg, path):

        # if auth is disabled or it's a unix socket, they're root.
        if link.get('unix'):
            name = 'root'
            auth = mesg[1].get('auth')
            if auth is not None:
                name, info = auth

            # By design, unix sockets can auth as any user.
            user = await self.auth.getUserByName(name)
            if user is None:
                raise s_exc.NoSuchUser(username=name, mesg=f'No such user: {name}.')

        else:
            user = await self._getCellUser(link, mesg)

        return await self.getCellApi(link, user, path)

    async def getCellApi(self, link, user, path):
        '''
        Get an instance of the telepath Client object for a given user, link and path.

        Args:
            link (s_link.Link): The link object.
            user (s_auth.User): The heavy user object.
            path (str): The path requested.

        Notes:
           This defaults to the self.cellapi class. Implementors may override the
           default class attribute for cellapi to share a different interface.

        Returns:
            object: The shared object for this cell.
        '''
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
        sess = s_scope.get('sess')  # type: s_daemon.Sess
        user = s_scope.get('user')  # type: s_auth.User
        if user:
            extra['user'] = user.iden
            extra['username'] = user.name
        elif sess and sess.user:
            extra['user'] = sess.user.iden
            extra['username'] = sess.user.name
        return {'synapse': extra}

    async def _getSpawnLogConf(self):
        conf = self.conf.get('_log_conf')
        if conf:
            conf = conf.copy()
        else:
            conf = s_common._getLogConfFromEnv()
        conf['log_setup'] = False
        return conf

    def modCellConf(self, conf):
        '''
        Modify the Cell's ondisk configuration overrides file and runtime configuration.

        Args:
            conf (dict): A dictionary of items to set.

        Notes:
            This does require the data being set to be schema valid.

        Returns:
            None.
        '''
        for key, valu in conf.items():
            self.conf.reqKeyValid(key, valu)
            logger.info(f'Setting cell config override for [{key}]')

        self.conf.update(conf)
        s_common.yamlmod(conf, self.dirn, 'cell.mods.yaml')

    def popCellConf(self, name):
        '''
        Remove a key from the Cell's ondisk configuration overrides file and
        runtime configuration.

        Args:
            name (str): Name of the value to remove.

        Notes:

            This does **not** modify the cell.yaml file.
            This does re-validate the configuration after removing the value,
            so if the value removed had a default populated by schema, that
            default would be reset.

        Returns:
            None
        '''
        self.conf.pop(name, None)
        self.conf.reqConfValid()
        s_common.yamlpop(name, self.dirn, 'cell.mods.yaml')
        logger.info(f'Removed cell config override for [{name}]')

    @classmethod
    def getCellType(cls):
        return cls.__name__.lower()

    @classmethod
    def getEnvPrefix(cls):
        '''Get a list of envar prefixes for config resolution.'''
        return (f'SYN_{cls.__name__.upper()}', )

    def getCellIden(self):
        return self.iden

    async def getCellRunId(self):
        return self.runid

    @classmethod
    def initCellConf(cls, conf=None):
        '''
        Create a Config object for the Cell.

        Args:
            conf (s_config.Config): An optional config structure. This has _opts_data taken from it.

        Notes:
            The Config object has a ``envar_prefix`` set according to the results of ``cls.getEnvPrefix()``.

        Returns:
            s_config.Config: A Config helper object.
        '''
        prefixes = cls.getEnvPrefix()
        schema = s_config.getJsSchema(cls.confbase, cls.confdefs)
        config = s_config.Config(schema, envar_prefixes=prefixes)
        if conf:
            config._opts_data = conf._opts_data
        return config

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
        prefix = cls.getEnvPrefix()[0]

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

    async def _initCellBoot(self):
        # NOTE: best hook point for custom provisioning

        isok, pnfo = await self._bootCellProv()

        # check this before we setup loadTeleCell()
        if not self._mustBootMirror():
            return

        if not isok:
            # The way that we get to this requires the following states to be true:
            # 1. self.dirn/cell.guid file is NOT present in the service directory.
            # 2. mirror config is present.
            # 3. aha:provision config is not set OR the aha:provision guid matches the self.dirn/prov.done file.
            mesg = 'Service has been configured to boot from an upstream mirror, but has entered into an invalid ' \
                   'state. This may have been caused by manipulation of the service storage or an error during a ' \
                   f'backup / restore operation. {pnfo.get("mesg")}'
            raise s_exc.FatalErr(mesg=mesg)

        async with s_telepath.loadTeleCell(self.dirn):
            await self._bootCellMirror(pnfo)

    @classmethod
    async def _initBootRestore(cls, dirn):

        env = 'SYN_RESTORE_HTTPS_URL'
        rurl = os.getenv(env, None)

        if rurl is None:
            return

        dirn = s_common.gendir(dirn)

        # restore.done - Allow an existing URL to be left in the configuration
        # for a service without issues.
        doneiden = None

        donepath = s_common.genpath(dirn, 'restore.done')
        if os.path.isfile(donepath):
            with s_common.genfile(donepath) as fd:
                doneiden = fd.read().decode().strip()

        rurliden = s_common.guid(rurl)

        if doneiden == rurliden:
            logger.warning(f'restore.done matched value from {env}. It is recommended to remove the {env} value.')
            return

        clean_url = s_urlhelp.sanitizeUrl(rurl).rsplit('?', 1)[0]
        logger.warning(f'Restoring {cls.getCellType()} from {env}={clean_url}')

        # First we clear any files out of the directory though. This avoids the possibility
        # of a restore that is potentially mixed.
        efiles = os.listdir(dirn)
        for fn in efiles:
            fp = os.path.join(dirn, fn)

            if os.path.isfile(fp):
                logger.warning(f'Removing existing file: {fp}')
                os.unlink(fp)
                continue

            if os.path.isdir(fp):
                logger.warning(f'Removing existing directory: {fp}')
                shutil.rmtree(fp)
                continue

            logger.warning(f'Unhandled existing file: {fp}')  # pragma: no cover

        # Setup get args
        insecure_marker = 'https+insecure://'
        kwargs = {}
        if rurl.startswith(insecure_marker):
            logger.warning(f'Disabling SSL verification for restore request.')
            kwargs['ssl'] = False
            rurl = 'https://' + rurl[len(insecure_marker):]

        tmppath = s_common.gendir(dirn, 'tmp')
        tarpath = s_common.genpath(tmppath, f'restore_{rurliden}.tgz')

        try:

            with s_common.genfile(tarpath) as fd:
                # Leave a 60 second timeout check for the connection and reads.
                # Disable total timeout
                timeout = aiohttp.client.ClientTimeout(
                    total=None,
                    connect=60,
                    sock_read=60,
                    sock_connect=60,
                )
                async with aiohttp.client.ClientSession(timeout=timeout) as sess:
                    async with sess.get(rurl, **kwargs) as resp:
                        resp.raise_for_status()

                        content_length = int(resp.headers.get('content-length', 0))
                        if content_length > 100:
                            logger.warning(f'Downloading {content_length/s_const.megabyte:.3f} MB of data.')
                            pvals = [int((content_length * 0.01) * i) for i in range(1, 100)]
                        else:  # pragma: no cover
                            logger.warning(f'Odd content-length encountered: {content_length}')
                            pvals = []

                        csize = s_const.kibibyte * 64  # default read chunksize for ClientSession
                        tsize = 0

                        async for chunk in resp.content.iter_chunked(csize):
                            fd.write(chunk)

                            tsize = tsize + len(chunk)
                            if pvals and tsize > pvals[0]:
                                pvals.pop(0)
                                percentage = (tsize / content_length) * 100
                                logger.warning(f'Downloaded {tsize/s_const.megabyte:.3f} MB, {percentage:.3f}%')

            logger.warning(f'Extracting {tarpath} to {dirn}')

            with tarfile.open(tarpath) as tgz:
                for memb in tgz.getmembers():
                    if memb.name.find('/') == -1:
                        continue
                    memb.name = memb.name.split('/', 1)[1]
                    logger.warning(f'Extracting {memb.name}')
                    tgz.extract(memb, dirn)

            # and record the rurliden
            with s_common.genfile(donepath) as fd:
                fd.truncate(0)
                fd.seek(0)
                fd.write(rurliden.encode())

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception:  # pragma: no cover
            logger.exception('Failed to restore cell from URL.')
            raise

        else:
            logger.warning('Restored service from URL')
            return

        finally:
            if os.path.isfile(tarpath):
                os.unlink(tarpath)

    async def _bootCellProv(self):

        provurl = self.conf.get('aha:provision')
        if provurl is None:
            return False, {'mesg': 'No aha:provision configuration has been provided to allow the service to '
                                   'bootstrap via AHA.'}

        doneiden = None

        donepath = s_common.genpath(self.dirn, 'prov.done')
        if os.path.isfile(donepath):
            with s_common.genfile(donepath) as fd:
                doneiden = fd.read().decode().strip()

        urlinfo = s_telepath.chopurl(provurl)
        providen = urlinfo.get('path').strip('/')

        if doneiden == providen:
            return False, {'mesg': f'The aha:provision URL guid matches the service prov.done guid, '
                                   f'aha:provision={provurl}'}

        logger.info(f'Provisioning {self.getCellType()} from AHA service.')

        certdir = s_certdir.CertDir(path=(s_common.gendir(self.dirn, 'certs'),))

        async with await s_telepath.openurl(provurl) as prov:

            provinfo = await prov.getProvInfo()
            provconf = provinfo.get('conf', {})

            ahauser = provconf.get('aha:user')
            ahaname = provconf.get('aha:name')
            ahanetw = provconf.get('aha:network')

            _crt = certdir.getCaCertPath(ahanetw)
            if _crt:
                logger.debug(f'Removing existing CA crt: {_crt}')
                os.unlink(_crt)
            certdir.saveCaCertByts(await prov.getCaCert())

            await self._bootProvConf(provconf)

            hostname = f'{ahaname}.{ahanetw}'
            _crt = certdir.getHostCertPath(hostname)
            if _crt:
                logger.debug(f'Removing existing host crt {_crt}')
                os.unlink(_crt)
            _kp = certdir.getHostKeyPath(hostname)
            if _kp:
                logger.debug(f'Removing existing host key {_kp}')
                os.unlink(_kp)
            _csr = certdir.getHostCsrPath(hostname)
            if _csr:
                logger.debug(f'Removing existing host csr {_csr}')
                os.unlink(_csr)
            hostcsr = certdir.genHostCsr(hostname)
            certdir.saveHostCertByts(await prov.signHostCsr(hostcsr))

            userfull = f'{ahauser}@{ahanetw}'
            _crt = certdir.getUserCertPath(userfull)
            if _crt:
                logger.debug(f'Removing existing user crt {_crt}')
                os.unlink(_crt)
            _kp = certdir.getUserKeyPath(userfull)
            if _kp:
                logger.debug(f'Removing existing user key {_kp}')
                os.unlink(_kp)
            _csr = certdir.getUserCsrPath(userfull)
            if _csr:
                logger.debug(f'Removing existing user csr {_csr}')
                os.unlink(_csr)
            usercsr = certdir.genUserCsr(userfull)
            certdir.saveUserCertByts(await prov.signUserCsr(usercsr))

        with s_common.genfile(self.dirn, 'prov.done') as fd:
            fd.write(providen.encode())

        logger.info(f'Done provisioning {self.getCellType()} AHA service.')

        return True, {'conf': provconf, 'iden': providen}

    async def _bootProvConf(self, provconf):
        '''
        Get a configuration object for booting the cell from a AHA configuration.

        Args:
            provconf (dict): A dictionary containing provisioning config data from AHA.

        Notes:
            The cell.yaml will have the "mirror" key removed from it.
            The cell.yaml will be modified with data from provconf.
            The cell.mods.yaml will have the "mirror" key removed from it.
            The cell.mods.yaml will have any keys in the prov conf removed from it.
            This sets the runtime configuration as well.

        Returns:
            s_config.Config: The new config object to be used.
        '''
        # replace our runtime config with the updated config with provconf data
        new_conf = self.initCellConf(self.conf)
        new_conf.setdefault('_log_conf', await self._getSpawnLogConf())

        # Load any opts we have and environment variables.
        new_conf.setConfFromOpts()

        new_conf.setConfFromEnvs()

        # Validate provconf, and insert it into cell.yaml
        for name, valu in provconf.items():
            new_conf.reqKeyValid(name, valu)

        cell_path = s_common.genpath(self.dirn, 'cell.yaml')

        # Slice the mirror option out of the cell.yaml file. This avoids
        # a situation where restoring a backup from a cell which was provisioned
        # as a mirror is then provisioned as a leader and then has an extra
        # cell config value which conflicts with the new provconf.
        s_common.yamlpop('mirror', cell_path)

        # Inject the provconf value into the cell configuration
        s_common.yamlmod(provconf, cell_path)

        # load cell.yaml, still preferring actual config data from opts/envs.
        new_conf.setConfFromFile(cell_path)

        # Remove any keys from overrides that were set from provconf
        # then load the file
        mods_path = s_common.genpath(self.dirn, 'cell.mods.yaml')
        for key in provconf:
            s_common.yamlpop(key, mods_path)

        # Slice the mirror option out of the cell.mods.yaml file. This avoids
        # a situation where restoring a backup from a cell which was demoted
        # from a leader to a follower has a config value which conflicts with
        # the new provconf.
        s_common.yamlpop('mirror', mods_path)

        new_conf.setConfFromFile(mods_path, force=True)

        # Ensure defaults are set
        new_conf.reqConfValid()
        self.conf = new_conf
        return new_conf

    def _mustBootMirror(self):
        path = s_common.genpath(self.dirn, 'cell.guid')
        if os.path.isfile(path):
            return False

        murl = self.conf.get('mirror')
        if murl is None:
            return False

        return True

    async def readyToMirror(self):
        if not self.conf.get('nexslog:en'):
            self.modCellConf({'nexslog:en': True})
            await self.nexsroot.enNexsLog()
            await self.sync()

    async def _initCloneCell(self, proxy):

        tarpath = s_common.genpath(self.dirn, 'tmp', 'bootstrap.tgz')
        try:

                await proxy.readyToMirror()
                with s_common.genfile(tarpath) as fd:
                    async for byts in proxy.iterNewBackupArchive(remove=True):
                        fd.write(byts)

                with tarfile.open(tarpath) as tgz:
                    for memb in tgz.getmembers():
                        if memb.name.find('/') == -1:
                            continue
                        memb.name = memb.name.split('/', 1)[1]
                        tgz.extract(memb, self.dirn)

        finally:

            if os.path.isfile(tarpath):
                os.unlink(tarpath)

    async def _bootCellMirror(self, pnfo):
        # this function must assume almost nothing is initialized
        # but that's ok since it will only run rarely.
        # It assumes it has a tuple of (provisioning configuration, provisioning iden) available
        murl = self.conf.req('mirror')
        provconf, providen = pnfo.get('conf'), pnfo.get('iden')

        logger.warning(f'Bootstrap mirror from: {murl} (this could take a while!)')

        async with await s_telepath.openurl(murl) as proxy:
            await self._initCloneCell(proxy)

        # Remove aha:provision from cell.yaml if it exists and the iden differs.
        mnfo = s_common.yamlload(self.dirn, 'cell.yaml')
        if mnfo:
            provurl = mnfo.get('aha:provision', None)
            if provurl:
                murlinfo = s_telepath.chopurl(provurl)
                miden = murlinfo.get('path').strip('/')
                if miden != providen:
                    s_common.yamlpop('aha:provision', self.dirn, 'cell.yaml')
                    logger.debug('Removed aha:provision from cell.yaml')

        await self._bootProvConf(provconf)

        # Overwrite the prov.done file that may have come from
        # the upstream backup.
        with s_common.genfile(self.dirn, 'prov.done') as fd:
            fd.truncate(0)
            fd.write(providen.encode())

        logger.warning(f'Bootstrap mirror from: {murl} DONE!')

    async def getMirrorUrls(self):
        if self.ahaclient is None:
            raise s_exc.BadConfValu(mesg='Enumerating mirror URLs is only supported when AHA is configured')

        await self.ahaclient.waitready()

        proxy = await self.ahaclient.proxy(timeout=5)
        mirrors = await proxy.getAhaSvcMirrors(self.ahasvcname)
        if mirrors is None:
            mesg = 'Service must be configured with AHA to enumerate mirror URLs'
            raise s_exc.NoSuchName(mesg=mesg, name=self.ahasvcname)

        return [f'aha://{svc["svcname"]}.{svc["svcnetw"]}' for svc in mirrors]

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
        path = s_common.genpath(opts.dirn, 'cell.yaml')
        mods_path = s_common.genpath(opts.dirn, 'cell.mods.yaml')

        logconf = s_common.setlogging(logger, defval=opts.log_level,
                                      structlog=opts.structured_logging)

        logger.info(f'Starting {cls.getCellType()} version {cls.VERSTRING}, Synapse version: {s_version.verstring}',
                    extra={'synapse': {'svc_type': cls.getCellType(), 'svc_version': cls.VERSTRING,
                                       'synapse_version': s_version.verstring}})

        await cls._initBootRestore(opts.dirn)

        try:
            conf.setdefault('_log_conf', logconf)
            conf.setConfFromOpts(opts)
            conf.setConfFromEnvs()
            conf.setConfFromFile(path)
            conf.setConfFromFile(mods_path, force=True)
        except:
            logger.exception(f'Error while bootstrapping cell config.')
            raise

        s_coro.set_pool_logging(logger, logconf=conf['_log_conf'])

        try:
            cell = await cls.anit(opts.dirn, conf=conf)
        except:
            logger.exception(f'Error starting cell at {opts.dirn}')
            raise

        try:

            turl = cell._getDmonListen()
            if turl is None:
                turl = opts.telepath
                await cell.dmon.listen(turl)

            logger.info(f'...{cell.getCellType()} API (telepath): {turl}')

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

            if username.find('@') != -1:
                userpart, hostpart = username.split('@', 1)
                if hostpart == self.conf.get('aha:network'):
                    user = await self.auth.getUserByName(userpart)
                    if user is not None:
                        if user.isLocked():
                            raise s_exc.AuthDeny(mesg=f'User ({userpart}) is locked.', user=user.iden, username=userpart)
                        return user

            user = await self.auth.getUserByName(username)
            if user is not None:
                if user.isLocked():
                    raise s_exc.AuthDeny(mesg=f'User ({username}) is locked.', user=user.iden, username=username)
                return user

            raise s_exc.NoSuchUser(mesg=f'TLS client cert User not found: {username}', username=username)

        auth = mesg[1].get('auth')
        if auth is None:

            anonuser = self.conf.get('auth:anon')
            if anonuser is None:
                raise s_exc.AuthDeny(mesg=f'Unable to find cell user ({anonuser})')

            user = await self.auth.getUserByName(anonuser)
            if user is None:
                raise s_exc.AuthDeny(mesg=f'Anon user ({anonuser}) is not found.', username=anonuser)

            if user.isLocked():
                raise s_exc.AuthDeny(mesg=f'Anon user ({anonuser}) is locked.', username=anonuser,
                                     user=user.iden)

            return user

        name, info = auth

        user = await self.auth.getUserByName(name)
        if user is None:
            raise s_exc.NoSuchUser(username=name, mesg=f'No such user: {name}.')

        # passwd None always fails...
        passwd = info.get('passwd')

        if not await user.tryPasswd(passwd):
            raise s_exc.AuthDeny(mesg='Invalid password', username=user.name, user=user.iden)

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

    async def iterSlabData(self, name, prefix=''):
        slabkv = self.slab.getSafeKeyVal(name, prefix=prefix, create=False)
        for key, valu in slabkv.items():
            yield key, valu
            await asyncio.sleep(0)

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

    async def getAhaProxy(self, timeout=None, feats=None):

        if self.ahaclient is None:
            return

        proxy = await self.ahaclient.proxy(timeout=timeout)
        if proxy is None:
            logger.warning('AHA client connection failed.')
            return

        if feats is not None:
            for name, vers in feats:
                if not proxy._hasTeleFeat(name, vers):
                    logger.warning(f'AHA server does not support feature: {name} >= {vers}')
                    return None

        return proxy

    async def callPeerApi(self, todo, timeout=None):
        '''
        Yield responses from our peers via the AHA gather call API.
        '''
        proxy = await self.getAhaProxy(timeout=timeout, feats=(feat_aha_callpeers_v1,))
        if proxy is None:
            return

        async for item in proxy.callAhaPeerApi(self.iden, todo, timeout=timeout, skiprun=self.runid):
            yield item

    async def callPeerGenr(self, todo, timeout=None):
        '''
        Yield responses from invoking a generator via the AHA gather API.
        '''
        proxy = await self.getAhaProxy(timeout=timeout, feats=(feat_aha_callpeers_v1,))
        if proxy is None:
            return

        async for item in proxy.callAhaPeerGenr(self.iden, todo, timeout=timeout, skiprun=self.runid):
            yield item

    async def getTasks(self, peers=True, timeout=None):

        for task in self.boss.ps():

            item = task.packv2()
            item['service'] = self.ahasvcname

            yield item

        if not peers:
            return

        todo = s_common.todo('getTasks', peers=False)
        # we can ignore the yielded aha names because we embed it in the task
        async for (ahasvc, (ok, retn)) in self.callPeerGenr(todo, timeout=timeout):

            if not ok: # pragma: no cover
                logger.warning(f'getTasks() on {ahasvc} failed: {retn}')
                continue

            yield retn

    async def getTask(self, iden, peers=True, timeout=None):

        task = self.boss.get(iden)
        if task is not None:
            item = task.packv2()
            item['service'] = self.ahasvcname
            return item

        if not peers:
            return

        todo = s_common.todo('getTask', iden, peers=False, timeout=timeout)
        async for ahasvc, (ok, retn) in self.callPeerApi(todo, timeout=timeout):

            if not ok: # pragma: no cover
                logger.warning(f'getTask() on {ahasvc} failed: {retn}')
                continue

            if retn is not None:
                return retn

    async def killTask(self, iden, peers=True, timeout=None):

        task = self.boss.get(iden)
        if task is not None:
            await task.kill()
            return True

        if not peers:
            return False

        todo = s_common.todo('killTask', iden, peers=False, timeout=timeout)
        async for ahasvc, (ok, retn) in self.callPeerApi(todo, timeout=timeout):

            if not ok: # pragma: no cover
                logger.warning(f'killTask() on {ahasvc} failed: {retn}')
                continue

            if retn:
                return True

        return False

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
        raise s_exc.AuthDeny(mesg=f'User ({user.name}) must have permission {perm} or own the task',
                             task=iden, user=user.iden, username=user.name, perm=perm)

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

        mirror = self.conf.get('mirror')
        if mirror is not None:
            mirror = s_urlhelp.sanitizeUrl(mirror)

        ret = {
            'synapse': {
                'commit': s_version.commit,
                'version': s_version.version,
                'verstring': s_version.verstring,
            },
            'cell': {
                'run': await self.getCellRunId(),
                'type': self.getCellType(),
                'iden': self.getCellIden(),
                'paused': self.paused,
                'active': self.isactive,
                'started': self.startms,
                'ready': self.nexsroot.ready.is_set(),
                'commit': self.COMMIT,
                'version': self.VERSION,
                'verstring': self.VERSTRING,
                'cellvers': dict(self.cellvers.items()),
                'nexsindx': await self.getNexsIndx(),
                'uplink': self.nexsroot.miruplink.is_set(),
                'mirror': mirror,
                'aha': {
                    'name': self.conf.get('aha:name'),
                    'leader': self.conf.get('aha:leader'),
                    'network': self.conf.get('aha:network'),
                },
                'network': {
                    'https': self.https_listeners,
                }
            },
            'features': self.features,
        }
        return ret

    async def getTeleFeats(self):
        return dict(self.features)

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
                - tmpdir - The temporary directory interpreted by the Python runtime.
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
        sysctls = s_thisplat.getSysctls()
        tmpdir = s_thisplat.getTempDir()

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
            'sysctls': sysctls,                # Performance related sysctls
            'tmpdir': tmpdir,                  # Temporary File / Folder Directory
        }

        return retn

    @contextlib.asynccontextmanager
    async def getSpooledSet(self):
        async with await s_spooled.Set.anit(dirn=self.dirn, cell=self) as sset:
            yield sset

    @contextlib.asynccontextmanager
    async def getSpooledDict(self):
        async with await s_spooled.Dict.anit(dirn=self.dirn, cell=self) as sdict:
            yield sdict

    async def addSignalHandlers(self):
        await s_base.Base.addSignalHandlers(self)

        def sighup():
            logger.info('Caught SIGHUP, running reloadable subsystems.')
            task = asyncio.create_task(self.reload())
            self._syn_signal_tasks.add(task)
            task.add_done_callback(self._syn_signal_tasks.discard)

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGHUP, sighup)

    def addReloadableSystem(self, name: str, func: callable):
        '''
        Add a reloadable system. This may be dynamically called at at time.

        Args:
            name (str): Name of the system.
            func: The callable for reloading a given system.

        Note:
            Reload functions take no arguments when they are executed.
            Values returned by the reload function must be msgpack friendly.

        Returns:
            None
        '''
        self._reloadfuncs[name] = func

    def getReloadableSystems(self):
        return tuple(self._reloadfuncs.keys())

    async def reload(self, subsystem=None):
        ret = {}
        if subsystem:
            func = self._reloadfuncs.get(subsystem)
            if func is None:
                raise s_exc.NoSuchName(mesg=f'No reload system named {subsystem}',
                                       name=subsystem)
            ret[subsystem] = await self._runReloadFunc(subsystem, func)
        else:
            # Run all funcs
            for (rname, func) in self._reloadfuncs.items():
                ret[rname] = await self._runReloadFunc(rname, func)
        return ret

    async def _runReloadFunc(self, name, func):
        try:
            logger.debug(f'Running cell reload system {name}')
            ret = await s_coro.ornot(func)
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f'Error running reload system {name}')
            return s_common.retnexc(e)
        logger.debug(f'Completed cell reload system {name}')
        return (True, ret)

    async def addUserApiKey(self, useriden, name, duration=None):
        '''
        Add an API key for a user.

        Notes:
            The secret API key is only available once.

        Args:
            useriden (str): User iden value.
            name (str): Name of the API key.
            duration (int or None): Duration of time for the API key to be valid ( in milliseconds ).

        Returns:
            tuple: A tuple of the secret API key value and the API key metadata information.
        '''
        user = await self.auth.reqUser(useriden)
        iden, token, shadow = await s_passwd.generateApiKey()
        now = s_common.now()
        kdef = {
            'iden': iden,
            'name': name,
            'user': user.iden,
            'created': now,
            'updated': now,
            'shadow': shadow,
        }

        if duration is not None:
            if duration < 1:
                raise s_exc.BadArg(mesg='Duration must be equal or greater than 1', name='duration')
            kdef['expires'] = now + duration

        kdef = s_schemas.reqValidUserApiKeyDef(kdef)

        await self._push('user:apikey:add', kdef)

        logger.info(f'Created HTTP API key {iden} for {user.name}, {name=}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, iden=iden,
                                                 status='MODIFY'))

        kdef.pop('shadow')
        return token, kdef

    @s_nexus.Pusher.onPush('user:apikey:add')
    async def _genUserApiKey(self, kdef):
        iden = s_common.uhex(kdef.get('iden'))
        user = s_common.uhex(kdef.get('user'))
        self.slab.put(iden, user, db=self.apikeydb)
        lkey = user + b'apikey' + iden
        self.slab.put(lkey, s_msgpack.en(kdef), db=self.usermetadb)

    async def getUserApiKey(self, iden):
        '''
        Get a user API key via iden.

        Notes:
            This contains the raw value. Callers are responsible for removing the ``shadow`` key.

        Args:
            iden (str): The key iden.

        Returns:
            dict: The key dictionary; or none.
        '''
        lkey = s_common.uhex(iden)
        user = self.slab.get(lkey, db=self.apikeydb)
        if user is None:
            return None
        buf = self.slab.get(user + b'apikey' + lkey, db=self.usermetadb)
        if buf is None:  # pragma: no cover
            logger.warning(f'Missing API key {iden} from user metadata for {s_common.ehex(user)}')
            return None
        kdef = s_msgpack.un(buf)  # This includes the shadow key
        return kdef

    async def listUserApiKeys(self, useriden):
        '''
        Get all the API keys for a user.

        Args:
            useriden (str): The user iden.

        Returns:
            list: A list of kdef values.
        '''
        user = await self.auth.reqUser(useriden)
        vals = []
        prefix = s_common.uhex(user.iden) + b'apikey'
        for lkey, valu in self.slab.scanByPref(prefix, db=self.usermetadb):
            kdef = s_msgpack.un(valu)
            kdef.pop('shadow')
            vals.append(kdef)
            await asyncio.sleep(0)
        return vals

    async def getApiKeys(self):
        '''
        Get all API keys in the cell.

        Yields:
            tuple: kdef values
        '''
        # yield all users API keys
        for keyiden, useriden in self.slab.scanByFull(db=self.apikeydb):
            lkey = useriden + b'apikey' + keyiden
            valu = self.slab.get(lkey, db=self.usermetadb)
            kdef = s_msgpack.un(valu)
            kdef.pop('shadow')
            yield kdef
            await asyncio.sleep(0)

    async def checkUserApiKey(self, key):
        '''
        Check if a user API key is valid.

        Notes:
            If the key is not valid, the dictionary will contain a ``mesg`` key.
            If the key is valid, the dictionary will contain the user def in a ``udef`` key,
            and the key metadata in a ``kdef`` key.

        Args:
            key (str): The API key to check.

        Returns:
            tuple: Tuple of two items, a boolean if the key is valid and a dictionary.
        '''
        isok, valu = s_passwd.parseApiKey(key)
        if isok is False:
            return False, {'mesg': 'API key is malformed.'}

        iden, secv = valu

        kdef = await self.getUserApiKey(iden)
        if kdef is None:
            return False, {'mesg': f'API key does not exist: {iden}'}

        user = kdef.get('user')
        udef = await self.getUserDef(user)
        if udef is None: # pragma: no cover
            return False, {'mesg': f'User does not exist for API key: {iden}', 'user': user}

        if udef.get('locked'):
            return False, {'mesg': f'User associated with API key is locked: {iden}',
                           'user': user, 'name': udef.get('name')}

        if ((expires := kdef.get('expires')) is not None):
            if s_common.now() > expires:
                return False, {'mesg': f'API key is expired: {iden}',
                               'user': user, 'name': udef.get('name')}

        shadow = kdef.pop('shadow')
        valid = await s_passwd.checkShadowV2(secv, shadow)
        if valid is False:
            return False, {'mesg': f'API key shadow mismatch: {iden}',
                           'user': user, 'name': udef.get('name')}

        return True, {'kdef': kdef, 'udef': udef}

    async def modUserApiKey(self, iden, key, valu):
        '''
        Update a value in the user API key metadata.

        Args:
            iden (str): Iden of the key to update.
            key (str): Name of the valu to update.
            valu: The new value.

        Returns:
            dict: An updated key metadata dictionary.
        '''
        if key not in ('name',):
            raise s_exc.BadArg(mesg=f'Cannot set {key} on user API keys.', name=key)

        kdef = await self.getUserApiKey(iden)
        if kdef is None:
            raise s_exc.NoSuchIden(mesg=f'User API key does not exist, cannot modify it: {iden}', iden=iden)
        useriden = kdef.get('user')
        user = await self.auth.reqUser(useriden)

        vals = {
            'updated': s_common.now()
        }
        if key == 'name':
            vals['name'] = valu

        kdef.update(vals)
        kdef = s_schemas.reqValidUserApiKeyDef(kdef)

        await self._push('user:apikey:edit', kdef.get('user'), iden, vals)

        logger.info(f'Updated HTTP API key {iden} for {user.name}, set {key}={valu}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, iden=iden,
                                                 status='MODIFY'))

        kdef.pop('shadow')
        return kdef

    @s_nexus.Pusher.onPush('user:apikey:edit')
    async def _setUserApiKey(self, user, iden, vals):
        lkey = s_common.uhex(user) + b'apikey' + s_common.uhex(iden)
        buf = self.slab.get(lkey, db=self.usermetadb)
        if buf is None:  # pragma: no cover
            raise s_exc.NoSuchIden(mesg=f'User API key does not exist: {iden}')
        kdef = s_msgpack.un(buf)
        kdef.update(vals)
        self.slab.put(lkey, s_msgpack.en(kdef), db=self.usermetadb)
        return kdef

    async def delUserApiKey(self, iden):
        '''
        Delete an existing API key.

        Args:
            iden (str): The iden of the API key to delete.

        Returns:
            bool: True indicating the key was deleted.
        '''
        kdef = await self.getUserApiKey(iden)
        if kdef is None:
            raise s_exc.NoSuchIden(mesg=f'User API key does not exist: {iden}')
        useriden = kdef.get('user')
        user = await self.auth.reqUser(useriden)
        ret = await self._push('user:apikey:del', useriden, iden)
        logger.info(f'Deleted HTTP API key {iden} for {user.name}',
                    extra=await self.getLogExtra(target_user=user.iden, target_username=user.name, iden=iden,
                                                 status='MODIFY'))
        return ret

    @s_nexus.Pusher.onPush('user:apikey:del')
    async def _delUserApiKey(self, user, iden):
        user = s_common.uhex(user)
        iden = s_common.uhex(iden)

        self.slab.delete(iden, db=self.apikeydb)
        self.slab.delete(user + b'apikey' + iden, db=self.usermetadb)
        return True

    async def _onUserDelEvnt(self, evnt):
        # Call callback for handling user:del events
        udef = evnt[1].get('udef')
        user = udef.get('iden')
        ukey = s_common.uhex(user)
        for lkey, buf in self.slab.scanByPref(ukey, db=self.usermetadb):
            suffix = lkey[16:]
            # Special handling for certain meta which has secondary indexes
            if suffix.startswith(b'apikey'):
                key_iden = suffix[6:]
                self.slab.delete(key_iden, db=self.apikeydb)
            self.slab.delete(lkey, db=self.usermetadb)
            await asyncio.sleep(0)

    async def _onUserLockEvnt(self, evnt):
        # Call callback for handling user:lock events
        useriden = evnt[1].get('user')
        locked = evnt[1].get('locked')

        if not locked:
            return

        # Find and delete all HTTP sessions for useriden
        for iden, sess in list(self.sessions.items()):
            if sess.info.get('user') == useriden:
                username = sess.info.get('username', '<unknown>')
                await self._delHttpSess(iden)
                logger.info(f'Invalidated HTTP session for locked user {username}',
                            extra=await self.getLogExtra(target_user=useriden))

    def _makeCachedSslCtx(self, opts):

        opts = dict(opts)

        cadir = self.conf.get('tls:ca:dir')

        if cadir is not None:
            sslctx = s_common.getSslCtx(cadir, purpose=ssl.Purpose.SERVER_AUTH)
        else:
            sslctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        if not opts['verify']:
            sslctx.check_hostname = False
            sslctx.verify_mode = ssl.CERT_NONE

        # crypto functions require reading certs/keys from disk so make a temp dir
        # to save any certs/keys to disk so they can be read.
        with self.getTempDir() as tmpdir:
            if opts.get('ca_cert'):
                ca_cert = opts.get('ca_cert').encode()
                with tempfile.NamedTemporaryFile(dir=tmpdir, mode='wb', delete=False) as fh:
                    fh.write(ca_cert)
                try:
                    sslctx.load_verify_locations(cafile=fh.name)
                except Exception as e:  # pragma: no cover
                    raise s_exc.BadArg(mesg=f'Error loading CA cert: {str(e)}') from None

            if not opts['client_cert']:
                return sslctx

            client_cert = opts['client_cert'].encode()

            if opts['client_key']:
                client_key = opts['client_key'].encode()
            else:
                client_key = None
                client_key_path = None

            with tempfile.NamedTemporaryFile(dir=tmpdir, mode='wb', delete=False) as fh:
                fh.write(client_cert)
                client_cert_path = fh.name

            if client_key:
                with tempfile.NamedTemporaryFile(dir=tmpdir, mode='wb', delete=False) as fh:
                    fh.write(client_key)
                    client_key_path = fh.name

            try:
                sslctx.load_cert_chain(client_cert_path, keyfile=client_key_path)
            except ssl.SSLError as e:
                raise s_exc.BadArg(mesg=f'Error loading client cert: {str(e)}') from None

        return sslctx

    def getCachedSslCtx(self, opts=None, verify=None):

        if opts is None:
            opts = {}

        if verify is not None:
            opts['verify'] = verify

        opts = s_schemas.reqValidSslCtxOpts(opts)

        key = tuple(sorted(opts.items()))
        return self._sslctx_cache.get(key)

    async def freeze(self, timeout=30):

        if self.paused:
            mesg = 'The service is already frozen.'
            raise s_exc.BadState(mesg=mesg)

        logger.warning(f'Freezing service for volume snapshot.')

        logger.warning('...acquiring nexus lock to prevent edits.')

        try:
            await asyncio.wait_for(self.nexslock.acquire(), timeout=timeout)

        except asyncio.TimeoutError:
            logger.warning('...nexus lock acquire timed out!')
            logger.warning('Aborting freeze and resuming normal operation.')

            mesg = 'Nexus lock acquire timed out.'
            raise s_exc.TimeOut(mesg=mesg)

        self.paused = True

        try:

            logger.warning('...committing pending transactions.')
            await self.slab.syncLoopOnce()

            logger.warning('...flushing dirty buffers to disk.')
            await s_task.executor(os.sync)

            logger.warning('...done!')

        except Exception:
            self.paused = False
            self.nexslock.release()
            logger.exception('Failed to freeze. Resuming normal operation.')
            raise

    async def resume(self):

        if not self.paused:
            mesg = 'The service is not frozen.'
            raise s_exc.BadState(mesg=mesg)

        logger.warning('Resuming normal operations from a freeze.')

        self.paused = False
        self.nexslock.release()
