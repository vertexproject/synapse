from __future__ import absolute_import,unicode_literals

import time

import synapse.compat as s_compat
import synapse.cores.common as common

from synapse.compat import queue
import synapse.datamodel as s_datamodel
from synapse.exc import HitMaxTime

int_t = s_compat.typeof(0)
str_t = s_compat.typeof('visi')
none_t = s_compat.typeof(None)

istable = '''
   SELECT 1
   FROM   information_schema.tables
   WHERE    table_name = %s
'''

inittable = '''
CREATE TABLE %s (
    id VARCHAR,
    prop VARCHAR,
    strval TEXT,
    intval BIGINT,
    stamp BIGINT
);
'''

init_id_idx = 'CREATE INDEX %s_id_idx ON %s (id,prop)'
init_prop_idx = 'CREATE INDEX %s_prop_time_idx ON %s (prop,stamp)'
init_strval_idx = 'CREATE INDEX %s_strval_idx ON %s (prop,left(strval,32),stamp)'
init_intval_idx = 'CREATE INDEX %s_intval_idx ON %s (prop,intval,stamp)'

addrows = 'INSERT INTO %s (id,prop,strval,intval,stamp) VALUES (%(iden)s,%(prop)s,%(strval)s,%(intval)s,%(stamp)s)'
getrows_by_id = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id=%(iden)s'
getrows_by_range = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s and intval>=%(min)s AND intval<%(max)s LIMIT %(limit)s'
getrows_by_le = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s and intval<=%(valu)s LIMIT %(limit)s'
getrows_by_ge = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s and intval>=%(valu)s LIMIT %(limit)s'
getrows_by_id_prop = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id=%(iden)s AND prop=%(prop)s'

################################################################################
getrows_by_prop = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s LIMIT %(limit)s'
getrows_by_prop_int = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND intval=%(valu)s LIMIT %(limit)s'

getrows_by_prop_wmin = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND stamp>=%(stamp)s LIMIT %(limit)s'
getrows_by_prop_int_wmin = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(stamp)s LIMIT %(limit)s'

getrows_by_prop_wmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND stamp<%(stamp)s LIMIT %(limit)s'
getrows_by_prop_int_wmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s'

getrows_by_prop_wminmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'
getrows_by_prop_int_wminmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'
################################################################################
getsize_by_prop = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s LIMIT %(limit)s'
getsize_by_prop_int = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND intval=%(valu)s LIMIT %(limit)s'

getsize_by_prop_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND stamp>=%(stamp)s LIMIT %(limit)s'
getsize_by_prop_int_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(stamp)s LIMIT %(limit)s'

getsize_by_prop_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND stamp<%(stamp)s LIMIT %(limit)s'
getsize_by_prop_int_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s'

getsize_by_prop_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'
getsize_by_prop_int_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'
################################################################################

getsize_by_range = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s and intval>=%(min)s AND intval<%(max)s LIMIT %(limit)s'
getsize_by_le = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s and intval<=%(valu)s LIMIT %(limit)s'
getsize_by_ge = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s and intval>=%(valu)s LIMIT %(limit)s'

delrows_by_id = 'DELETE FROM %s WHERE id=%(iden)s'
delrows_by_id_prop = 'DELETE FROM %s WHERE id=%(iden)s AND prop=%(prop)s'

################################################################################
delrows_by_prop = 'DELETE FROM %s WHERE prop=%(prop)s'
delrows_by_prop_int = 'DELETE FROM %s WHERE prop=%(prop)s AND intval=%(valu)s'

delrows_by_prop_wmin = 'DELETE FROM %s WHERE prop=%(prop)s AND stamp>=%(stamp)s'
delrows_by_prop_int_wmin = 'DELETE FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(stamp)s'

delrows_by_prop_wmax = 'DELETE FROM %s WHERE prop=%(prop)s AND stamp<%(stamp)s'
delrows_by_prop_int_wmax = 'DELETE FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp<%(stamp)s'

delrows_by_prop_wminmax = 'DELETE FROM %s WHERE prop=%(prop)s AND stamp>=%(min)s AND stamp<%(max)s'
delrows_by_prop_int_wminmax = 'DELETE FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s'

################################################################################
getjoin_by_prop = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s LIMIT %(limit)s)'
getjoin_by_prop_int = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s LIMIT %(limit)s)'

