import collections
import synapse.cores.common as common

from synapse.compat import isint

class Cortex(common.Cortex):

    def _initCortex(self):
        self.rowsbyid = collections.defaultdict(set)
        self.rowsbyprop = collections.defaultdict(set)
        self.rowsbyvalu = collections.defaultdict(set)

        self.initSizeBy('ge',self._sizeByGe)
        self.initRowsBy('ge',self._rowsByGe)

        self.initSizeBy('le',self._sizeByLe)
        self.initRowsBy('le',self._rowsByLe)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

    def _sizeByRange(self, prop, valu, limit=None):
        # HACK: for speed
        data = [0]
        def inc():
            data[0] += 1
        [ inc() for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] >= valu[0] and r[2] < valu[1] ]
        return data[0]

    def _rowsByRange(self, prop, valu, limit=None):
        # HACK: for speed
        ret = [ r for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] >= valu[0] and r[2] < valu[1] ]
        if limit != None:
            ret = ret[:limit]
        return ret

    def _sizeByGe(self, prop, valu, limit=None):
        return len([ r for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] >= valu ])

    def _rowsByGe(self, prop, valu, limit=None):
        return [ r for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] >= valu ][:limit]

    def _sizeByLe(self, prop, valu, limit=None):
        return len([ r for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] <= valu ])

    def _rowsByLe(self, prop, valu, limit=None):
        return [ r for r in self.rowsbyprop.get(prop,()) if isint(r[2]) and r[2] <= valu ][:limit]

    def _addRows(self, rows):
        for row in rows:
            self.rowsbyid[row[0]].add(row)
            self.rowsbyprop[row[1]].add(row)
            self.rowsbyvalu[ (row[1],row[2]) ].add(row)

    def _delRowsById(self, ident):
        for row in self.rowsbyid.pop(ident,()):
            self._delRawRow(row)

    def _delRowsByIdProp(self, iden, prop):
        rows = [ row for row in self.rowsbyid.get(iden) if row[1] == prop ]
        [ self._delRawRow(row) for row in rows ]

    def _getRowsByIdProp(self, iden, prop):
        return [ row for row in self.rowsbyid.get(iden) if row[1] == prop ]

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        for row in self.getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime):
            self._delRawRow(row)

    def _delRawRow(self, row):

        byid = self.rowsbyid.get(row[0])
        if byid != None:
            byid.discard(row)

        byprop = self.rowsbyprop[ row[1] ]
        byprop.discard(row)
        if not byprop:
            self.rowsbyprop.pop(row[1],None)

        propvalu = (row[1],row[2])

        byvalu = self.rowsbyvalu[propvalu]
        byvalu.discard(row)
        if not byvalu:
            self.rowsbyvalu.pop(propvalu,None)

    def _getRowsById(self, iden):
        return list(self.rowsbyid.get(iden,()))

    def _getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):

        if valu == None:
            rows = self.rowsbyprop.get(prop)
        else:
            rows = self.rowsbyvalu.get( (prop,valu) )

        if rows == None:
            return

        c = 0
        for row in rows:
            if mintime != None and row[3] < mintime:
                continue

            if maxtime != None and row[3] >= maxtime:
                continue

            yield row

            c +=1 
            if limit != None and c >= limit:
                break

    def _getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        if valu == None:
            rows = self.rowsbyprop.get(prop)
        else:
            rows = self.rowsbyvalu.get( (prop,valu) )

        if rows == None:
            return 0

        if mintime != None:
            rows = [ row for row in rows if row[3] >= mintime ]

        if maxtime != None:
            rows = [ row for row in rows if row[3] < maxtime ]

        return len(rows)

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
    if core == None:
        core = Cortex(link)

        ramcores[path] = core
        def onfini():
            ramcores.pop(path,None)

        core.onfini(onfini)

    return core
