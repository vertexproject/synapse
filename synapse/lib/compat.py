import os
import lmdb
import logging

import synapse.lib.msgpack as s_msgpack

'''
Various conversion routines for migrating / updating components.
'''

logger = logging.getLogger(__name__)

async def cellAuthToHive(dirn, auth):
    '''
    Migrate old cell Auth() data into a HiveAuth().
    '''
    logger.warning('migrating old cell auth to hive')

    path = os.path.join(dirn, 'auth.lmdb')

    lenv = lmdb.open(path, max_dbs=128)

    userdb = lenv.open_db(b'users')
    roledb = lenv.open_db(b'roles')

    with lenv.begin() as xact:

        with xact.cursor(db=roledb) as curs:

            for lkey, lval in curs.iternext():

                name = lkey.decode('utf8')
                info = s_msgpack.un(lval)

                role = auth.getRoleByName(name)
                if role is None:
                    role = await auth.addRole(name)

                rules = info.get('rules', ())

                await user.setRules(rules)

        with xact.cursor(db=userdb) as curs:

            for lkey, lval in curs.iternext():

                name = lkey.decode('utf8')
                info = s_msgpack.un(lval)

                user = auth.getUserByName(name)
                if user is None:
                    user = await auth.addUser(name)

                if info.get('admin', False):
                    await user.setAdmin(True)

                if info.get('locked', False):
                    await user.setLocked(True)

                #set this directly since we only have the shadow
                shadow = info.get('shadow')
                if shadow is not None:
                    await user.info.set('passwd', shadow)

                rules = info.get('rules', ())
                await user.setRules(rules)

                for name in info.get('roles', ()):
                    await user.grant(name)

    lenv.sync()
    lenv.close()
