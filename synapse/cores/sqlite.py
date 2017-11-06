import queue
import logging
import sqlite3

import regex

import synapse.common as s_common

import synapse.cores.xact as s_xact
import synapse.cores.common as s_cores_common
import synapse.cores.storage as s_cores_storage

logger = logging.getLogger(__name__)

stashre = regex.compile('{{([A-Z]+)}}')

int_t = type(0)
str_t = type('synapse')
none_t = type(None)

def initSqliteCortex(link, conf=None, storconf=None):
    '''
    Initialize a Sqlite based Cortex from a link tufo.

    Args:
        link ((str, dict)): Link tufo.
        conf (dict): Configable opts for the Cortex object.
        storconf (dict): Configable opts for the storage object.

    Returns:
        s_cores_common.Cortex: Cortex created from the link tufo.
    '''
    if not conf:
        conf = {}
    if not storconf:
        storconf = {}

    store = SqliteStorage(link, **storconf)
    return s_cores_common.Cortex(link, store, **conf)

class SqlXact(s_xact.StoreXact):

    def _coreXactInit(self):
        self.db = None
        self.cursor = None

    def _coreXactCommit(self):
        self.cursor.execute('COMMIT')

    def _coreXactBegin(self):
        self.cursor.execute('BEGIN TRANSACTION')

    def _coreXactAcquire(self):
        self.db = self.store.dbpool.get()
        self.cursor = self.db.cursor()

    def _coreXactRelease(self):
        self.cursor.close()
        self.store.dbpool.put(self.db)

        self.db = None
        self.cursor = None

class DbPool:
    '''
    The DbPool allows generic db connection pooling using
    a factory/ctor method and a python queue.

    Example:

        def connectdb():
            # do stuff
            return db

        pool = DbPool(3, connectdb)

    '''

    def __init__(self, size, ctor):
        # TODO: high/low water marks
        self.size = size
        self.ctor = ctor
        self.dbque = queue.Queue()

        for i in range(size):
            db = ctor()
            self.put(db)

    def put(self, db):
        '''
        Add/Return a db connection to the pool.
        '''
        self.dbque.put(db)

    def get(self):
        return self.dbque.get()

