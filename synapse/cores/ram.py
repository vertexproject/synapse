import logging
import collections

import synapse.common as s_common

from synapse.compat import isint, intern

import synapse.cores.common as s_cores_common

class CoreXact(s_cores_common.CoreXact):

    # Ram Cortex fakes out the idea of xact...
    def _coreXactBegin(self):
        pass

    def _coreXactCommit(self):
        pass

class Cortex(s_cores_common.Cortex):

    def _initCortex(self):
        self.rowsbyid = collections.defaultdict(set)
        self.rowsbyprop = collections.defaultdict(set)
        self.rowsbyvalu = collections.defaultdict(set)

        self.initSizeBy('ge', self._sizeByGe)
        self.initRowsBy('ge', self._rowsByGe)

        self.initSizeBy('le', self._sizeByLe)
        self.initRowsBy('le', self._rowsByLe)

        self.initTufosBy('ge', self._tufosByGe)
        self.initTufosBy('le', self._tufosByLe)

        # use helpers from base class
        self.initRowsBy('gt', self._rowsByGt)
        self.initRowsBy('lt', self._rowsByLt)
        self.initTufosBy('gt', self._tufosByGt)
        self.initTufosBy('lt', self._tufosByLt)

        self.initSizeBy('range', self._sizeByRange)
        self.initRowsBy('range', self._rowsByRange)

        self._admin_store = {}

    def _getCoreXact(self, size=None):
        return CoreXact(self, size=size)

    def _tufosByGe(self, prop, valu, limit=None):
        # FIXME sortedcontainers optimizations go here
        valu, _ = self.getPropNorm(prop, valu)
        rows = self._rowsByGe(prop, valu, limit=limit)
        return self.getTufosByIdens([r[0] for r in rows])

    def _tufosByLe(self, prop, valu, limit=None):
        # FIXME sortedcontainers optimizations go here
        valu, _ = self.getPropNorm(prop, valu)
        rows = self._rowsByLe(prop, valu, limit=limit)
        return self.getTufosByIdens([r[0] for r in rows])

    def _sizeByRange(self, prop, valu, limit=None):
        minval = int(self.getPropNorm(prop, valu[0])[0])
        maxval = int(self.getPropNorm(prop, valu[1])[0])
        return sum(1 for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] >= minval and r[2] < maxval)

    def _rowsByRange(self, prop, valu, limit=None):
        minval = int(self.getPropNorm(prop, valu[0])[0])
        maxval = int(self.getPropNorm(prop, valu[1])[0])

        # HACK: for speed
        ret = [r for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] >= minval and r[2] < maxval]

        if limit is not None:
            ret = ret[:limit]

        return ret

    def _sizeByGe(self, prop, valu, limit=None):
        return sum(1 for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] >= valu)

    def _rowsByGe(self, prop, valu, limit=None):
        return [r for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] >= valu][:limit]

    def _sizeByLe(self, prop, valu, limit=None):
        return sum(1 for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] <= valu)

    def _rowsByLe(self, prop, valu, limit=None):
        return [r for r in self.rowsbyprop.get(prop, ()) if isint(r[2]) and r[2] <= valu][:limit]

    def _addRows(self, rows):
        for row in rows:
            row = (intern(row[0]), intern(row[1]), row[2], row[3])
            self.rowsbyid[row[0]].add(row)
            self.rowsbyprop[row[1]].add(row)
            self.rowsbyvalu[(row[1], row[2])].add(row)

    def _delRowsById(self, ident):
        for row in self.rowsbyid.pop(ident, ()):
            self._delRawRow(row)

    def _delRowsByIdProp(self, iden, prop, valu=None):
        if valu is None:
            rows = [row for row in self.rowsbyid.get(iden, ()) if row[1] == prop]
            [self._delRawRow(row) for row in rows]
            return

        rows = [row for row in self.rowsbyid.get(iden, ()) if row[1] == prop and row[2] == valu]
        [self._delRawRow(row) for row in rows]
        return

    def _getRowsByIdProp(self, iden, prop, valu=None):
        if valu is None:
            return [row for row in self.rowsbyid.get(iden, ()) if row[1] == prop]

        return [row for row in self.rowsbyid.get(iden, ()) if row[1] == prop and row[2] == valu]

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        for row in self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime):
            self._delRawRow(row)

    def _delRawRow(self, row):

        byid = self.rowsbyid.get(row[0])
        if byid is not None:
            byid.discard(row)

        byprop = self.rowsbyprop[row[1]]
        byprop.discard(row)
        if not byprop:
            self.rowsbyprop.pop(row[1], None)

        propvalu = (row[1], row[2])

        byvalu = self.rowsbyvalu[propvalu]
        byvalu.discard(row)
        if not byvalu:
            self.rowsbyvalu.pop(propvalu, None)

    def _getRowsById(self, iden):
        return list(self.rowsbyid.get(iden, ()))

    def _getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):

        if valu is None:
            rows = self.rowsbyprop.get(prop)
        else:
            rows = self.rowsbyvalu.get((prop, valu))

        if rows is None:
            return

        c = 0
        for row in rows:
            if mintime is not None and row[3] < mintime:
                continue

            if maxtime is not None and row[3] >= maxtime:
                continue

            yield row

            c += 1
            if limit is not None and c >= limit:
                break

    def _getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        if valu is None:
            rows = self.rowsbyprop.get(prop)
        else:
            rows = self.rowsbyvalu.get((prop, valu))

        if rows is None:
            return 0

        if mintime is not None:
            rows = [row for row in rows if row[3] >= mintime]

        if maxtime is not None:
            rows = [row for row in rows if row[3] < maxtime]

        return len(rows)

    def _getCoreType(self):
        return 'ram'

    def _getAdminValu(self, key, default):
        v = self._admin_store.get(key, default)
        if v is s_common.novalu:
            raise s_common.NoSuchName(name=key, mesg='Admin store has no such key present.')
        if v == default:
            return v
        ret = s_common.msgunpack(v)
        return ret

    def _setAdminValu(self, key, valu):
        mesg = 'Setting admin value in ram cortex [{}]. Not a persistent action.'.format(self.myfo[0])
        self.log(logging.WARNING, mesg=mesg, key=key, valu=valu)
        self._admin_store[key] = s_common.msgenpack(valu)
        return valu

ramcores = {}

def initRamCortex(link):
    '''
    Initialize a RAM based Cortex from a link tufo.

    NOTE: the "path" element of the link tufo is used to
          potentially return an existing cortex instance.

    '''
    path = link[1].get('path').strip('/')
    if not path:
        return Cortex(link)

    core = ramcores.get(path)
    if core is None:
        core = Cortex(link)

        ramcores[path] = core
        def onfini():
            ramcores.pop(path, None)

        core.onfini(onfini)

    return core