getjoin_by_prop_wmin = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp>=%(stamp)s LIMIT %(limit)s)'
getjoin_by_prop_int_wmin = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(stamp)s LIMIT %(limit)s)'

getjoin_by_prop_wmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp<%(stamp)s LIMIT %(limit)s)'
getjoin_by_prop_int_wmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s)'

getjoin_by_prop_wminmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s)'
getjoin_by_prop_int_wminmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s)'

getjoin_by_range_int = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s and %(min)s <= intval AND intval<%(max)s LIMIT %(limit)s)'
getjoin_by_range_str = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s and left(%(min)s,32) <= left(strval,32) AND left(strval,32)<=left(%(max)s,32) and %(min)s <= strval AND strval<%(max)s LIMIT %(limit)s)'

################################################################################
deljoin_by_prop = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s)'
deljoin_by_prop_int = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s)'

deljoin_by_prop_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp>=%(stamp)s )'
deljoin_by_prop_int_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(stamp)s )'

deljoin_by_prop_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp<%(stamp)s )'
deljoin_by_prop_int_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp<%(stamp)s )'

deljoin_by_prop_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND stamp>=%(min)s AND stamp<%(max)s)'
deljoin_by_prop_int_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND intval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s)'
################################################################################

uprows_by_id_prop_int = 'UPDATE %s SET intval=%(valu)s WHERE id=%(iden)s and prop=%(prop)s'

################################################################################
getjoin_by_in_int = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s and intval IN %(valus)s LIMIT %(limit)s)'
getjoin_by_in_str = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s and left(strval,32) in %(short_valus)s and strval in %(valus)s LIMIT %(limit)s)'

################################################################################
getrows_by_prop_str = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s LIMIT %(limit)s'
getrows_by_prop_str_wmin = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(stamp:%(stamp)s LIMIT %(limit)s'
getrows_by_prop_str_wmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s'
getrows_by_prop_str_wminmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'

################################################################################
getsize_by_prop_str = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s LIMIT %(limit)s'
getsize_by_prop_str_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(stamp)s LIMIT %(limit)s'
getsize_by_prop_str_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s'
getsize_by_prop_str_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s'

################################################################################
delrows_by_prop_str = 'DELETE FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s'
delrows_by_prop_str_wmin = 'DELETE FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(stamp)s'
delrows_by_prop_str_wmax = 'DELETE FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp<%(stamp)s'
delrows_by_prop_str_wminmax = 'DELETE FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s'

################################################################################
getjoin_by_prop_str = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s LIMIT %(limit)s)'
getjoin_by_prop_str_wmin = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(stamp)s LIMIT %(limit)s)'
getjoin_by_prop_str_wmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp<%(stamp)s LIMIT %(limit)s)'
getjoin_by_prop_str_wminmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s LIMIT %(limit)s)'

################################################################################
deljoin_by_prop_str = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s)'
deljoin_by_prop_str_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(stamp)s )'
deljoin_by_prop_str_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp<%(stamp)s )'
deljoin_by_prop_str_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=%(prop)s AND left(strval,32)=left(%(valu)s,32) AND strval=%(valu)s AND stamp>=%(min)s AND stamp<%(max)s)'

################################################################################
uprows_by_id_prop_str = 'UPDATE %s SET strval=%(valu)s WHERE id=%(iden)s and prop=%(prop)s'

class WithCursor:

    def __init__(self, pool, db, cursor):
        self.db = db
        self.pool = pool
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc, cls, tb):
        self.cursor.close()

        self.db.commit()
        self.pool.putdb( self.db )

class DbPool:
    '''
    The DbPool allows generic db connection pooling using
    a factory/ctor method and a python queue.
    Example:
        def connectdb():
            # do stuff
            return db
        pool = DbPool(3, connectdb)
        with pool.cursor() as c:
    '''

    def __init__(self, size, ctor):
        # TODO: high/low water marks
        self.size = size
        self.ctor = ctor
        self.dbque = queue.Queue()

        for i in range(size):
            db = ctor()
            self.putdb( db )

    def cursor(self):
        db = self.dbque.get()
        cur = db.cursor()
        return WithCursor(self, db, cur)

    def putdb(self, db):
        '''
        Add/Return a db connection to the pool.
        '''
        self.dbque.put(db)

