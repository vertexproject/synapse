import json
import time
import itertools
import threading
import traceback
import collections

from synapse.compat import queue

import synapse.async as s_async
import synapse.compat as s_compat
import synapse.datamodel as s_datamodel

import synapse.lib.tags as s_tags
import synapse.lib.cache as s_cache
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.eventbus import EventBus

class NoSuchGetBy(Exception):pass

def chunked(n, iterable):
    it = iter(iterable)
    while True:
       chunk = tuple(itertools.islice(it, n))
       if not chunk:
           return

       yield chunk

class Cortex(EventBus):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link):
        EventBus.__init__(self)

        self.link = link

        self.lock = threading.Lock()
        self.statfuncs = {}

        self.tagcache = {}
        self.splicefuncs = {}

        self.model = s_datamodel.DataModel()

        self.sizebymeths = {}
        self.rowsbymeths = {}

        self.savebus = EventBus()
        self.loadbus = EventBus()

        self.loadbus.on('core:save:add:rows', self._loadAddRows)

        self.loadbus.on('core:save:del:rows:by:iden', self._loadDelRowsById)
        self.loadbus.on('core:save:del:rows:by:prop', self._loadDelRowsByProp)

        self.loadbus.on('core:save:set:rows:by:idprop', self._loadSetRowsByIdProp)
        self.loadbus.on('core:save:del:rows:by:idprop', self._loadDelRowsByIdProp)

        self.onfini( self.savebus.fini )
        self.onfini( self.loadbus.fini )

        self.addStatFunc('any',self._calcStatAny)
        self.addStatFunc('all',self._calcStatAll)
        self.addStatFunc('min',self._calcStatMin)
        self.addStatFunc('max',self._calcStatMax)
        self.addStatFunc('sum',self._calcStatSum)
        self.addStatFunc('count',self._calcStatCount)
        self.addStatFunc('histo',self._calcStatHisto)
        self.addStatFunc('average',self._calcStatAverage)

        self._initCortex()

        self.model.addTufoForm('syn:tag', ptype='str:lwr')
        self.model.addTufoProp('syn:tag','up',ptype='str:lwr')
        self.model.addTufoProp('syn:tag','doc',defval='',ptype='str')
        self.model.addTufoProp('syn:tag','depth',defval=0,ptype='int')
        self.model.addTufoProp('syn:tag','title',defval='',ptype='str')

        #self.model.addTufoForm('syn:model',ptype='str')

        #self.model.addTufoForm('syn:type',ptype='str')
        #self.model.addTufoProp('syn:type','base',ptype='str',doc='what base type does this type extend?')
        #self.model.addTufoProp('syn:type','baseinfo',ptype='str',doc='Base type specific info (for example, a regex)')

        #self.model.addTufoForm('syn:form',ptype='str:prop')
        #self.model.addTufoProp('syn:form','doc',ptype='str')

        #self.model.addTufoForm('syn:prop',ptype='str:prop')
        #self.model.addTufoProp('syn:prop','doc',ptype='str')
        #self.model.addTufoProp('syn:prop','form',ptype='str:syn:prop')

        #self.model.addTufoProp('syn:prop','ptype',ptype='str')
        #self.model.addTufoProp('syn:prop','title',ptype='str')
        #self.model.addTufoProp('syn:prop','defval') # ptype='any'

        #self.model.addTufoForm('syn:splice',ptype='guid')
        #self.model.addTufoProp('syn:splice','date',ptype='time:epoch',doc='Time that the splice was requested')
        #self.model.addTufoProp('syn:splice','user',ptype='str',doc='Time user/system which requested the splice')
        #self.model.addTufoProp('syn:splice','note',ptype='str',doc='Filthy humon notes about the change')
        #self.model.addTufoProp('syn:splice','status',ptype='str',doc='Enum for init,done,deny to show the splice status')
        #self.model.addTufoProp('syn:splice','action',ptype='str:lwr',doc='The requested splice action')

        # FIXME load forms / props / etc

        self.model.addTufoGlob('syn:splice','form:*')    # syn:splice:form:fqdn=woot.com
        self.model.addTufoGlob('syn:splice','action:*')

        self.on('tufo:add:syn:tag', self._onAddSynTag)

        #self.on('tufo:add:syn:type', self._onAddSynType)
        #self.on('tufo:add:syn:form', self._onAddSynForm)
        #self.on('tufo:add:syn:prop', self._onAddSynProp)

        self.on('tufo:del:syn:tag', self._onDelSynTag)
        self.on('tufo:form:syn:tag', self._onFormSynTag)

        self.isok = True

    #def _onAddSynForm(self, mesg):
        #pass

    #def _onAddSynType(self, mesg):
        #pass

    #def _onAddSynProp(self, mesg):
        #pass

    def _onDelSynTag(self, mesg):
        # deleting a tag.  delete all sub tags and wipe tufos.
        tufo = mesg[1].get('tufo')
        valu = tufo[1].get('syn:tag')

        [ self.delTufo(t) for t in self.getTufosByProp('syn:tag:up',valu) ]

        # do the (possibly very heavy) removal of the tag from all known forms.
        for form in self.model.getTufoForms():
            [ self.delTufoTag(t,valu) for t in self.getTufosByTag(form,valu) ]

    def _onAddSynTag(self, mesg):
        tufo = mesg[1].get('tufo')
        uptag = tufo[1].get('syn:tag:up')

        if uptag != None:
            self._genTufoTag(uptag)

    def _onFormSynTag(self, mesg):
        valu = mesg[1].get('valu')
        props = mesg[1].get('props')

        tags = valu.split('.')

        tlen = len(tags)

        if tlen > 1:
            props['syn:tag:up'] = '.'.join(tags[:-1])

        props['syn:tag:depth'] = tlen - 1

    def setSaveFd(self, fd, load=True):
        '''
        Set a save fd for the cortex and optionally load.

        Example:

            core.setSaveFd(fd)

        '''
        if load:
            for mesg in msgpackfd(fd):
                self.loadbus.dist(mesg)

        def savemesg(mesg):
            fd.write( msgenpack(mesg) )

        self.savebus.link(savemesg)

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
        # FIXME this is deprecated but remains for backward compat
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
        self.savebus.fire('core:save:add:rows', rows=rows)
        self._addRows(rows)

    def _loadAddRows(self, mesg):
        self._addRows( mesg[1].get('rows') )

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

    def getRowsByIdProp(self, iden, prop):
        '''
        Return rows with the given <iden>,<prop>.

        Example:

            for row in core.getRowsByIdProp(iden,'foo:bar'):
                dostuff(row)

        '''
        return self._getRowsByIdProp(iden, prop)

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
        self.savebus.fire('core:save:del:rows:by:iden', iden=iden)
        self._delRowsById(iden)

    def _loadDelRowsById(self, mesg):
        self._delRowsById( mesg[1].get('iden') )

    def delRowsByIdProp(self, iden, prop):
        '''
        Delete rows with the givin combination of iden and prop[=valu].

        Example:

            core.delRowsByIdProp(id, 'foo')

        '''
        self.savebus.fire('core:save:del:rows:by:idprop', iden=iden, prop=prop)
        return self._delRowsByIdProp(iden, prop)

    def _loadDelRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        self._delRowsByIdProp(iden,prop)

    def _loadSetRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        self._setRowsByIdProp(iden,prop,valu)

    def setRowsByIdProp(self, iden, prop, valu):
        '''
        Update/insert the value of the row(s) with iden and prop to valu.

        Example:

            core.setRowsByIdProp(iden,'foo',10)

        '''
        self.savebus.fire('core:save:set:rows:by:idprop', iden=iden, prop=prop, valu=valu)
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

    def getPivotRows(self, prop, byprop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but pivots through "iden" to a different property.
        This can be a light way to return a single property from a tufo rather than lifting the whole.

        Example:

            # return rows for the foo:bar prop by lifting foo:baz=10 and pivoting through iden.

            for row in core.getPivotRows('foo:bar', 'foo:baz', valu=10):
                dostuff()

        '''
        return tuple(self._getPivotRows(prop, byprop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

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

    def _genTufoTag(self, tag):
        if not self.tagcache.get(tag):
            self.formTufoByProp('syn:tag',tag)
            self.tagcache[tag] = True

    def addTufoTag(self, tufo, tag, valu=None):
        '''
        Add a tag to a tufo.

        Example:

            tufo = core.formTufoByProp('foo','bar')
            core.addTufoTag(tufo,'baz.faz')

        '''
        self._genTufoTag(tag)
        rows = s_tags.genTufoRows(tufo,tag,valu=valu)
        self.addRows(rows)
        tufo[1].update({ p:v for (i,p,v,t) in rows })
        return tufo

    def delTufoTag(self, tufo, tag):
        '''
        Delete a tag from a tufo.

        Example:

            tufo = core.getTufosByTag('foo','baz.faz')
            core.delTufoTag(tufo,'baz')

        '''
        iden = tufo[0]
        props = s_tags.getTufoSubs(tufo,tag)
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
        prop = '*|%s|%s' % (form,tag)
        return self.getTufosByProp(prop)

    def addTufoKeys(self, tufo, keyvals, stamp=None):
        '''
        A raw row adding API to allow tufo selection by more than one possible value.

        Note: only use this API if you really know how it effects your model.
        '''
        if stamp == None:
            stamp = int(time.time())

        rows = []
        form = tufo[1].get('tufo:form')
        for key,val in keyvals:
            prop = '%s:%s' % (form,key)
            valu = self._normTufoProp(prop,val)

            rows.append( (tufo[0], prop, valu, stamp) )

        self.addRows(rows)

    def addTufoEvent(self, form, **props):
        '''
        Add a "non-deconflicted" tufo by generating a guid

        Example:

            tufo = core.addTufoEvent('foo',bar=baz)

        Notes:

            If props contains a key "time" it will be used for
            the cortex timestap column in the row storage.

        '''
        return self.addTufoEvents(form,(props,))[0]

    def addJsonText(self, form, text):
        '''
        Add and fully index a blob of JSON text.

        Example:

        '''
        item = json.loads(text)
        return self.addJsonItem(item)

    def addJsonItem(self, form, item, tstamp=None):
        '''
        Add and fully index a JSON compatible data structure ( not in text form ).

        Example:

            foo = { 'bar':10, 'baz':{ 'faz':'hehe', 'woot':30 } }

            core.addJsonItem('foo',foo)

        '''
        return self.addJsonItems(form, (item,), tstamp=tstamp)

    def getStatByProp(self, stat, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Calculate and return a statistic for the specified rows.
        ( See getRowsByProp docs for most args )

        Various statistics types are builtin.

        sum     - total of all row values
        count   - number of rows
        histo   - histogram of values
        average - sum / count

        min     - minimum value
        max     - maximum value

        any     - True if any value is true
        all     - True if every value is true

        Example:

            minval = core.getStatByProp('min','foo:bar')

        '''
        statfunc = self.statfuncs.get(stat)
        if statfunc == None:
            raise Exception('Unknown Stat: %s' % (stat,))

        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return statfunc(rows)

    def addStatFunc(self, name, func):
        '''
        Add a callback function to implement a statistic type.

        Example:

            def calcwoot(rows):
                sum([ r[2] for r in rows ]) + 99
                ...

            core.addStatFunc('woot', calcwoot)

            # later..
            woot = core.getStatByProp('haha')

        '''
        self.statfuncs[name] = func

    def addJsonItems(self, form, items, tstamp=None):
        '''
        Add and fully index a list of JSON compatible data structures.

        Example:

            core.addJsonItems('foo', foolist)

        '''
        if tstamp == None:
            tstamp = int(time.time())

        for chunk in chunked(100,items):

            for item in chunk:
                iden = guid()

                props = self._primToProps(form,item)
                props = [ (p,self._normTufoProp(p,v)) for (p,v) in props ]

                rows = [ (iden,p,v,tstamp) for (p,v) in props ]

                rows.append( (iden, form, iden, tstamp) )
                rows.append( (iden, 'prim:json', json.dumps(item), tstamp) )

            self.addRows(rows)

    def getJsonItems(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of (iden,item) tuples (similar to tufos, but with hierarchical structure )

        Example:

            x = {
                'bar':10,
            }

            core.addJsonItem('foo',x)

            # ... later ...

            for prim in core.getJsonsByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        rows = self.getPivotRows('prim:json', prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
        return [ json.loads(r[2]) for r in rows ]

    def _primToProps(self, form, item):
        '''
        Take a json compatible primitive item and return a list of
        "index" props for the various fields/values.
        '''
        props = [ ('prim:form',form) ]

        todo = [ (form,item) ]
        while todo:
            path,item = todo.pop()

            itype = type(item)

            if itype in s_compat.numtypes:
                props.append( (path,item) )
                continue

            if itype in s_compat.strtypes:
                props.append( (path,item) )
                continue

            if itype == bool:
                props.append( (path,int(item)) )
                continue

            if itype in (list,tuple):
                props.append( ('prim:type:list',path) )
                [ todo.append((path,valu)) for valu in item ]
                continue

            if itype == dict:
                props.append( ('prim:type:dict',path) )
                for prop,valu in item.items():
                    todo.append( ('%s:%s' % (path,prop), valu ) )

        return props

    def addTufoEvents(self, form, propss):
        '''
        Add a list of tufo events in bulk.

        Example:

            propss = [
                {'foo':10,'bar':30},
                {'foo':11,'bar':99},
            ]

            core.addTufoEvents('woot',propss)

        '''
        nowstamp = int(time.time())

        ret = []
        for chunk in chunked(1000,propss):

            rows = []
            tufos = []

            for props in chunk:

                iden = guid()

                stamp = props.get('time')
                if stamp == None:
                    stamp = nowstamp

                props = self._normTufoProps(form,props)
                props[form] = iden

                self.fire('tufo:form', form=form, valu=iden, props=props)
                self.fire('tufo:form:%s' % form, form=form, valu=iden, props=props)

                rows.extend([ (iden,p,v,stamp) for (p,v) in props.items() ])

                tufos.append( (iden,props) )

            self.addRows(rows)

            for tufo in tufos:
                self.fire('tufo:add', tufo=tufo)
                self.fire('tufo:add:%s' % form, tufo=tufo)

            ret.extend(tufos)

        return ret

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
        form = tufo[1].get('tufo:form')

        self.fire('tufo:del',tufo=tufo)
        self.fire('tufo:del:%s' % form, tufo=tufo)

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

    def _normTufoProp(self, prop, valu):
        if self.model != None:
            valu = self.model.getPropNorm(prop,valu)
        return valu

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

    def addSaveLink(self, func):
        '''
        Add an event callback to receive save events for this cortex.

        Example:

            def savemesg(mesg):
                dostuff()

            core.addSaveLink(savemesg)

        '''
        self.savebus.link(func)

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

        if props:
            self.fire('tufo:set', tufo=tufo, props=props)

        for p,v in props.items():

            oldv = tufo[1].get(p)
            self.setRowsByIdProp(tid,p,v)

            tufo[1][p] = v

            self.fire('tufo:set:%s' % (p,), tufo=tufo, prop=p, valu=v, oldv=oldv)

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
        self.savebus.fire('core:save:del:rows:by:prop', prop=prop, valu=valu, mintime=mintime, maxtime=maxtime)
        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _loadDelRowsByProp(self, mesg):
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        mint = mesg[1].get('mintime')
        maxt = mesg[1].get('maxtime')
        self._delRowsByProp(prop, valu=valu, mintime=mint, maxtime=maxt)

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

    def _getPivotRows(self, prop, byprop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(byprop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsByIdProp( irow[0], prop ):
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

    def _calcStatSum(self, rows):
        return sum([ r[2] for r in rows ])

    def _calcStatHisto(self, rows):
        histo = collections.defaultdict(int)
        for row in rows:
            histo[row[2]] += 1
        return histo

    def _calcStatCount(self, rows):
        return len(rows)

    def _calcStatMin(self, rows):
        return min([ r[2] for r in rows ])

    def _calcStatMax(self, rows):
        return max([ r[2] for r in rows ])

    def _calcStatAverage(self, rows):
        tot = sum([ r[2] for r in rows ])
        return tot / float(len(rows))

    def _calcStatAny(self, rows):
        return any([ r[2] for r in rows ])

    def _calcStatAll(self, rows):
        return all([ r[2] for r in rows ])

