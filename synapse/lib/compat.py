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

    migrated_roles = False
    migrated_users = False

    with lenv.begin() as xact:

        with xact.cursor(db=roledb) as curs:

            for lkey, lval in curs.iternext():

                name = lkey.decode('utf8')
                info = s_msgpack.un(lval)

                logger.info(f'Migrating role: {name}')

                role = auth.getRoleByName(name)
                if role is None:
                    logger.info(f'Creating role: {name}')
                    role = await auth.addRole(name)

                rules = info.get('rules', ())

                await role.setRules(rules)

                migrated_roles = True

        if not migrated_roles:  # pragma: no cover
            logger.info('No roles were migrated.')

        with xact.cursor(db=userdb) as curs:

            for lkey, lval in curs.iternext():

                name = lkey.decode('utf8')
                info = s_msgpack.un(lval)

                logger.info(f'Migrating user: {name}')

                user = auth.getUserByName(name)
                if user is None:
                    logger.info(f'Creating user: {name}')
                    user = await auth.addUser(name)

                if info.get('admin', False):
                    await user.setAdmin(True)

                if info.get('locked', False):
                    await user.setLocked(True)

                # set this directly since we only have the shadow
                shadow = info.get('shadow')
                if shadow is not None:
                    await user.info.set('passwd', shadow)

                rules = info.get('rules', ())
                await user.setRules(rules)

                for name in info.get('roles', ()):
                    await user.grant(name)

                migrated_users = True

        if not migrated_users:  # pragma: no cover
            logger.info('No users were migrated.')

    lenv.sync()
    lenv.close()