class SqliteStorage(s_cores_storage.Storage):

    dblim = -1

    _t_istable = '''
        SELECT
            name
        FROM
            sqlite_master
        WHERE
            type='table'
        AND
            name={{NAME}}
    '''

    _t_inittable = '''
    CREATE TABLE {{TABLE}} (
        iden VARCHAR,
        prop VARCHAR,
        strval TEXT,
        intval BIGINT,
        tstamp BIGINT
    );
    '''

    _t_init_blobtable = '''
    CREATE TABLE {{BLOB_TABLE}} (
         k VARCHAR,
         v BLOB
    );
    '''

    _t_init_iden_idx = 'CREATE INDEX {{TABLE}}_iden_idx ON {{TABLE}} (iden,prop)'
    _t_init_prop_idx = 'CREATE INDEX {{TABLE}}_prop_time_idx ON {{TABLE}} (prop,tstamp)'
    _t_init_strval_idx = 'CREATE INDEX {{TABLE}}_strval_idx ON {{TABLE}} (prop,strval,tstamp)'
    _t_init_intval_idx = 'CREATE INDEX {{TABLE}}_intval_idx ON {{TABLE}} (prop,intval,tstamp)'
    _t_init_blobtable_idx = 'CREATE UNIQUE INDEX {{BLOB_TABLE}}_indx ON {{BLOB_TABLE}} (k)'

    _t_addrows = 'INSERT INTO {{TABLE}} (iden,prop,strval,intval,tstamp) VALUES ({{IDEN}},{{PROP}},{{STRVAL}},{{INTVAL}},{{TSTAMP}})'
    _t_getrows_by_iden = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}}'
    _t_getrows_by_range = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{MINVALU}} AND intval < {{MAXVALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_le = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval <= {{VALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_ge = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{VALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_iden_prop = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}}'
    _t_getrows_by_iden_prop_intval = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND intval={{VALU}}'
    _t_getrows_by_iden_prop_strval = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND strval={{VALU}}'

    _t_getrows_by_iden_range = 'SELECT * FROM {{TABLE}} WHERE iden >= {{LOWERBOUND}} and iden < {{UPPERBOUND}}'
    _t_getiden_max = 'SELECT MAX(iden) FROM {{TABLE}}'
    _t_getiden_min = 'SELECT MIN(iden) FROM {{TABLE}}'

    ################################################################################
    _t_blob_set = 'INSERT OR REPLACE INTO {{BLOB_TABLE}} (k, v) VALUES ({{KEY}}, {{VALU}})'
    _t_blob_get = 'SELECT v FROM {{BLOB_TABLE}} WHERE k={{KEY}}'
    _t_blob_del = 'DELETE FROM {{BLOB_TABLE}} WHERE k={{KEY}}'
    _t_blob_get_keys = 'SELECT k FROM {{BLOB_TABLE}}'

    ################################################################################
    _t_getrows_by_prop = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_int = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} LIMIT {{LIMIT}}'

    _t_getrows_by_prop_wmin = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp >= {{MINTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_int_wmin = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp >= {{MINTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wmin = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp >= {{MINTIME}} LIMIT {{LIMIT}}'

    _t_getrows_by_prop_wmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_int_wmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'

    _t_getrows_by_prop_wminmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_int_wminmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp >= {{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wminmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp >= {{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    ################################################################################
    _t_getsize_by_prop = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_int = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} LIMIT {{LIMIT}}'

    _t_getsize_by_prop_wmin = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_int_wmin = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wmin = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}}'

    _t_getsize_by_prop_wmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_int_wmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'

    _t_getsize_by_prop_wminmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_int_wminmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wminmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    ################################################################################

    _t_getsize_by_range = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{MINVALU}} AND intval < {{MAXVALU}} LIMIT {{LIMIT}}'
    _t_getsize_by_le = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} and intval <= {{VALU}} LIMIT {{LIMIT}}'
    _t_getsize_by_ge = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{VALU}} LIMIT {{LIMIT}}'

    _t_delrows_by_iden = 'DELETE FROM {{TABLE}} WHERE iden={{IDEN}}'
    _t_delrows_by_iden_prop = 'DELETE FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}}'
    _t_delrows_by_iden_prop_strval = 'DELETE FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND strval={{VALU}}'
    _t_delrows_by_iden_prop_intval = 'DELETE FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND intval={{VALU}}'

    ################################################################################
    _t_delrows_by_prop = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}}'
    _t_delrows_by_prop_int = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}}'
    _t_delrows_by_prop_str = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}}'

    _t_delrows_by_prop_wmin = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}}'
    _t_delrows_by_prop_int_wmin = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}}'
    _t_delrows_by_prop_str_wmin = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}}'

    _t_delrows_by_prop_wmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp<{{MAXTIME}}'
    _t_delrows_by_prop_int_wmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp<{{MAXTIME}}'
    _t_delrows_by_prop_str_wmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp<{{MAXTIME}}'

    _t_delrows_by_prop_wminmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}}'
    _t_delrows_by_prop_int_wminmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}}'
    _t_delrows_by_prop_str_wminmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}}'

    ################################################################################
    _t_getjoin_by_prop = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_int = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} LIMIT {{LIMIT}})'

    _t_getjoin_by_prop_wmin = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_int_wmin = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wmin = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} LIMIT {{LIMIT}})'

    _t_getjoin_by_prop_wmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_int_wmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'

    _t_getjoin_by_prop_wminmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_int_wminmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wminmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'

    _t_getjoin_by_range_int = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and {{MINVALU}} <= intval AND intval < {{MAXVALU}} LIMIT {{LIMIT}})'
    _t_getjoin_by_range_str = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and {{MINVALU}} <= strval AND strval < {{MAXVALU}} LIMIT {{LIMIT}})'

    _t_getjoin_by_le_int = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and intval <= {{VALU}} LIMIT {{LIMIT}})'
    _t_getjoin_by_ge_int = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{VALU}} LIMIT {{LIMIT}})'

    ################################################################################
    _t_deljoin_by_prop = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}})'
    _t_deljoin_by_prop_int = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}})'
    _t_deljoin_by_prop_str = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}})'

    _t_deljoin_by_prop_wmin = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} )'
    _t_deljoin_by_prop_int_wmin = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} )'
    _t_deljoin_by_prop_str_wmin = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} )'

    _t_deljoin_by_prop_wmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp<{{MAXTIME}} )'
    _t_deljoin_by_prop_int_wmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp<{{MAXTIME}} )'
    _t_deljoin_by_prop_str_wmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp<{{MAXTIME}} )'

    _t_deljoin_by_prop_wminmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND tstamp>={{MINTIME}} AND tstamp < {{MAXTIME}})'
    _t_deljoin_by_prop_int_wminmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND intval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}})'
    _t_deljoin_by_prop_str_wminmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND strval={{VALU}} AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}})'

    ################################################################################
    _t_uprows_by_iden_prop_str = 'UPDATE {{TABLE}} SET strval={{VALU}} WHERE iden={{IDEN}} and prop={{PROP}}'
    _t_uprows_by_iden_prop_int = 'UPDATE {{TABLE}} SET intval={{VALU}} WHERE iden={{IDEN}} and prop={{PROP}}'
    _t_uprows_by_prop_prop = 'UPDATE {{TABLE}} SET prop={{NEWVALU}} WHERE prop={{OLDVALU}}'
    _t_uprows_by_prop_val_int = 'UPDATE {{TABLE}} SET intval={{NEWVALU}} WHERE prop={{PROP}} and intval={{OLDVALU}}'
    _t_uprows_by_prop_val_str = 'UPDATE {{TABLE}} SET strval={{NEWVALU}} WHERE prop={{PROP}} and strval={{OLDVALU}}'

    def _initDbInfo(self):
        name = self._link[1].get('path')[1:]
        if not name:
            raise Exception('No Path Specified!')

        if name.find(':') == -1:
            name = s_common.genpath(name)

        return {'name': name}

    def getStoreXact(self, size=None, core=None):
        return SqlXact(self, size=size, core=core)

    def _getDbLimit(self, limit):
        if limit is not None:
            return limit
        return self.dblim

    def rowsByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        q = self._q_getrows_by_range

        minvalu, maxvalu = valu[0], valu[1]

        rows = self.select(q, prop=prop, minvalu=minvalu, maxvalu=maxvalu, limit=limit)
        return self._foldTypeCols(rows)

    def rowsByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_ge

        rows = self.select(q, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def rowsByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_le
        rows = self.select(q, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def sizeByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_range
        minvalu, maxvalu = valu[0], valu[1]
        return self.select(q, prop=prop, minvalu=minvalu, maxvalu=maxvalu, limit=limit)[0][0]

    def sizeByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_ge
        return self.select(q, prop=prop, valu=valu, limit=limit)[0][0]

    def sizeByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_le
        args = [prop, valu, limit]
        return self.select(q, prop=prop, valu=valu, limit=limit)[0][0]

    def _initDbConn(self):
        dbinfo = self._initDbInfo()
        dbname = dbinfo.get('name')
        db = sqlite3.connect(dbname, check_same_thread=False)
        db.isolation_level = None
        def onfini():
            db.close()
        self.onfini(onfini)
        return db

    def _getTableName(self):
        return 'syncortex'

    def _addVarDecor(self, name):
        return ':%s' % (name,)

    def _initCoreStor(self):
        self.dbpool = self._link[1].get('dbpool')
        if self.dbpool is None:
            pool = int(self._link[1].get('pool', 1))
            self.dbpool = DbPool(pool, self._initDbConn)

        table = self._getTableName()

        self._initCorQueries()
        self._initCorTables(table)

    def _prepQuery(self, query):
        # prep query strings by replacing all %s with table name
        # and all ? with db specific variable token
        table = self._getTableName()
        query = query.replace('{{TABLE}}', table)

        for name in stashre.findall(query):
            query = query.replace('{{%s}}' % name, self._addVarDecor(name.lower()))

        return query

    def _prepBlobQuery(self, query):
        # prep query strings by replacing all %s with table name
        # and all ? with db specific variable token
        table = self._getTableName()
        table += '_blob'
        query = query.replace('{{BLOB_TABLE}}', table)

        for name in stashre.findall(query):
            query = query.replace('{{%s}}' % name, self._addVarDecor(name.lower()))

        return query

    def _initCorQueries(self):
        self._q_istable = self._prepQuery(self._t_istable)
        self._q_inittable = self._prepQuery(self._t_inittable)
        self._q_init_blobtable = self._prepBlobQuery(self._t_init_blobtable)

        self._q_init_iden_idx = self._prepQuery(self._t_init_iden_idx)
        self._q_init_prop_idx = self._prepQuery(self._t_init_prop_idx)
        self._q_init_strval_idx = self._prepQuery(self._t_init_strval_idx)
        self._q_init_intval_idx = self._prepQuery(self._t_init_intval_idx)
        self._q_init_blobtable_idx = self._prepBlobQuery(self._t_init_blobtable_idx)

        self._q_addrows = self._prepQuery(self._t_addrows)
        self._q_getrows_by_iden = self._prepQuery(self._t_getrows_by_iden)
        self._q_getrows_by_range = self._prepQuery(self._t_getrows_by_range)
        self._q_getrows_by_ge = self._prepQuery(self._t_getrows_by_ge)
        self._q_getrows_by_le = self._prepQuery(self._t_getrows_by_le)
        self._q_getrows_by_iden_prop = self._prepQuery(self._t_getrows_by_iden_prop)
        self._q_getrows_by_iden_prop_intval = self._prepQuery(self._t_getrows_by_iden_prop_intval)
        self._q_getrows_by_iden_prop_strval = self._prepQuery(self._t_getrows_by_iden_prop_strval)

        self._q_getrows_by_iden_range = self._prepQuery(self._t_getrows_by_iden_range)
        self._q_getiden_max = self._prepQuery(self._t_getiden_max)
        self._q_getiden_min = self._prepQuery(self._t_getiden_min)

        self._q_blob_get = self._prepBlobQuery(self._t_blob_get)
        self._q_blob_set = self._prepBlobQuery(self._t_blob_set)
        self._q_blob_del = self._prepBlobQuery(self._t_blob_del)
        self._q_blob_get_keys = self._prepBlobQuery(self._t_blob_get_keys)

        ###################################################################################
        self._q_getrows_by_prop = self._prepQuery(self._t_getrows_by_prop)
        self._q_getrows_by_prop_wmin = self._prepQuery(self._t_getrows_by_prop_wmin)
        self._q_getrows_by_prop_wmax = self._prepQuery(self._t_getrows_by_prop_wmax)
        self._q_getrows_by_prop_wminmax = self._prepQuery(self._t_getrows_by_prop_wminmax)
        ###################################################################################
        self._q_getrows_by_prop_int = self._prepQuery(self._t_getrows_by_prop_int)
        self._q_getrows_by_prop_int_wmin = self._prepQuery(self._t_getrows_by_prop_int_wmin)
        self._q_getrows_by_prop_int_wmax = self._prepQuery(self._t_getrows_by_prop_int_wmax)
        self._q_getrows_by_prop_int_wminmax = self._prepQuery(self._t_getrows_by_prop_int_wminmax)
        ###################################################################################
        self._q_getrows_by_prop_str = self._prepQuery(self._t_getrows_by_prop_str)
        self._q_getrows_by_prop_str_wmin = self._prepQuery(self._t_getrows_by_prop_str_wmin)
        self._q_getrows_by_prop_str_wmax = self._prepQuery(self._t_getrows_by_prop_str_wmax)
        self._q_getrows_by_prop_str_wminmax = self._prepQuery(self._t_getrows_by_prop_str_wminmax)
        ###################################################################################
        self._q_getjoin_by_prop = self._prepQuery(self._t_getjoin_by_prop)
        self._q_getjoin_by_prop_wmin = self._prepQuery(self._t_getjoin_by_prop_wmin)
        self._q_getjoin_by_prop_wmax = self._prepQuery(self._t_getjoin_by_prop_wmax)
        self._q_getjoin_by_prop_wminmax = self._prepQuery(self._t_getjoin_by_prop_wminmax)
        ###################################################################################
        self._q_getjoin_by_prop_int = self._prepQuery(self._t_getjoin_by_prop_int)
        self._q_getjoin_by_prop_int_wmin = self._prepQuery(self._t_getjoin_by_prop_int_wmin)
        self._q_getjoin_by_prop_int_wmax = self._prepQuery(self._t_getjoin_by_prop_int_wmax)
        self._q_getjoin_by_prop_int_wminmax = self._prepQuery(self._t_getjoin_by_prop_int_wminmax)
        ###################################################################################
        self._q_getjoin_by_prop_str = self._prepQuery(self._t_getjoin_by_prop_str)
        self._q_getjoin_by_prop_str_wmin = self._prepQuery(self._t_getjoin_by_prop_str_wmin)
        self._q_getjoin_by_prop_str_wmax = self._prepQuery(self._t_getjoin_by_prop_str_wmax)
        self._q_getjoin_by_prop_str_wminmax = self._prepQuery(self._t_getjoin_by_prop_str_wminmax)
        ###################################################################################
        self._q_getsize_by_prop = self._prepQuery(self._t_getsize_by_prop)
        self._q_getsize_by_prop_wmin = self._prepQuery(self._t_getsize_by_prop_wmin)
        self._q_getsize_by_prop_wmax = self._prepQuery(self._t_getsize_by_prop_wmax)
        self._q_getsize_by_prop_wminmax = self._prepQuery(self._t_getsize_by_prop_wminmax)
        ###################################################################################
        self._q_getsize_by_prop_int = self._prepQuery(self._t_getsize_by_prop_int)
        self._q_getsize_by_prop_int_wmin = self._prepQuery(self._t_getsize_by_prop_int_wmin)
        self._q_getsize_by_prop_int_wmax = self._prepQuery(self._t_getsize_by_prop_int_wmax)
        self._q_getsize_by_prop_int_wminmax = self._prepQuery(self._t_getsize_by_prop_int_wminmax)
        ###################################################################################
        self._q_getsize_by_prop_str = self._prepQuery(self._t_getsize_by_prop_str)
        self._q_getsize_by_prop_str_wmin = self._prepQuery(self._t_getsize_by_prop_str_wmin)
        self._q_getsize_by_prop_str_wmax = self._prepQuery(self._t_getsize_by_prop_str_wmax)
        self._q_getsize_by_prop_str_wminmax = self._prepQuery(self._t_getsize_by_prop_str_wminmax)
        ###################################################################################

        self.qbuild = {
            'rowsbyprop': {
                (none_t, none_t, none_t): self._q_getrows_by_prop,
                (none_t, int_t, none_t): self._q_getrows_by_prop_wmin,
                (none_t, none_t, int_t): self._q_getrows_by_prop_wmax,
                (none_t, int_t, int_t): self._q_getrows_by_prop_wminmax,

                (int_t, none_t, none_t): self._q_getrows_by_prop_int,
                (int_t, int_t, none_t): self._q_getrows_by_prop_int_wmin,
                (int_t, none_t, int_t): self._q_getrows_by_prop_int_wmax,
                (int_t, int_t, int_t): self._q_getrows_by_prop_int_wminmax,

                (str_t, none_t, none_t): self._q_getrows_by_prop_str,
                (str_t, int_t, none_t): self._q_getrows_by_prop_str_wmin,
                (str_t, none_t, int_t): self._q_getrows_by_prop_str_wmax,
                (str_t, int_t, int_t): self._q_getrows_by_prop_str_wminmax,
            },
            'joinbyprop': {
                (none_t, none_t, none_t): self._q_getjoin_by_prop,
                (none_t, int_t, none_t): self._q_getjoin_by_prop_wmin,
                (none_t, none_t, int_t): self._q_getjoin_by_prop_wmax,
                (none_t, int_t, int_t): self._q_getjoin_by_prop_wminmax,

                (int_t, none_t, none_t): self._q_getjoin_by_prop_int,
                (int_t, int_t, none_t): self._q_getjoin_by_prop_int_wmin,
                (int_t, none_t, int_t): self._q_getjoin_by_prop_int_wmax,
                (int_t, int_t, int_t): self._q_getjoin_by_prop_int_wminmax,

                (str_t, none_t, none_t): self._q_getjoin_by_prop_str,
                (str_t, int_t, none_t): self._q_getjoin_by_prop_str_wmin,
                (str_t, none_t, int_t): self._q_getjoin_by_prop_str_wmax,
                (str_t, int_t, int_t): self._q_getjoin_by_prop_str_wminmax,
            },
            'sizebyprop': {
                (none_t, none_t, none_t): self._q_getsize_by_prop,
                (none_t, int_t, none_t): self._q_getsize_by_prop_wmin,
                (none_t, none_t, int_t): self._q_getsize_by_prop_wmax,
                (none_t, int_t, int_t): self._q_getsize_by_prop_wminmax,

                (int_t, none_t, none_t): self._q_getsize_by_prop_int,
                (int_t, int_t, none_t): self._q_getsize_by_prop_int_wmin,
                (int_t, none_t, int_t): self._q_getsize_by_prop_int_wmax,
                (int_t, int_t, int_t): self._q_getsize_by_prop_int_wminmax,

                (str_t, none_t, none_t): self._q_getsize_by_prop_str,
                (str_t, int_t, none_t): self._q_getsize_by_prop_str_wmin,
                (str_t, none_t, int_t): self._q_getsize_by_prop_str_wmax,
                (str_t, int_t, int_t): self._q_getsize_by_prop_str_wminmax,
            },
            'delrowsbyprop': {
                (none_t, none_t, none_t): self._prepQuery(self._t_delrows_by_prop),
                (none_t, int_t, none_t): self._prepQuery(self._t_delrows_by_prop_wmin),
                (none_t, none_t, int_t): self._prepQuery(self._t_delrows_by_prop_wmax),
                (none_t, int_t, int_t): self._prepQuery(self._t_delrows_by_prop_wminmax),

                (int_t, none_t, none_t): self._prepQuery(self._t_delrows_by_prop_int),
                (int_t, int_t, none_t): self._prepQuery(self._t_delrows_by_prop_int_wmin),
                (int_t, none_t, int_t): self._prepQuery(self._t_delrows_by_prop_int_wmax),
                (int_t, int_t, int_t): self._prepQuery(self._t_delrows_by_prop_int_wminmax),

                (str_t, none_t, none_t): self._prepQuery(self._t_delrows_by_prop_str),
                (str_t, int_t, none_t): self._prepQuery(self._t_delrows_by_prop_str_wmin),
                (str_t, none_t, int_t): self._prepQuery(self._t_delrows_by_prop_str_wmax),
                (str_t, int_t, int_t): self._prepQuery(self._t_delrows_by_prop_str_wminmax),
            },
            'deljoinbyprop': {
                (none_t, none_t, none_t): self._prepQuery(self._t_deljoin_by_prop),
                (none_t, int_t, none_t): self._prepQuery(self._t_deljoin_by_prop_wmin),
                (none_t, none_t, int_t): self._prepQuery(self._t_deljoin_by_prop_wmax),
                (none_t, int_t, int_t): self._prepQuery(self._t_deljoin_by_prop_wminmax),

                (int_t, none_t, none_t): self._prepQuery(self._t_deljoin_by_prop_int),
                (int_t, int_t, none_t): self._prepQuery(self._t_deljoin_by_prop_int_wmin),
                (int_t, none_t, int_t): self._prepQuery(self._t_deljoin_by_prop_int_wmax),
                (int_t, int_t, int_t): self._prepQuery(self._t_deljoin_by_prop_int_wminmax),

                (str_t, none_t, none_t): self._prepQuery(self._t_deljoin_by_prop_str),
                (str_t, int_t, none_t): self._prepQuery(self._t_deljoin_by_prop_str_wmin),
                (str_t, none_t, int_t): self._prepQuery(self._t_deljoin_by_prop_str_wmax),
                (str_t, int_t, int_t): self._prepQuery(self._t_deljoin_by_prop_str_wminmax),
            }
        }

        self._q_getsize_by_prop = self._prepQuery(self._t_getsize_by_prop)

        self._q_getsize_by_ge = self._prepQuery(self._t_getsize_by_ge)
        self._q_getsize_by_le = self._prepQuery(self._t_getsize_by_le)
        self._q_getsize_by_range = self._prepQuery(self._t_getsize_by_range)

        self._q_delrows_by_iden = self._prepQuery(self._t_delrows_by_iden)
        self._q_delrows_by_iden_prop = self._prepQuery(self._t_delrows_by_iden_prop)
        self._q_delrows_by_iden_prop_intval = self._prepQuery(self._t_delrows_by_iden_prop_intval)
        self._q_delrows_by_iden_prop_strval = self._prepQuery(self._t_delrows_by_iden_prop_strval)

        self._q_uprows_by_iden_prop_str = self._prepQuery(self._t_uprows_by_iden_prop_str)
        self._q_uprows_by_iden_prop_int = self._prepQuery(self._t_uprows_by_iden_prop_int)
        self._q_uprows_by_prop_prop = self._prepQuery(self._t_uprows_by_prop_prop)
        self._q_uprows_by_prop_val_str = self._prepQuery(self._t_uprows_by_prop_val_str)
        self._q_uprows_by_prop_val_int = self._prepQuery(self._t_uprows_by_prop_val_int)

        self._q_getjoin_by_range_str = self._prepQuery(self._t_getjoin_by_range_str)
        self._q_getjoin_by_range_int = self._prepQuery(self._t_getjoin_by_range_int)

        self._q_getjoin_by_ge_int = self._prepQuery(self._t_getjoin_by_ge_int)
        self._q_getjoin_by_le_int = self._prepQuery(self._t_getjoin_by_le_int)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable, name=name))

    def _initCorTables(self, table):

        revs = [
            (0, self._rev0)
        ]

        max_rev = max([rev for rev, func in revs])
        vsn_str = 'syn:core:{}:version'.format(self.getStoreType())

        if not self._checkForTable(table):
            # We are a new cortex, stamp in tables and set
            # blob values and move along.
            self._initCorTable(table)
            self.setBlobValu(vsn_str, max_rev)
            return

        # Strap in the blobstore if it doesn't exist - this allows us to have
        # a helper which doesn't have to care about queries against a table
        # which may not exist.
        blob_table = table + '_blob'
        if not self._checkForTable(blob_table):
            with self.getCoreXact() as xact:
                xact.cursor.execute(self._q_init_blobtable)
                xact.cursor.execute(self._q_init_blobtable_idx)

        # Apply storage layer revisions
        self._revCorVers(revs)

    def _initCorTable(self, name):
        with self.getCoreXact() as xact:
            xact.cursor.execute(self._q_inittable)
            xact.cursor.execute(self._q_init_iden_idx)
            xact.cursor.execute(self._q_init_prop_idx)
            xact.cursor.execute(self._q_init_strval_idx)
            xact.cursor.execute(self._q_init_intval_idx)
            xact.cursor.execute(self._q_init_blobtable)
            xact.cursor.execute(self._q_init_blobtable_idx)

    def _rev0(self):
        # Simple rev0 function stub.
        # If we're here, we're clearly an existing cortex and
        #  we need to have this valu set.
        self.setBlobValu('syn:core:created', s_common.now())

    def _addRows(self, rows):
        args = []
        for i, p, v, t in rows:
            if isinstance(v, int):
                args.append({'iden': i, 'prop': p, 'intval': v, 'strval': None, 'tstamp': t})
            else:
                args.append({'iden': i, 'prop': p, 'intval': None, 'strval': v, 'tstamp': t})

        with self.getCoreXact() as xact:
            xact.cursor.executemany(self._q_addrows, args)

    def update(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q, args)
            return xact.cursor.rowcount

    def select(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q, args)
            return xact.cursor.fetchall()

    def delete(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q, args)

    def _foldTypeCols(self, rows):
        ret = []
        for iden, prop, intval, strval, tstamp in rows:

            if intval is not None:
                ret.append((iden, prop, intval, tstamp))
            else:
                ret.append((iden, prop, strval, tstamp))

        return ret

    def getRowsById(self, iden):
        rows = self.select(self._q_getrows_by_iden, iden=iden)
        return self._foldTypeCols(rows)

    def getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('sizebyprop', prop, valu=valu, limit=limit, mintime=mintime, maxtime=maxtime)
        return rows[0][0]

    def getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('rowsbyprop', prop, valu=valu, limit=limit, mintime=mintime, maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _joinsByRange(self, prop, valu, limit=None):
        minvalu, maxvalu = valu[0], valu[1]

        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_range_int, prop=prop, minvalu=minvalu, maxvalu=maxvalu, limit=limit)
        return self._foldTypeCols(rows)

    def _joinsByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_le_int, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def _joinsByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_ge_int, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def _runPropQuery(self, name, prop, valu=None, limit=None, mintime=None, maxtime=None, meth=None, nolim=False):
        limit = self._getDbLimit(limit)

        qkey = (type(valu), type(mintime), type(maxtime))

        qstr = self.qbuild[name][qkey]
        if meth is None:
            meth = self.select

        rows = meth(qstr, prop=prop, valu=valu, limit=limit, mintime=mintime, maxtime=maxtime)

        return rows

    def _delRowsByIdProp(self, iden, prop, valu=None):
        if valu is None:
            return self.delete(self._q_delrows_by_iden_prop, iden=iden, prop=prop)

        if isinstance(valu, int):
            return self.delete(self._q_delrows_by_iden_prop_intval, iden=iden, prop=prop, valu=valu)
        else:
            return self.delete(self._q_delrows_by_iden_prop_strval, iden=iden, prop=prop, valu=valu)

    def getRowsByIdProp(self, iden, prop, valu=None):
        if valu is None:
            rows = self.select(self._q_getrows_by_iden_prop, iden=iden, prop=prop)
            return self._foldTypeCols(rows)

        if isinstance(valu, int):
            rows = self.select(self._q_getrows_by_iden_prop_intval, iden=iden, prop=prop, valu=valu)
        else:
            rows = self.select(self._q_getrows_by_iden_prop_strval, iden=iden, prop=prop, valu=valu)
        return self._foldTypeCols(rows)

    def _setRowsByIdProp(self, iden, prop, valu):
        if isinstance(valu, int):
            count = self.update(self._q_uprows_by_iden_prop_int, iden=iden, prop=prop, valu=valu)
        else:
            count = self.update(self._q_uprows_by_iden_prop_str, iden=iden, prop=prop, valu=valu)

        if count == 0:
            rows = [(iden, prop, valu, s_common.now()), ]
            self._addRows(rows)

    def _delRowsById(self, iden):
        self.delete(self._q_delrows_by_iden, iden=iden)

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('deljoinbyprop', prop, valu=valu, mintime=mintime, maxtime=maxtime, meth=self.delete, nolim=True)

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self._runPropQuery('joinbyprop', prop, valu=valu, limit=limit, mintime=mintime, maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('delrowsbyprop', prop, valu=valu, mintime=mintime, maxtime=maxtime, meth=self.delete, nolim=True)

    def _updateProperty(self, oldprop, newprop):
        return self.update(self._q_uprows_by_prop_prop, oldvalu=oldprop, newvalu=newprop)

    def _updatePropertyValu(self, prop, oldval, newval):
        if isinstance(oldval, int):
            return self.update(self._q_uprows_by_prop_val_int, oldvalu=oldval, newvalu=newval, prop=prop)
        return self.update(self._q_uprows_by_prop_val_str, oldvalu=oldval, newvalu=newval, prop=prop)

    def _genStoreRows(self, **kwargs):
        '''
        Generator which yields lists of rows from the DB in tuple form.

        This works by performing range lookups on iden prefixes over the range
        of 00000000000000000000000000000000 to ffffffffffffffffffffffffffffffff.
        The runtime of this is dependent on the number of rows in the DB,
        but is generally the fastest approach to getting rows out of the DB
        in a linear time fashion.

        Args:
            **kwargs: Optional args.

        Notes:
            The following values may be passed in as kwargs in order to
            impact the performance of _genStoreRows:

            * slicebytes: The number of bytes to use when generating the iden
              prefix values.  This defaults to 4.
            * incvalu (int): The amount in which to increase the internal
              counter used to generate the prefix by on each pass.  This value
              determines the width of the iden range looked up at a single
              time.  This defaults to 4.

            The number of queries which are executed by this generator is
            equal to (16 ** slicebytes) / incvalu.  This defaults to 16384
            queries.

        Returns:
            list: List of tuples, each containing an iden, property, value and timestamp.
        '''
        slicebytes = kwargs.get('slicebytes', 4)
        incvalu = kwargs.get('incvalu', 4)

        # Compute upper and lower bounds up front
        lowest_iden = '00000000000000000000000000000000'
        highst_iden = 'ffffffffffffffffffffffffffffffff'

        highest_core_iden = self.select(self._q_getiden_max)[0][0]
        if not highest_core_iden:
            # No rows present at all - return early
            return

        fmt = '{{:0={}x}}'.format(slicebytes)
        maxv = 16 ** slicebytes
        num_queries = int(maxv / incvalu)
        q_count = 0
        percentaged = {}
        if num_queries > 128:
            percentaged = {int((num_queries * i) / 100): i for i in range(100)}

        # Setup lower bound and first upper bound
        lowerbound = lowest_iden[:slicebytes]
        c = int(lowerbound, 16) + incvalu
        upperbound = fmt.format(c)

        logger.info('Dumping rows - slicebytes %s, incvalu %s', slicebytes, incvalu)
        logger.info('Will perform %s SQL queries given the slicebytes/incvalu calculations.', num_queries)
        while True:
            # Check to see if maxv is reached
            if c >= maxv:
                upperbound = highst_iden
            rows = self.select(self._q_getrows_by_iden_range, lowerbound=lowerbound, upperbound=upperbound)
            q_count += 1
            completed_rate = percentaged.get(q_count)
            if completed_rate:
                logger.info('Completed %s%% queries', completed_rate)
            if rows:
                rows = self._foldTypeCols(rows)
                # print(len(rows), lowerbound, upperbound)
                yield rows
            if c >= maxv:
                break
            # Increment and continue
            c += incvalu
            lowerbound = upperbound
            upperbound = fmt.format(c)
            continue

        # Edge case because _q_getrows_by_iden_range is exclusive on the upper bound.
        if highest_core_iden == highst_iden:
            rows = self.select(self._q_getrows_by_iden, iden=highest_core_iden)
            rows = self._foldTypeCols(rows)
            yield rows

    def getStoreType(self):
        return 'sqlite'

    def _getBlobValu(self, key):
        rows = self._getBlobValuRows(key)

        if not rows:
            return None

        if len(rows) > 1:  # pragma: no cover
            raise s_common.BadCoreStore(store=self.getCoreType(), mesg='Too many blob rows received.')

        return rows[0][0]

    def _getBlobValuRows(self, key):
        rows = self.select(self._q_blob_get, key=key)
        return rows

    def _prepBlobValu(self, valu):
        return sqlite3.Binary(valu)

    def _setBlobValu(self, key, valu):
        v = self._prepBlobValu(valu)
        self.update(self._q_blob_set, key=key, valu=v)
        return valu

    def _hasBlobValu(self, key):
        rows = self._getBlobValuRows(key)

        if len(rows) > 1:  # pragma: no cover
            raise s_common.BadCoreStore(store=self.getCoreType(), mesg='Too many blob rows received.')

        if not rows:
            return False
        return True

    def _delBlobValu(self, key):
        ret = self._getBlobValu(key)
        if ret is None:  # pragma: no cover
            # We should never get here, but if we do, throw an exception.
            raise s_common.NoSuchName(name=key, mesg='Cannot delete key which is not present in the blobstore.')
        self.delete(self._q_blob_del, key=key)
        return ret

    def _getBlobKeys(self):
        rows = self.select(self._q_blob_get_keys)
        ret = [row[0] for row in rows]
        return ret
