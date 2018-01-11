import time
import hashlib

import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.cores.common as s_cores_common
import synapse.cores.sqlite as s_cores_sqlite

def md5(x):
    return hashlib.md5(x.encode('utf8')).hexdigest()

def initPsqlCortex(link, conf=None, storconf=None):
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

    store = PsqlStorage(link, **storconf)
    return s_cores_common.Cortex(link, store, **conf)

class PsqlStorage(s_cores_sqlite.SqliteStorage):

    dblim = None

    # postgres uses BYTEA instead of BLOB
    _t_init_blobtable = '''
    CREATE TABLE {{BLOB_TABLE}} (
         k VARCHAR,
         v BYTEA
    );
    '''
    # postgres upsert!
    _t_blob_set = 'INSERT INTO {{BLOB_TABLE}} (k, v) VALUES ({{KEY}}, {{VALU}}) ON CONFLICT (k) DO UPDATE SET ' \
                   'v={{VALU}}'

    # postgres over-rides for md5() based indexing
    _t_init_strval_idx = 'CREATE INDEX {{TABLE}}_strval_idx ON {{TABLE}} (prop,MD5(strval),tstamp)'

    _t_getrows_by_prop_str = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wmin = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp >= {{MINTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getrows_by_prop_str_wminmax = 'SELECT * FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp >= {{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wmin = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_getsize_by_prop_str_wminmax = 'SELECT COUNT(*) FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}}'
    _t_delrows_by_prop_str = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}})'
    _t_delrows_by_prop_str_wmin = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}}'
    _t_delrows_by_prop_str_wmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp<{{MAXTIME}}'
    _t_delrows_by_prop_str_wminmax = 'DELETE FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}}'
    _t_getjoin_by_prop_str = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wmin = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'
    _t_getjoin_by_prop_str_wminmax = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} LIMIT {{LIMIT}})'

    _t_deljoin_by_prop_str = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}))'
    _t_deljoin_by_prop_str_wmin = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} )'
    _t_deljoin_by_prop_str_wmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp<{{MAXTIME}} )'
    _t_deljoin_by_prop_str_wminmax = 'DELETE FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} AND MD5(strval)=MD5({{VALU}}) AND tstamp>={{MINTIME}} AND tstamp<{{MAXTIME}} )'

    _t_istable = '''
       SELECT 1
       FROM   information_schema.tables
       WHERE    table_name = {{NAME}}
    '''

    _t_getjoin_by_in_int = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and intval IN {{VALU}} LIMIT {{LIMIT}})'
    _t_getjoin_by_in_str = 'SELECT * FROM {{TABLE}} WHERE iden IN (SELECT iden FROM {{TABLE}} WHERE prop={{PROP}} and MD5(strval) IN {{VALU}} LIMIT {{LIMIT}})'

    _t_getrows_by_idens = 'SELECT * FROM {{TABLE}} WHERE iden IN {{VALU}}'

    _t_uprows_by_prop_val_str = 'UPDATE {{TABLE}} SET strval={{NEWVALU}} WHERE prop={{PROP}} and MD5(strval)=MD5({{OLDVALU}})'

    def _initDbConn(self):
        import psycopg2
        self._psycopg2 = psycopg2

        retry = self._link[1].get('retry', 0)

        dbinfo = self._initDbInfo()

        db = None
        tries = 0
        while db is None:
            try:
                db = psycopg2.connect(**dbinfo)
            except Exception as e:  # pragma: no cover
                tries += 1
                if tries > retry:
                    raise

                time.sleep(1)

        seqscan = self._link[1].get('pg:seqscan', 0)
        seqscan, _ = s_datamodel.getTypeNorm('bool', seqscan)

        c = db.cursor()
        c.execute('SET enable_seqscan=%s', (seqscan,))
        c.close()

        return db

    def _getTableName(self):
        path = self._link[1].get('path')
        if not path:
            return 'syncortex'

        parts = [p for p in path.split('/') if p]
        if len(parts) <= 1:
            return 'syncortex'

        return parts[1]

    def _initDbInfo(self):

        dbinfo = {}

        path = self._link[1].get('path')
        if path:
            parts = [p for p in path.split('/') if p]
            if parts:
                dbinfo['database'] = parts[0]

        host = self._link[1].get('host')
        if host is not None:
            dbinfo['host'] = host

        port = self._link[1].get('port')
        if port is not None:
            dbinfo['port'] = port

        user = self._link[1].get('user')
        if user is not None:
            dbinfo['user'] = user

        passwd = self._link[1].get('passwd')
        if passwd is not None:
            dbinfo['password'] = passwd

        return dbinfo

    def _joinsByIn(self, prop, valus, limit=None):
        if len(valus) == 0:
            return []

        limit = self._getDbLimit(limit)

        if isinstance(valus[0], int):
            q = self._q_getjoin_by_in_int
        else:
            q = self._q_getjoin_by_in_str
            valus = [md5(v) for v in valus]

        rows = self.select(q, prop=prop, valu=tuple(valus), limit=limit)
        return self._foldTypeCols(rows)

    def getRowsByIdens(self, idens):
        if len(idens) == 0:
            return []
        rows = self.select(self._q_getrows_by_idens, valu=tuple(idens))
        return self._foldTypeCols(rows)

    def _initCorQueries(self):
        s_cores_sqlite.SqliteStorage._initCorQueries(self)

        self._q_getrows_by_idens = self._prepQuery(self._t_getrows_by_idens)
        self._q_getjoin_by_in_int = self._prepQuery(self._t_getjoin_by_in_int)
        self._q_getjoin_by_in_str = self._prepQuery(self._t_getjoin_by_in_str)

    def _addVarDecor(self, name):
        return '%%(%s)s' % (name,)

    def getStoreType(self):
        return 'postgres'

    def _prepBlobValu(self, valu):
        return memoryview(valu)
