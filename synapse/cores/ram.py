import collections
import synapse.cores.common as common

class Cortex(common.Cortex):

    def _initCortex(self):
        self.rowsbyid = collections.defaultdict(set)
        self.rowsbyprop = collections.defaultdict(set)
        self.rowsbyvalu = collections.defaultdict(set)

        self.initSizeBy('range',self._sizeByRange)
        self.initRowsBy('range',self._rowsByRange)

    def _sizeByRange(self, prop, valu, limit=None):
        # HACK: for speed
        data = dict(size=0)
        def inc():
            data['size'] += 1
        [ inc() for r in self.rowsbyprop.get(prop,()) if r[2] >= valu[0] and r[2] < valu[1] ]
        return data['size']

    def _rowsByRange(self, prop, valu, limit=None):
        # HACK: for speed
        ret = [ r for r in self.rowsbyprop.get(prop,()) if r[2] >= valu[0] and r[2] < valu[1] ]
        if limit != None:
            ret = ret[:limit]
        return ret

    def _addRows(self, rows):
        for row in rows:
            self.rowsbyid[row[0]].add(row)
            self.rowsbyprop[row[1]].add(row)
            self.rowsbyvalu[ (row[1],row[2]) ].add(row)

    def _delRowsById(self, ident):
        for row in self.rowsbyid.pop(ident,()):
            self._delRawRow(row)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        for row in self.getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime):
            self._delRawRow(row)

    def _delRawRow(self, row):
        byprop = self.rowsbyprop[ row[1] ]
        byprop.discard(row)
        if not byprop:
            self.rowsbyprop.pop(row[1],None)

        propvalu = (row[1],row[2])

        byvalu = self.rowsbyvalu[propvalu]
        byvalu.discard(row)
        if not byvalu:
            self.rowsbyvalu.pop(propvalu,None)

    def _getRowsById(self, ident):
        return self.rowsbyid.get(ident,())

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

        if mintime != None:
            rows = [ row for row in rows if row[3] >= mintime ]

        if maxtime != None:
            rows = [ row for row in rows if row[3] < maxtime ]

        return len(rows)

    def _getJoinBy(self, name, prop, valu):
        pass

    def _getRowsBy(self, name, prop, valu):
        pass

