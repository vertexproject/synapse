import time
import threading
import traceback
import collections

from synapse.compat import queue

import synapse.async as s_async
import synapse.aspects as s_aspects
import synapse.lib.threads as s_threads
import synapse.datamodel as s_datamodel

from synapse.common import *
from synapse.eventbus import EventBus

class NoSuchGetBy(Exception):pass

class Cortex(EventBus):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link, model=None):
        EventBus.__init__(self)

        self.link = link

        self.lock = threading.Lock()

        self.model = model
        self.sizebymeths = {}
        self.rowsbymeths = {}

        self._initCortex()

        self.isok = True

        self.mytufo = self.formTufoByProp('cortex','self')

    def getCortexProp(self, prop):
        return self.mytufo.get(prop)

    def setCortexProp(self, prop, valu):
        self.setTufoProp(self.mytufo,prop,valu)

    def addCortexTag(self, tag):
        self.addTufoTag(self.mytufo,tag)

    def delCortexTag(self, tag):
        self.delTufoTag(self.mytufo,tag)

    def getCortexTags(self):
        return s_aspects.getTufoTags(self.mytufo)

    def setDataModel(self, model):
        '''
        Set a DataModel instance to enforce when using Tufo API.

        Example:

            core.setDataModel(model)

        '''
        self.model = model

    def getDataModel(self):
        '''
        Return the DataModel instance for this Cortex.

        Example:

            model = core.getDataModel()
            if model != None:
                dostuff(model)

        '''
        return self.model

    def genDataModel(self):
        '''
        Return (and create if needed) the DataModel instance for this Cortex.

        Example:

            model = core.genDataModel()

        '''
        if self.model == None:
            self.model = s_datamodel.DataModel()
        return self.model

    def getDataModelDict(self):
        '''
        Return the DataModel dictionary for this Cortex.

        Example:

            moddef = core.getDataModelDict()
            if moddef != None:
                model = DataModel(model=moddef)
                dostuff(model)

        '''
        if self.model == None:
            return None

        return self.model.getModelDict()

    def isOk(self):
        '''
        An API allowing MetaCortex to test for internal error states.
        '''
        return self.isok

    def delAddRows(self, iden, rows):
        '''
        Delete rows by iden and add rows as a single operation.

        Example:

            core.delAddRows( iden, rows )

        Notes:

            This API is oriented toward "reparse" cases where iden
            will be the same for the new rows.

        '''
        self.delRowsById(iden)
        self.addRows(rows)

    def addRows(self, rows):
        '''
        Add (iden,prop,valu,time) rows to the Cortex.

        Example:

            import time
            now = int(time.time())

            rows = [
                (id1,'baz',30,now),
                (id1,'foo','bar',now),
            ]

            core.addRows(rows)

        '''
        self._addRows(rows)

    def addListRows(self, prop, *vals):
        '''
        Add rows by making a guid for each and using now().

        Example:

            core.addListRows('foo:bar',[ 1, 2, 3, 4])

        '''
        now = int(time.time())
        rows = [ (guid(), prop, valu, now) for valu in vals ]
        self.addRows(rows)
        return rows

    def getTufoList(self, tufo, name):
        '''
        Retrieve "list" values from a tufo.

        Example:

            for val in core.getTufoList(item,'foolist'):
                dostuff(val)

        '''
        prop = '%s:list:%s' % (tufo[0],name)
        return [ v for (i,p,v,t) in self.getRowsByProp(prop) ]

    def delTufoListValu(self, tufo, name, valu):
        prop = '%s:list:%s' % (tufo[0],name)
        self.delRowsByProp(prop,valu=valu)

    def addTufoList(self, tufo, name, *vals):
        '''
        Add "list" rows to a tufo.

        Example:

            core.addTufoList(tufo, 'counts', 99, 300, 1773)

        Notes:

            * this creates the tufo:list:<name> prop on the
              tufo to indicate that the list is present.

        '''
        rows = []
        now = int(time.time())
        prop = '%s:list:%s' % (tufo[0],name)

        haslist = 'tufo:list:%s' % name
        if tufo[1].get(haslist) == None:
            tufo[1][haslist] = 1
            rows.append( ( tufo[0], haslist, 1, now) )

        [ rows.append( (guid(),prop,v,now) ) for v in vals ]

        self.addRows( rows )

    def getRowsById(self, iden):
        '''
        Return all the rows for a given iden.

        Example:

            for row in core.getRowsById(iden):
                stuff()

        '''
        return self._getRowsById(iden)

    def getRowsByIds(self, idens):
        '''
        Return all the rows for a given list of idens.

        Example:

            rows = core.getRowsByIds( (id1, id2, id3) )

        '''
        return self._getRowsByIds(idens)

    def delRowsById(self, iden):
        '''
        Delete all the rows for a given iden.

        Example:

            core.delRowsById(iden)

        '''
        self._delRowsById(iden)

    def delRowsByIdProp(self, iden, prop):
        '''
        Delete rows with the givin combination of iden and prop[=valu].

        Example:

            core.delRowsByIdProp(id, 'foo')

        '''
        return self._delRowsByIdProp(iden, prop)

    def setRowsByIdProp(self, iden, prop, valu):
        '''
        Update/insert the value of the row(s) with iden and prop to valu.

        Example:

            core.setRowsByIdProp(iden,'foo',10)

        '''
        self._setRowsByIdProp(iden, prop, valu)

    def getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a tuple of (iden,prop,valu,time) rows by prop[=valu].

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)

        Notes:

            * Specify limit=<count> to limit return size
            * Specify mintime=<time> in epoch to filter rows
            * Specify maxtime=<time> in epoch to filter rows

        '''
        return tuple(self._getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but also lifts all other rows for iden.

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)
        Notes:

            * See getRowsByProp for options

        '''
        return tuple(self._getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Return the count of matching rows by prop[=valu]

        Example:

            if core.getSizeByProp('foo',valu=10) > 30:
                stuff()

        '''
        return self._getSizeByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def getRowsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve rows by a specialized index within the cortex.

        Example:

            rows = core.getRowsBy('range','foo',(20,30))

        Notes:
            * most commonly used to facilitate range searches

        '''
        meth = self._reqRowsByMeth(name)
        return meth(prop,valu,limit=limit)

    def getSizeBy(self, name, prop, valu, limit=None):
        '''
        Retrieve row count by a specialized index within the cortex.

        Example:

            size = core.getSizeBy('range','foo',(20,30))
            print('there are %d rows where 20 <= foo < 30 ' % (size,))

        '''
        meth = self._reqSizeByMeth(name)
        return meth(prop,valu,limit=limit)

    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Cortex.

        Example:

            def getbywoot(prop,valu,limit=None):
                return stuff() # list of rows

            core.initRowsBy('woot',getbywoot)

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        '''
        Initialize a "size by" handler for the Cortex.

        Example:

            def sizebywoot(prop,valu,limit=None):
                return stuff() # size of rows

            core.initSizeBy('woot',meth)

        '''
        self.sizebymeths[name] = meth

    def getTufoById(self, iden):
        '''
        Retrieve a tufo by id.

        Example:

            tufo = core.getTufoById(iden)

        '''
        rows = self.getRowsById(iden)
        if not rows:
            return None

        return (iden,{ p:v for (i,p,v,t) in rows })

    def getTufoByProp(self, prop, valu=None):
        '''
        Return an (iden,info) tuple by joining rows based on a property.

        Example:

            tufo = core.getTufoByProp('fqdn','woot.com')

        Notes:

            * This must be used only for rows added with formTufoByProp!

        '''
        rows = self.getJoinByProp(prop, valu=valu, limit=1)
        if not rows:
            return None

        tufo = ( rows[0][0], {} )
        for iden,prop,valu,stamp in rows:
            tufo[1][prop] = valu

        return tufo

    def getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of tufos by property.

        Example:

            for tufo in core.getTufosByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        rows = self.getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)

        res = collections.defaultdict(dict)
        [ res[i].__setitem__(p,v) for (i,p,v,t) in rows ]
        return list(res.items())

    def addTufoTag(self, tufo, tag, valu=None):
        '''
        Add an aspect tag to a tufo.

        Example:

            tufo = core.formTufoByProp('foo','bar')
            core.addTufoTag(tufo,'baz.faz')

        '''
        rows = s_aspects.genTufoRows(tufo,tag,valu=valu)
        self.addRows(rows)
        tufo[1].update({ p:v for (i,p,v,t) in rows })
        return tufo

    def delTufoTag(self, tufo, tag):
        '''
        Delete an aspect tag from a tufo.

        Example:

            tufo = core.getTufosByTag('foo','baz.faz')
            core.delTufoTag(tufo,'baz')

        '''
        iden = tufo[0]
        props = s_aspects.getTufoSubs(tufo,tag)
        [ self.delRowsByIdProp(iden,prop) for prop in props ]
        [ tufo[1].pop(p) for p in props ]
        return tufo

    def getTufosByTag(self, form, tag):
        '''
        Retrieve a list of tufos by form and tag.

        Example:

            for tufo in core.getTufosByTag('woot','foo.bar'):
                dostuff(tufo)

        '''
        prop = '%s:tag:%s' % (form,tag)
        return self.getTufosByProp(prop)

    def addTufoEvent(self, form, **props):
        '''
        Add a "non-deconflicted" tufo by generating a guid

        Example:

            tufo = core.addTufoEvent('foo',bar=baz)

        '''
        iden = guid()

        stamp = int(time.time())

        props = self._normTufoProps(form,props)
        props[form] = iden

        self.fire('tufo:form', form=form, valu=iden, props=props)
        self.fire('tufo:form:%s' % form, form=form, valu=iden, props=props)

        rows = [ (iden,p,v,stamp) for (p,v) in props.items() ]

        self.addRows(rows)

        tufo = (iden,props)

        self.fire('tufo:add', tufo=tufo)
        self.fire('tufo:add:%s' % form, tufo=tufo)

        return tufo

    def formTufoByTufo(self, tufo):
        '''
        Form an (iden,info) tufo by extracting information from an existing one.
        '''
        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)
        prefix = '%s:' % (form,)
        props = { k:v for (k,v) in tufo[1].items() if k.startswith(prefix) }
        return self.formTufoByProp(form,valu,**props)

    def formTufoByProp(self, form, valu, **props):
        '''
        Form an (iden,info) tuple by atomically deconflicting
        the existance of prop=valu and creating it if not present.

        Example:

            tufo = core.formTufoByProp('fqdn','woot.com')

        Notes:

            * this will trigger an 'cortex:tufo:add' event if the
              tufo does not yet exist and is being construted.

        '''
        if self.model != None:
            valu = self.model.getPropNorm(form,valu)

        with self.lock:
            tufo = self.getTufoByProp(form,valu=valu)
            if tufo != None:
                return tufo

            iden = guid()
            stamp = int(time.time())

            props = self._normTufoProps(form,props)
            props[form] = valu

            self.fire('tufo:form', form=form, valu=valu, props=props)
            self.fire('tufo:form:%s' % form, form=form, valu=valu, props=props)

            rows = [ (iden,p,v,stamp) for (p,v) in props.items() ]

            self.addRows(rows)

            tufo = (iden,props)

            self.fire('tufo:add', tufo=tufo)
            self.fire('tufo:add:%s' % form, tufo=tufo)

            return tufo

    def delTufo(self, tufo):
        '''
        Delete a tufo and it's associated props/lists/etc.


        Example:

            core.delTufo(foob)

        '''
        iden = tufo[0]
        with self.lock:
            self.delRowsById(iden)

        lists = [ p.split(':',2)[2] for p in tufo[1].keys() if p.startswith('tufo:list:') ]
        for name in lists:
            self.delRowsByProp('%s:list:%s' % (iden,name))

    def delTufoByProp(self, form, valu):
        '''
        Delete a tufo from the cortex by prop=valu.

        Example:

            core.delTufoByProp('foo','bar')

        '''
        if self.model != None:
            valu = self.model.getPropNorm(form,valu)

        item = self.getTufoByProp(form,valu)
        if item != None:
            self.delTufo(item)

        return item

    def delTufosByProp(self, prop, valu):
        '''
        Delete multiple tufos by a single property.
        '''
        for item in self.getTufosByProp(prop,valu):
            self.delTufo(item)

    def _normTufoProps(self, form, props):
        # add form prefix to tufo props
        props = {'%s:%s' % (form,p):v for (p,v) in props.items() }

        props['tufo:form'] = form

        # if we are using a data model, lets enforce it.
        if self.model != None:
            # if we have a model *and* a prop def
            # check to see if it should be a form
            fdef = self.model.getPropDef(form)
            if fdef != None and not fdef[1].get('form'):
                raise s_datamodel.NoSuchForm(form)

            props = self.model.getNormProps(props)
            defprops = self.model.getSubPropDefs(form)
            for p,v in defprops.items():
                props.setdefault(p,v)

        return props

    def setTufoProps(self, tufo, **props):
        '''
        Set ( with de-duplication ) the given tufo props.

        Example:

            tufo = core.setTufoProps(tufo, woot='hehe', blah=10)

        '''
        # add tufo form prefix to props
        form = tufo[1].get('tufo:form')
        props = { '%s:%s' % (form,p):v for (p,v) in props.items() }

        # normalize property values
        if self.model != None:
            props = { p:self.model.getPropNorm(p,v) for (p,v) in props.items() }

        tid = tufo[0]

        props = { p:v for (p,v) in props.items() if tufo[1].get(p) != v }

        for p,v in props.items():
            self.setRowsByIdProp(tid,p,v)

        tufo[1].update(props)
        return tufo

    def setTufoProp(self, tufo, prop, valu):
        '''
        Set a single tufo property.

        Example:

            core.setTufoProp(tufo, 'woot', 'hehe')

        '''
        self.setTufoProps(tufo, **{prop:valu})
        return tufo

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)

        '''
        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete a group of rows by selecting for property and joining on iden.

        Example:

            core.delJoinByProp('foo',valu=10)

        '''
        return self._delJoinByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsById(irow[0]):
                yield jrow

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)
        done = set()
        for row in rows:
            iden = row[0]
            if iden in done:
                continue

            self.delRowsById(iden)
            done.add(iden)

    def _reqSizeByMeth(self, name):
        meth = self.sizebymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth

    def _reqRowsByMeth(self, name):
        meth = self.rowsbymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth

    def _setRowsByIdProp(self, iden, prop, valu):
        # base case is delete and add
        self._delRowsByIdProp(iden, prop)
        rows = [ (iden, prop, valu, now()) ]
        self.addRows(rows)
