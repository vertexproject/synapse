from __future__ import absolute_import,unicode_literals

import re
import sqlite3

import synapse.compat as s_compat
import synapse.cores.common as s_cores_common

from synapse.compat import queue
from synapse.common import now,genpath

stashre = re.compile('{{([A-Z]+)}}')

int_t = s_compat.typeof(0)
str_t = s_compat.typeof('visi')
none_t = s_compat.typeof(None)

class CoreXact(s_cores_common.CoreXact):

    def _coreXactInit(self):
        self.db = None
        self.cursor = None

    def _coreXactCommit(self):
        self.cursor.execute('COMMIT')

    def _coreXactBegin(self):
        self.cursor.execute('BEGIN TRANSACTION')

    def _coreXactAcquire(self):
        self.db = self.core.dbpool.get()
        self.cursor = self.db.cursor()

    def _coreXactRelease(self):
        self.cursor.close()
        self.core.dbpool.put( self.db )

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
            self.put( db )

    def put(self, db):
        '''
        Add/Return a db connection to the pool.
        '''
        self.dbque.put(db)

    def get(self):
        return self.dbque.get()

class Cortex(s_cores_common.Cortex):

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

    _t_init_iden_idx = 'CREATE INDEX {{TABLE}}_iden_idx ON {{TABLE}} (iden,prop)'
    _t_init_prop_idx = 'CREATE INDEX {{TABLE}}_prop_time_idx ON {{TABLE}} (prop,tstamp)'
    _t_init_strval_idx = 'CREATE INDEX {{TABLE}}_strval_idx ON {{TABLE}} (prop,strval,tstamp)'
    _t_init_intval_idx = 'CREATE INDEX {{TABLE}}_intval_idx ON {{TABLE}} (prop,intval,tstamp)'

    _t_addrows = 'INSERT INTO {{TABLE}} (iden,prop,strval,intval,tstamp) VALUES ({{IDEN}},{{PROP}},{{STRVAL}},{{INTVAL}},{{TSTAMP}})'
    _t_getrows_by_iden = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}}'
    _t_getrows_by_range = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{MINVALU}} AND intval < {{MAXVALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_le = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval <= {{VALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_ge = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} and intval >= {{VALU}} LIMIT {{LIMIT}}'
    _t_getrows_by_iden_prop = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}}'
    _t_getrows_by_iden_prop_intval = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND intval={{VALU}}'
    _t_getrows_by_iden_prop_strval = 'SELECT * FROM {{TABLE}} WHERE iden={{IDEN}} AND prop={{PROP}} AND strval={{VALU}}'

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

    def _initDbInfo(self):
        name = self._link[1].get('path')[1:]
        if not name:
            raise Exception('No Path Specified!')

        if name.find(':') == -1:
            name = genpath(name)

        return {'name':name}

    def _getCoreXact(self, size=None):
        return CoreXact(self, size=size)

    def _getDbLimit(self, limit):
        if limit != None:
            return limit
        return self.dblim

    def _rowsByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        q = self._q_getrows_by_range

        minvalu = int(valu[0])
        maxvalu = int(valu[1])

        rows = self.select(q, prop=prop, minvalu=minvalu, maxvalu=maxvalu, limit=limit)
        return self._foldTypeCols(rows)

    def _rowsByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_ge

        rows = self.select(q, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def _rowsByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_le
        rows = self.select(q, prop=prop, valu=valu, limit=limit)
        return self._foldTypeCols(rows)

    def _sizeByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_range
        return self.select(q,prop=prop,minvalu=valu[0],maxvalu=valu[1],limit=limit)[0][0]

    def _sizeByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_ge
        return self.select(q,prop=prop,valu=valu,limit=limit)[0][0]

    def _sizeByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_le
        args = [ prop, valu, limit ]
        return self.select(q,prop=prop,valu=valu,limit=limit)[0][0]

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

    def _initCortex(self):

        self.initSizeBy('ge',self._sizeByGe)
        self.initRowsBy('ge',self._rowsByGe)

        self.initSizeBy('le',self._sizeByLe)
        self.initRowsBy('le',self._rowsByLe)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

        self.initTufosBy('ge', self._tufosByGe)
        self.initTufosBy('le', self._tufosByLe)
        self.initTufosBy('range',self._tufosByRange)

        # borrow the helpers from common
        self.initTufosBy('gt', self._tufosByGt)
        self.initTufosBy('lt', self._tufosByLt)

        self.dbpool = self._link[1].get('dbpool')
        if self.dbpool == None:
            pool = int( self._link[1].get('pool',1) )
            self.dbpool = DbPool(pool, self._initDbConn)

        table = self._getTableName()

        self._initCorQueries()

        if not self._checkForTable( table ):
            self._initCorTable( table )

    def _prepQuery(self, query):
        # prep query strings by replacing all %s with table name
        # and all ? with db specific variable token
        table = self._getTableName()
        query = query.replace('{{TABLE}}',table)

        for name in stashre.findall(query):
            query = query.replace('{{%s}}' % name, self._addVarDecor(name.lower()))

        return query

    def _initCorQueries(self):
        self._q_istable = self._prepQuery(self._t_istable)
        self._q_inittable = self._prepQuery(self._t_inittable)
        self._q_init_iden_idx = self._prepQuery(self._t_init_iden_idx)
        self._q_init_prop_idx = self._prepQuery(self._t_init_prop_idx)
        self._q_init_strval_idx = self._prepQuery(self._t_init_strval_idx)
        self._q_init_intval_idx = self._prepQuery(self._t_init_intval_idx)

        self._q_addrows = self._prepQuery(self._t_addrows)
        self._q_getrows_by_iden = self._prepQuery(self._t_getrows_by_iden)
        self._q_getrows_by_range = self._prepQuery(self._t_getrows_by_range)
        self._q_getrows_by_ge = self._prepQuery(self._t_getrows_by_ge)
        self._q_getrows_by_le = self._prepQuery(self._t_getrows_by_le)
        self._q_getrows_by_iden_prop = self._prepQuery(self._t_getrows_by_iden_prop)
        self._q_getrows_by_iden_prop_intval = self._prepQuery(self._t_getrows_by_iden_prop_intval)
        self._q_getrows_by_iden_prop_strval = self._prepQuery(self._t_getrows_by_iden_prop_strval)

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
            'rowsbyprop':{
                (none_t,none_t,none_t):self._q_getrows_by_prop,
                (none_t,int_t,none_t):self._q_getrows_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getrows_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getrows_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getrows_by_prop_int,
                (int_t,int_t,none_t):self._q_getrows_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getrows_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getrows_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getrows_by_prop_str,
                (str_t,int_t,none_t):self._q_getrows_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getrows_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getrows_by_prop_str_wminmax,
            },
            'joinbyprop':{
                (none_t,none_t,none_t):self._q_getjoin_by_prop,
                (none_t,int_t,none_t):self._q_getjoin_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getjoin_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getjoin_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getjoin_by_prop_int,
                (int_t,int_t,none_t):self._q_getjoin_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getjoin_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getjoin_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getjoin_by_prop_str,
                (str_t,int_t,none_t):self._q_getjoin_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getjoin_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getjoin_by_prop_str_wminmax,
            },
            'sizebyprop':{
                (none_t,none_t,none_t):self._q_getsize_by_prop,
                (none_t,int_t,none_t):self._q_getsize_by_prop_wmin,
                (none_t,none_t,int_t):self._q_getsize_by_prop_wmax,
                (none_t,int_t,int_t):self._q_getsize_by_prop_wminmax,

                (int_t,none_t,none_t):self._q_getsize_by_prop_int,
                (int_t,int_t,none_t):self._q_getsize_by_prop_int_wmin,
                (int_t,none_t,int_t):self._q_getsize_by_prop_int_wmax,
                (int_t,int_t,int_t):self._q_getsize_by_prop_int_wminmax,

                (str_t,none_t,none_t):self._q_getsize_by_prop_str,
                (str_t,int_t,none_t):self._q_getsize_by_prop_str_wmin,
                (str_t,none_t,int_t):self._q_getsize_by_prop_str_wmax,
                (str_t,int_t,int_t):self._q_getsize_by_prop_str_wminmax,
            },
            'delrowsbyprop':{
                (none_t,none_t,none_t):self._prepQuery(self._t_delrows_by_prop),
                (none_t,int_t,none_t):self._prepQuery(self._t_delrows_by_prop_wmin),
                (none_t,none_t,int_t):self._prepQuery(self._t_delrows_by_prop_wmax),
                (none_t,int_t,int_t):self._prepQuery(self._t_delrows_by_prop_wminmax),

                (int_t,none_t,none_t):self._prepQuery(self._t_delrows_by_prop_int),
                (int_t,int_t,none_t):self._prepQuery(self._t_delrows_by_prop_int_wmin),
                (int_t,none_t,int_t):self._prepQuery(self._t_delrows_by_prop_int_wmax),
                (int_t,int_t,int_t):self._prepQuery(self._t_delrows_by_prop_int_wminmax),

                (str_t,none_t,none_t):self._prepQuery(self._t_delrows_by_prop_str),
                (str_t,int_t,none_t):self._prepQuery(self._t_delrows_by_prop_str_wmin),
                (str_t,none_t,int_t):self._prepQuery(self._t_delrows_by_prop_str_wmax),
                (str_t,int_t,int_t):self._prepQuery(self._t_delrows_by_prop_str_wminmax),
            },
            'deljoinbyprop':{
                (none_t,none_t,none_t):self._prepQuery(self._t_deljoin_by_prop),
                (none_t,int_t,none_t):self._prepQuery(self._t_deljoin_by_prop_wmin),
                (none_t,none_t,int_t):self._prepQuery(self._t_deljoin_by_prop_wmax),
                (none_t,int_t,int_t):self._prepQuery(self._t_deljoin_by_prop_wminmax),

                (int_t,none_t,none_t):self._prepQuery(self._t_deljoin_by_prop_int),
                (int_t,int_t,none_t):self._prepQuery(self._t_deljoin_by_prop_int_wmin),
                (int_t,none_t,int_t):self._prepQuery(self._t_deljoin_by_prop_int_wmax),
                (int_t,int_t,int_t):self._prepQuery(self._t_deljoin_by_prop_int_wminmax),

                (str_t,none_t,none_t):self._prepQuery(self._t_deljoin_by_prop_str),
                (str_t,int_t,none_t):self._prepQuery(self._t_deljoin_by_prop_str_wmin),
                (str_t,none_t,int_t):self._prepQuery(self._t_deljoin_by_prop_str_wmax),
                (str_t,int_t,int_t):self._prepQuery(self._t_deljoin_by_prop_str_wminmax),
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

        self._q_getjoin_by_range_str = self._prepQuery(self._t_getjoin_by_range_str)
        self._q_getjoin_by_range_int = self._prepQuery(self._t_getjoin_by_range_int)

        self._q_getjoin_by_ge_int = self._prepQuery(self._t_getjoin_by_ge_int)
        self._q_getjoin_by_le_int = self._prepQuery(self._t_getjoin_by_le_int)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable, name=name))

    def _initCorTable(self, name):
        with self.getCoreXact() as xact:
            xact.cursor.execute(self._q_inittable)
            xact.cursor.execute(self._q_init_iden_idx)
            xact.cursor.execute(self._q_init_prop_idx)
            xact.cursor.execute(self._q_init_strval_idx)
            xact.cursor.execute(self._q_init_intval_idx)

    def _addRows(self, rows):
        args = []
        for i,p,v,t in rows:
            if s_compat.isint(v):
                args.append( {'iden':i, 'prop':p, 'intval':v, 'strval':None, 'tstamp':t} )
            else:
                args.append( {'iden':i, 'prop':p, 'intval':None, 'strval':v, 'tstamp':t} )

        with self.getCoreXact() as xact:
            xact.cursor.executemany( self._q_addrows, args )

    def update(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q,args)
            return xact.cursor.rowcount

    def select(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q,args)
            return xact.cursor.fetchall()

    def delete(self, q, **args):
        with self.getCoreXact() as xact:
            xact.cursor.execute(q,args)

    def _foldTypeCols(self, rows):
        ret = []
        for iden,prop,intval,strval,tstamp in rows:

            if intval != None:
                ret.append( (iden,prop,intval,tstamp) )
            else:
                ret.append( (iden,prop,strval,tstamp) )

        return ret

    def _getRowsById(self, iden):
        rows = self.select(self._q_getrows_by_iden,iden=iden)
        return self._foldTypeCols(rows)

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('sizebyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return rows[0][0]

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        rows = self._runPropQuery('rowsbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _tufosByRange(self, prop, valu, limit=None):

        if len(valu) != 2:
            return []

        minvalu,maxvalu = valu
        if not s_compat.isint(minvalu) or not s_compat.isint(maxvalu):
            raise Exception('by "range" requires (int,int)')

        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_range_int, prop=prop, minvalu=minvalu, maxvalu=maxvalu, limit=limit)
        rows = self._foldTypeCols(rows)
        return self._rowsToTufos(rows)

    def _tufosByLe(self, prop, valu, limit=None):
        valu,_ = self.getPropNorm(prop,valu)
        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_le_int, prop=prop, valu=valu, limit=limit)
        rows = self._foldTypeCols(rows)

        return self._rowsToTufos(rows)

    def _tufosByGe(self, prop, valu, limit=None):
        valu,_ = self.getPropNorm(prop,valu)
        limit = self._getDbLimit(limit)

        rows = self.select(self._q_getjoin_by_ge_int, prop=prop, valu=valu, limit=limit)
        rows = self._foldTypeCols(rows)

        return self._rowsToTufos(rows)

    def _runPropQuery(self, name, prop, valu=None, limit=None, mintime=None, maxtime=None, meth=None, nolim=False):
        limit = self._getDbLimit(limit)

        qkey = (s_compat.typeof(valu),s_compat.typeof(mintime),s_compat.typeof(maxtime))

        qstr = self.qbuild[name][qkey]
        if meth == None:
            meth = self.select

        rows = meth(qstr, prop=prop, valu=valu, limit=limit, mintime=mintime, maxtime=maxtime)

        return rows

    def _delRowsByIdProp(self, iden, prop, valu=None):
        if valu == None:
            return self.delete( self._q_delrows_by_iden_prop, iden=iden, prop=prop )

        if s_compat.isint(valu):
            return self.delete( self._q_delrows_by_iden_prop_intval, iden=iden, prop=prop, valu=valu )
        else:
            return self.delete( self._q_delrows_by_iden_prop_strval, iden=iden, prop=prop, valu=valu )

    def _getRowsByIdProp(self, iden, prop, valu=None):
        if valu == None:
            rows = self.select( self._q_getrows_by_iden_prop, iden=iden, prop=prop)
            return self._foldTypeCols(rows)

        if s_compat.isint(valu):
            rows = self.select( self._q_getrows_by_iden_prop_intval, iden=iden, prop=prop, valu=valu)
            return self._foldTypeCols(rows)

        else:
            rows = self.select( self._q_getrows_by_iden_prop_strval, iden=iden, prop=prop, valu=valu)
            return self._foldTypeCols(rows)

    def _setRowsByIdProp(self, iden, prop, valu):
        if s_compat.isint(valu):
            count = self.update( self._q_uprows_by_iden_prop_int, iden=iden, prop=prop, valu=valu )
        else:
            count = self.update( self._q_uprows_by_iden_prop_str, iden=iden, prop=prop, valu=valu )

        if count == 0:
            rows = [ (iden,prop,valu,now()), ]
            self._addRows(rows)

    def _delRowsById(self, iden):
        self.delete(self._q_delrows_by_iden, iden=iden)

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('deljoinbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,meth=self.delete, nolim=True)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        rows = self._runPropQuery('joinbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime)
        return self._foldTypeCols(rows)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._runPropQuery('delrowsbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,meth=self.delete, nolim=True)