class Cortex(common.Cortex):

    dblim = None
    max_idx_len = 2712

    def cursor(self):
        return self.dbpool.cursor()

    def _getDbLimit(self, limit):
        if limit != None:
            return limit
        return self.dblim

    def _rowsByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)

        q = self._q_getrows_by_range
        args = { 'prop':prop, 'min':valu[0], 'max':valu[1], 'limit':limit }

        rows = self.select(q,args)
        return self._foldTypeCols(rows)

    def _rowsByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_ge

        rows = self.select(q, { 'prop':prop, 'valu':valu, 'limit':limit })
        return self._foldTypeCols(rows)

    def _rowsByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getrows_by_le
        rows = self.select(q, { 'prop':prop, 'valu':valu, 'limit':limit })
        return self._foldTypeCols(rows)

    def _sizeByRange(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_range
        args = { 'prop':prop, 'min':valu[0], 'max':valu[1], 'limit':limit }
        return self.select(q,args)[0][0]

    def _sizeByGe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_ge
        args = { 'prop':prop, 'valu':valu, 'limit':limit }
        return self.select(q,args)[0][0]

    def _sizeByLe(self, prop, valu, limit=None):
        limit = self._getDbLimit(limit)
        q = self._q_getsize_by_le
        args = { 'prop':prop, 'valu':valu, 'limit':limit }
        return self.select(q,args)[0][0]

    def _initDbConn(self):
        import psycopg2

        retry = self._link[1].get('retry',0)

        dbinfo = self._initDbInfo()

        db = None
        tries = 0
        while db == None:
            try:
                db = psycopg2.connect(**dbinfo)
            except Exception as e:
                tries += 1
                if tries > retry:
                    raise

                time.sleep(1)

        seqscan = self._link[1].get('pg:seqscan',0)
        seqscan = s_datamodel.getTypeFrob('bool',seqscan)

        c = db.cursor()
        c.execute('SET enable_seqscan=%s', (seqscan,))
        c.close()

        return db

    def _getTableName(self):
        path = self._link[1].get('path')
        if not path:
            return 'syncortex'

        parts = [ p for p in path.split('/') if p ]
        if len(parts) <= 1:
            return 'syncortex'

        return parts[1]

    def _initDbInfo(self):

        dbinfo = {}

        path = self._link[1].get('path')
        if path:
            parts = [ p for p in path.split('/') if p ]
            if parts:
                dbinfo['database'] = parts[0]

        host = self._link[1].get('host')
        if host != None:
            dbinfo['host'] = host

        port = self._link[1].get('port')
        if port != None:
            dbinfo['port'] = port

        user = self._link[1].get('user')
        if user != None:
            dbinfo['user'] = user

        passwd = self._link[1].get('passwd')
        if passwd != None:
            dbinfo['password'] = passwd

        return dbinfo

    def _initCortex(self):

        self.initSizeBy('ge',self._sizeByGe)
        self.initRowsBy('ge',self._rowsByGe)

        self.initSizeBy('le',self._sizeByLe)
        self.initRowsBy('le',self._rowsByLe)

        self.initTufosBy('in',self._tufosByIn)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)
        self.initTufosBy('range',self._tufosByRange)

        self.dbpool = self._link[1].get('dbpool')
        if self.dbpool == None:
            pool = int( self._link[1].get('pool',1) )
            self.dbpool = DbPool(pool, self._initDbConn)

        table = self._getTableName()

        self._initCorQueries(table)
        if not self._checkForTable( table ):
            self._initCorTable( table )

    def _prepQuery(self, query, table):
        # prep query strings by replacing all %s with table name
        query = query.replace('%s', table)
        return query

    def _initCorQueries(self, table):
        self._q_istable = istable
        self._q_inittable = self._prepQuery(inittable, table)
        self._q_init_id_idx = self._prepQuery(init_id_idx, table)
        self._q_init_prop_idx = self._prepQuery(init_prop_idx, table)
        self._q_init_strval_idx = self._prepQuery(init_strval_idx, table)
        self._q_init_intval_idx = self._prepQuery(init_intval_idx, table)

        self._q_addrows = self._prepQuery(addrows, table)
        self._q_getrows_by_id = self._prepQuery(getrows_by_id, table)
        self._q_getrows_by_range = self._prepQuery(getrows_by_range, table)
        self._q_getrows_by_ge = self._prepQuery(getrows_by_ge, table)
        self._q_getrows_by_le = self._prepQuery(getrows_by_le, table)
        self._q_getrows_by_id_prop = self._prepQuery(getrows_by_id_prop, table)

        ###################################################################################
        self._q_getrows_by_prop = self._prepQuery(getrows_by_prop, table)
        self._q_getrows_by_prop_wmin = self._prepQuery(getrows_by_prop_wmin, table)
        self._q_getrows_by_prop_wmax = self._prepQuery(getrows_by_prop_wmax, table)
        self._q_getrows_by_prop_wminmax = self._prepQuery(getrows_by_prop_wminmax, table)
        ###################################################################################
        self._q_getrows_by_prop_int = self._prepQuery(getrows_by_prop_int, table)
        self._q_getrows_by_prop_int_wmin = self._prepQuery(getrows_by_prop_int_wmin, table)
        self._q_getrows_by_prop_int_wmax = self._prepQuery(getrows_by_prop_int_wmax, table)
        self._q_getrows_by_prop_int_wminmax = self._prepQuery(getrows_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getrows_by_prop_str = self._prepQuery(getrows_by_prop_str, table)
        self._q_getrows_by_prop_str_wmin = self._prepQuery(getrows_by_prop_str_wmin, table)
        self._q_getrows_by_prop_str_wmax = self._prepQuery(getrows_by_prop_str_wmax, table)
        self._q_getrows_by_prop_str_wminmax = self._prepQuery(getrows_by_prop_str_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop = self._prepQuery(getjoin_by_prop, table)
        self._q_getjoin_by_prop_wmin = self._prepQuery(getjoin_by_prop_wmin, table)
        self._q_getjoin_by_prop_wmax = self._prepQuery(getjoin_by_prop_wmax, table)
        self._q_getjoin_by_prop_wminmax = self._prepQuery(getjoin_by_prop_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop_int = self._prepQuery(getjoin_by_prop_int, table)
        self._q_getjoin_by_prop_int_wmin = self._prepQuery(getjoin_by_prop_int_wmin, table)
        self._q_getjoin_by_prop_int_wmax = self._prepQuery(getjoin_by_prop_int_wmax, table)
        self._q_getjoin_by_prop_int_wminmax = self._prepQuery(getjoin_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getjoin_by_prop_str = self._prepQuery(getjoin_by_prop_str, table)
        self._q_getjoin_by_prop_str_wmin = self._prepQuery(getjoin_by_prop_str_wmin, table)
        self._q_getjoin_by_prop_str_wmax = self._prepQuery(getjoin_by_prop_str_wmax, table)
        self._q_getjoin_by_prop_str_wminmax = self._prepQuery(getjoin_by_prop_str_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop, table)
        self._q_getsize_by_prop_wmin = self._prepQuery(getsize_by_prop_wmin, table)
        self._q_getsize_by_prop_wmax = self._prepQuery(getsize_by_prop_wmax, table)
        self._q_getsize_by_prop_wminmax = self._prepQuery(getsize_by_prop_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop_int = self._prepQuery(getsize_by_prop_int, table)
        self._q_getsize_by_prop_int_wmin = self._prepQuery(getsize_by_prop_int_wmin, table)
        self._q_getsize_by_prop_int_wmax = self._prepQuery(getsize_by_prop_int_wmax, table)
        self._q_getsize_by_prop_int_wminmax = self._prepQuery(getsize_by_prop_int_wminmax, table)
        ###################################################################################
        self._q_getsize_by_prop_str = self._prepQuery(getsize_by_prop_str, table)
        self._q_getsize_by_prop_str_wmin = self._prepQuery(getsize_by_prop_str_wmin, table)
        self._q_getsize_by_prop_str_wmax = self._prepQuery(getsize_by_prop_str_wmax, table)
        self._q_getsize_by_prop_str_wminmax = self._prepQuery(getsize_by_prop_str_wminmax, table)
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
                (none_t,none_t,none_t):self._prepQuery(delrows_by_prop, table),
                (none_t,int_t,none_t):self._prepQuery(delrows_by_prop_wmin, table),
                (none_t,none_t,int_t):self._prepQuery(delrows_by_prop_wmax, table),
                (none_t,int_t,int_t):self._prepQuery(delrows_by_prop_wminmax, table),

                (int_t,none_t,none_t):self._prepQuery(delrows_by_prop_int, table),
                (int_t,int_t,none_t):self._prepQuery(delrows_by_prop_int_wmin, table),
                (int_t,none_t,int_t):self._prepQuery(delrows_by_prop_int_wmax, table),
                (int_t,int_t,int_t):self._prepQuery(delrows_by_prop_int_wminmax, table),

                (str_t,none_t,none_t):self._prepQuery(delrows_by_prop_str, table),
                (str_t,int_t,none_t):self._prepQuery(delrows_by_prop_str_wmin, table),
                (str_t,none_t,int_t):self._prepQuery(delrows_by_prop_str_wmax, table),
                (str_t,int_t,int_t):self._prepQuery(delrows_by_prop_str_wminmax, table),
            },
            'deljoinbyprop':{
                (none_t,none_t,none_t):self._prepQuery(deljoin_by_prop, table),
                (none_t,int_t,none_t):self._prepQuery(deljoin_by_prop_wmin, table),
                (none_t,none_t,int_t):self._prepQuery(deljoin_by_prop_wmax, table),
                (none_t,int_t,int_t):self._prepQuery(deljoin_by_prop_wminmax, table),

                (int_t,none_t,none_t):self._prepQuery(deljoin_by_prop_int, table),
                (int_t,int_t,none_t):self._prepQuery(deljoin_by_prop_int_wmin, table),
                (int_t,none_t,int_t):self._prepQuery(deljoin_by_prop_int_wmax, table),
                (int_t,int_t,int_t):self._prepQuery(deljoin_by_prop_int_wminmax, table),

                (str_t,none_t,none_t):self._prepQuery(deljoin_by_prop_str, table),
                (str_t,int_t,none_t):self._prepQuery(deljoin_by_prop_str_wmin, table),
                (str_t,none_t,int_t):self._prepQuery(deljoin_by_prop_str_wmax, table),
                (str_t,int_t,int_t):self._prepQuery(deljoin_by_prop_str_wminmax, table),
            }
        }

        self._q_getsize_by_prop = self._prepQuery(getsize_by_prop, table)

        self._q_getsize_by_ge = self._prepQuery(getsize_by_ge, table)
        self._q_getsize_by_le = self._prepQuery(getsize_by_le, table)
        self._q_getsize_by_range = self._prepQuery(getsize_by_range, table)

        self._q_delrows_by_id = self._prepQuery(delrows_by_id, table)
        self._q_delrows_by_id_prop = self._prepQuery(delrows_by_id_prop, table)

        self._q_uprows_by_id_prop_str = self._prepQuery(uprows_by_id_prop_str, table)
        self._q_uprows_by_id_prop_int = self._prepQuery(uprows_by_id_prop_int, table)

        self._q_getjoin_by_range_str = self._prepQuery(getjoin_by_range_str, table)
        self._q_getjoin_by_range_int = self._prepQuery(getjoin_by_range_int, table)

        self._q_getjoin_by_in_int = self._prepQuery(getjoin_by_in_int, table)
        self._q_getjoin_by_in_str = self._prepQuery(getjoin_by_in_str, table)

    def _checkForTable(self, name):
        return len(self.select(self._q_istable,(name,)))

    def _initCorTable(self, name):
        with self.cursor() as c:
            c.execute(self._q_inittable)
            c.execute(self._q_init_id_idx)
            c.execute(self._q_init_prop_idx)
            c.execute(self._q_init_strval_idx)
            c.execute(self._q_init_intval_idx)

    def _addRows(self, rows):
        rows = [ {'iden':i,'prop':p,'strval':None,'intval':v,'stamp':t} if s_compat.isint(v) else {'iden':i,'prop':p,'strval':v,'intval':None,'stamp':t} for i,p,v,t in rows ]
        with self.cursor() as c:
            c.executemany( self._q_addrows, rows )

    def update(self, q, r, ret=False, timeout=None):
        #print('UPDATE: %r %r' % (q,r))
        with self.cursor() as cur:
            self._execute(cur,q,r,timeout=timeout)
            if ret:
                return cur.fetchall()

            return cur.rowcount

    def select(self, q, r, timeout=None):
        #print('SELECT: %r %r' % (q,r))
        with self.cursor() as cur:
            self._execute(cur,q,r,timeout=timeout)
            return cur.fetchall()

    def delete(self, q, r, timeout=None):
        #print('DELETE: %s %r' % (q,r))
        with self.cursor() as cur:
            self._execute(cur,q,r,timeout=timeout)

    def _execute(self, cur, q, r, timeout=None):
        from psycopg2.extensions import QueryCanceledError

        if timeout:
            cur.execute('set local statement_timeout = %s', [int(timeout * 1000)])

        try:
            cur.execute(q, r)
        except QueryCanceledError:
            cur.connection.rollback()
            raise HitMaxTime()

    def _foldTypeCols(self, rows):
        ret = []
        for ident,prop,intval,strval,stamp in rows:

            if intval != None:
                ret.append( (ident,prop,intval,stamp) )
            else:
                ret.append( (ident,prop,strval,stamp) )

        return ret

    def _getRowsById(self, ident):
        rows = self.select(self._q_getrows_by_id,{'iden':ident})
        return self._foldTypeCols(rows)

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None, timeout=None):
        rows = self._runPropQuery('sizebyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime,timeout=timeout)
        return rows[0][0]

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None, timeout=None):
        rows = self._runPropQuery('rowsbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime,timeout=timeout)
        return self._foldTypeCols(rows)

    def _tufosByIn(self, prop, valus, limit=None):
        if len(valus) == 0:
            return []

        limit = self._getDbLimit(limit)

        args = { 'prop':prop, 'valus':tuple(valus), 'limit':limit }

        if type(valus[0]) == int:
            q = self._q_getjoin_by_in_int
        else:
            q = self._q_getjoin_by_in_str
            args['short_valus'] = tuple([k for k in {s[0:32]:1 for s in valus}])

        rows = self.select(q,args)
        rows = self._foldTypeCols(rows)
        return self._rowsToTufos(rows)


    def _tufosByRange(self, prop, valus, limit=None):
        if len(valus) != 2:
            return []  # TODO: Raise exception?

        limit = self._getDbLimit(limit)

        if s_compat.isint(valus[0]):
            q = self._q_getjoin_by_range_int
        else:
            q = self._q_getjoin_by_range_str

        args = { 'prop':prop, 'min':valus[0], 'max':valus[1], 'limit':limit }

        rows = self.select(q,args)
        rows = self._foldTypeCols(rows)
        return self._rowsToTufos(rows)

    def _runPropQuery(self, name, prop, valu=None, limit=None, mintime=None, maxtime=None, timeout=None, meth=None, nolim=False):
        limit = self._getDbLimit(limit)

        qkey = (s_compat.typeof(valu),s_compat.typeof(mintime),s_compat.typeof(maxtime))

        qargs = { 'prop':prop }
        qargs.update( { k:v for k,v in {'valu':valu,'min':mintime,'max':maxtime}.items() if v is not None } )

        if not nolim:
            qargs['limit'] = limit

        qstr = self.qbuild[name][qkey]
        #print('QNAM: %r' % (name,))
        #print('QKEY: %r' % (qkey,))
        #print('QSTR: %r' % (qstr,))
        #print('QARG: %r' % (qargs,))
        if meth == None:
            meth = self.select

        rows = meth(qstr,qargs,timeout=timeout)

        #print('QROW: %r' % (rows,))
        return rows

    def _delRowsByIdProp(self, ident, prop):
        self.delete( self._q_delrows_by_id_prop, {'iden':ident,'prop':prop})

    def _getRowsByIdProp(self, iden, prop):
        rows = self.select( self._q_getrows_by_id_prop, {'iden':iden,'prop':prop})
        return self._foldTypeCols(rows)

    def _setRowsByIdProp(self, ident, prop, valu):
        if s_compat.isint(valu):
            count = self.update( self._q_uprows_by_id_prop_int, {'valu':valu,'iden':ident,'prop':prop} )
        else:
            count = self.update( self._q_uprows_by_id_prop_str, {'valu':valu,'iden':ident,'prop':prop} )

        if count == 0:
            rows = [ (ident,prop,valu,int(time.time())) ]
            self._addRows(rows)

    def _delRowsById(self, ident):
        self.delete(self._q_delrows_by_id,{'iden':ident})

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, timeout=None):
        self._runPropQuery('deljoinbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,timeout=timeout,meth=self.delete, nolim=True)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, timeout=None, limit=None):
        rows = self._runPropQuery('joinbyprop',prop,valu=valu,limit=limit,mintime=mintime,maxtime=maxtime,timeout=timeout)
        return self._foldTypeCols(rows)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, timeout=None):
        self._runPropQuery('delrowsbyprop',prop,valu=valu,mintime=mintime,maxtime=maxtime,timeout=timeout,meth=self.delete, nolim=True)
