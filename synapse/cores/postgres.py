import time
import hashlib

from . import sqlite as s_c_sqlite

import synapse.datamodel as s_datamodel


class Cortex(s_c_sqlite.Cortex):

    dbvar_open = '%('
    dbvar_close = ')s'
    dblim = None

    istable = '''
       SELECT 1
       FROM   information_schema.tables
       WHERE    table_name = %s
    '''

    init_strval_idx = 'CREATE INDEX %s_strval_idx ON %s (prop,md5(strval),stamp)'

    getjoin_by_in_int = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? and intval IN ?:valus:? LIMIT ?:limit:?)'
    getjoin_by_in_str = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? and md5(strval) IN ?:md5s:? and strval in ?:valus:? LIMIT ?:limit:?)'

    ################################################################################
    getrows_by_prop_str = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? LIMIT ?:limit:?'
    getrows_by_prop_str_wmin = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:stamp:?:stamp:? LIMIT ?:limit:?'
    getrows_by_prop_str_wmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp<?:stamp:? LIMIT ?:limit:?'
    getrows_by_prop_str_wminmax = 'SELECT id,prop,strval,intval,stamp FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:min:? AND stamp<?:max:? LIMIT ?:limit:?'

    ################################################################################
    getsize_by_prop_str = 'SELECT COUNT(*) FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? LIMIT ?:limit:?'
    getsize_by_prop_str_wmin = 'SELECT COUNT(*) FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:stamp:? LIMIT ?:limit:?'
    getsize_by_prop_str_wmax = 'SELECT COUNT(*) FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp<?:stamp:? LIMIT ?:limit:?'
    getsize_by_prop_str_wminmax = 'SELECT COUNT(*) FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:min:? AND stamp<?:max:? LIMIT ?:limit:?'

    ################################################################################
    delrows_by_prop_str = 'DELETE FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:?'
    delrows_by_prop_str_wmin = 'DELETE FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:stamp:?'
    delrows_by_prop_str_wmax = 'DELETE FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp<?:stamp:?'
    delrows_by_prop_str_wminmax = 'DELETE FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:min:? AND stamp<?:max:?'

    ################################################################################
    getjoin_by_prop_str = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? LIMIT ?:limit:?)'
    getjoin_by_prop_str_wmin = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:stamp:? LIMIT ?:limit:?)'
    getjoin_by_prop_str_wmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp<?:stamp:? LIMIT ?:limit:?)'
    getjoin_by_prop_str_wminmax = 'SELECT id,prop,strval,intval,stamp from %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:min:? AND stamp<?:max:? LIMIT ?:limit:?)'

    ################################################################################
    deljoin_by_prop_str = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:?)'
    deljoin_by_prop_str_wmin = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:stamp:? )'
    deljoin_by_prop_str_wmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp<?:stamp:? )'
    deljoin_by_prop_str_wminmax = 'DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE prop=?:prop:? AND md5(strval)=md5(?:valu:?) AND strval=?:valu:? AND stamp>=?:min:? AND stamp<?:max:?)'

    ################################################################################
    uprows_by_id_prop_str = 'UPDATE %s SET strval=?:valu:? WHERE id=?:iden:? and prop=?:prop:?'

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

    def _tufosByIn(self, prop, valus, limit=None):
        if len(valus) == 0:
            return []

        limit = self._getDbLimit(limit)

        args = { 'prop':prop, 'valus':tuple(valus), 'limit':limit }

        if type(valus[0]) == int:
            q = self._q_getjoin_by_in_int
        else:
            q = self._q_getjoin_by_in_str
            args['md5s'] = [hashlib.md5(s) for s in valus]

        rows = self.select(q,args)
        rows = self._foldTypeCols(rows)
        return self._rowsToTufos(rows)

    def _initCorQueries(self, table):
        s_c_sqlite.Cortex._initCorQueries(self, table)
        self._q_istable = self.istable

        self._q_getjoin_by_in_int = self._prepQuery(self.getjoin_by_in_int, table)
        self._q_getjoin_by_in_str = self._prepQuery(self.getjoin_by_in_str, table)


