import collections

import sortedcontainers

import synapse.cores.common
from synapse.compat import isint


class SortedRamCortex(synapse.cores.common.Cortex):
    '''
    SortedRamCortex is a RAM-backed Cortex that maintain int prop values
     in sorted order to facilitate range queries.

    Insertion performance appears to be a constant factor of 10% slower than
     synapse.cores.ram.Cortex
    Query by range performance is strictly better.
    Query by range runtime is O(log n) vs O(n) for the ram:// cortex.
    '''

    def _initCortex(self):

        def getValu(row):
            return row[2]

        def makePropSet():
            return sortedcontainers.SortedSet(key=getValu)

        self.rowsbyid = collections.defaultdict(set)
        # rows by props with type(value) == string
        self.srowsbyprop = collections.defaultdict(set)
        # rows by props with type(value) == int
        # split because sortedcontainers.SortedSet does not support keys with mixed types
        self.irowsbyprop = collections.defaultdict(makePropSet)
        self.rowsbyvalu = collections.defaultdict(set)

        self.initSizeBy('ge',self._sizeByGe)
        self.initRowsBy('ge',self._rowsByGe)

        self.initSizeBy('le',self._sizeByLe)
        self.initRowsBy('le',self._rowsByLe)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

    def _sizeByRange(self, prop, valu, limit=None):
        minrow = None
        if valu[0] != None:
            if not isint(valu[0]):
                return 0
            minrow = (None, None, valu[0], None)

        maxrow = None
        if valu[1] != None:
            if not isint(valu[1]):
                return 0
            maxrow = (None, None, valu[1], None)

        rowsbyprop = self.irowsbyprop.get(prop)
        if not rowsbyprop:
            return 0

        # if minval and maxval are provided, then we are doing a range query,
        #  of which minval is inclusive, and maxval is exclusive.
        # otherwise, we only support >= and <=, both of which are inclusive.
        return sum(1 for _ in rowsbyprop.irange(minimum=minrow, maximum=maxrow, inclusive=(True, not (minrow and maxrow))))

    def _rowsByRange(self, prop, valu, limit=None):
        minrow = None
        if valu[0] != None:
            if not isint(valu[0]):
                return []
            minrow = (None, None, valu[0], None)

        maxrow = None
        if valu[1] != None:
            if not isint(valu[1]):
                return []
            maxrow = (None, None, valu[1], None)

        rows = []
        rowsbyprop = self.irowsbyprop.get(prop)
        if not rowsbyprop:
            return rows

        for i, row in enumerate(rowsbyprop.irange(minimum=minrow, maximum=maxrow, inclusive=(True, not (minrow and maxrow)))):
            if limit != None and i > limit:
                return rows
            rows.append(row)
        return rows

    def _sizeByGe(self, prop, valu, limit=None):
        return self._sizeByRange(prop, (valu, None), limit=limit)

    def _rowsByGe(self, prop, valu, limit=None):
        return self._rowsByRange(prop, (valu, None), limit=limit)

    def _sizeByLe(self, prop, valu, limit=None):
        return self._sizeByRange(prop, (None, valu), limit=limit)

    def _rowsByLe(self, prop, valu, limit=None):
        return self._rowsByRange(prop, (None, valu), limit=limit)

    def _addRows(self, rows):
        for row in rows:
            self.rowsbyid[row[0]].add(row)
            if isint(row[2]):
                rowsbyprop = self.irowsbyprop
            else:
                rowsbyprop = self.srowsbyprop
            rowsbyprop[row[1]].add(row)
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

        if isint(row[2]):
            rowsbyprop = self.irowsbyprop
        else:
            rowsbyprop = self.srowsbyprop

        byprop = rowsbyprop[ row[1] ]
        byprop.discard(row)
        if not byprop:
            rowsbyprop.pop(row[1],None)

        propvalu = (row[1],row[2])

        byvalu = self.rowsbyvalu[propvalu]
        byvalu.discard(row)
        if not byvalu:
            self.rowsbyvalu.pop(propvalu,None)

    def _getRowsById(self, iden):
        return list(self.rowsbyid.get(iden,()))

    def _getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):

        if valu == None:
            rows = list(self.irowsbyprop.get(prop, ()))
            rows.extend(self.srowsbyprop.get(prop, ()))
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
            rows = list(self.irowsbyprop.get(prop, ()))
            rows.extend(self.srowsbyprop.get(prop, ()))
        else:
            rows = self.rowsbyvalu.get( (prop,valu) )

        if rows == None:
            return 0

        if mintime != None:
            rows = [ row for row in rows if row[3] >= mintime ]

        if maxtime != None:
            rows = [ row for row in rows if row[3] < maxtime ]

        return len(rows)


