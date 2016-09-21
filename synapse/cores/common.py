import json
import time
import itertools
import threading
import traceback
import collections

from synapse.compat import queue

import synapse.async as s_async
import synapse.compat as s_compat
import synapse.reactor as s_reactor
#import synapse.datamodel as s_datamodel

import synapse.lib.tags as s_tags
import synapse.lib.cache as s_cache
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.eventbus import EventBus
from synapse.datamodel import DataModel

class NoSuchGetBy(Exception):pass

def chunked(n, iterable):
    it = iter(iterable)
    while True:
       chunk = tuple(itertools.islice(it, n))
       if not chunk:
           return

       yield chunk

class Cortex(EventBus,DataModel):
    '''
    Top level Cortex key/valu storage object.
    '''
    def __init__(self, link):
        EventBus.__init__(self)
        DataModel.__init__(self)

        self._link = link

        #self.lock = threading.RLock()
        self.lock = threading.Lock()
        self.inclock = threading.Lock()

        self.statfuncs = {}

        self.auth = None

        self.secure = 0
        self.enforce = 0

        self.tagcache = {}
        self.splicefuncs = {}

        self.sizebymeths = {}
        self.rowsbymeths = {}
        self.tufosbymeths = {}

        #############################################################
        # buses to save/load *raw* save events
        #############################################################
        self.savebus = EventBus()
        self.loadbus = EventBus()

        self.loadbus.on('core:save:add:rows', self._loadAddRows)
        self.loadbus.on('core:save:del:rows:by:iden', self._loadDelRowsById)
        self.loadbus.on('core:save:del:rows:by:prop', self._loadDelRowsByProp)
        self.loadbus.on('core:save:set:rows:by:idprop', self._loadSetRowsByIdProp)
        self.loadbus.on('core:save:del:rows:by:idprop', self._loadDelRowsByIdProp)

        #############################################################
        # bus for model layer sync
        # sync events are fired on the cortex and may be ingested
        # into another coretx using the sync() method.
        #############################################################
        self.on('tufo:add', self._fireCoreSync )
        self.on('tufo:del', self._fireCoreSync )
        self.on('tufo:set', self._fireCoreSync )
        self.on('tufo:tag:add', self._fireCoreSync )
        self.on('tufo:tag:del', self._fireCoreSync )

        self.syncact = s_reactor.Reactor()
        self.syncact.act('tufo:add', self._actSyncTufoAdd )
        self.syncact.act('tufo:del', self._actSyncTufoDel )
        #self.syncact.act('tufo:set', self._actSyncTufoSet )
        self.syncact.act('tufo:tag:add', self._actSyncTufoTagAdd )
        self.syncact.act('tufo:tag:del', self._actSyncTufoTagDel )

        #############################################################

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

        # FIXME unicode / "word" characters
        #self.addSubType('syn:tag','str', regex='^[a-z0-9._]+$', lower=1)
        #self.addSubType('syn:prop','str', regex='^[a-z0-9:_]+$', lower=1)
        #self.addSubType('syn:type','str', regex='^[a-z0-9:_]+$', lower=1)

        self.addTufoForm('syn:tag', ptype='syn:tag')
        self.addTufoProp('syn:tag','up',ptype='syn:tag')
        self.addTufoProp('syn:tag','doc',defval='',ptype='str')
        self.addTufoProp('syn:tag','depth',defval=0,ptype='int')
        self.addTufoProp('syn:tag','title',defval='',ptype='str')

        #self.model.addTufoForm('syn:model',ptype='str')

        self.addTufoForm('syn:type',ptype='syn:type')
        self.addTufoProp('syn:type','doc',ptype='str', defval='??', doc='Description for this type')
        self.addTufoProp('syn:type','ver',ptype='int', defval=1, doc='What version is this type')
        self.addTufoProp('syn:type','base',ptype='str', doc='what type does this type extend?', req=True)
        self.addTufoGlob('syn:type','info:*')

        self.addTufoForm('syn:form',ptype='syn:prop')
        self.addTufoProp('syn:form','doc',ptype='str')

        self.addTufoForm('syn:prop',ptype='syn:prop')
        self.addTufoProp('syn:prop','doc',ptype='str')
        self.addTufoProp('syn:prop','form',ptype='syn:prop')
        self.addTufoProp('syn:prop','ptype',ptype='syn:type')

        self.addTufoForm('syn:core')
        self.addTufoProp('syn:core','url', ptype='inet:url')

        #self.addTufoProp('syn:core','opts:secure', ptype='bool', defval=0)
        self.addTufoProp('syn:core','opts:enforce', ptype='bool', defval=0)

        #self.on('tufo:set:syn:core:opts:secure', self._onSetSecure )
        self.on('tufo:set:syn:core:opts:enforce', self._onSetEnforce )

        self.myfo = self.formTufoByProp('syn:core','self')
        self.secure = self.myfo[1].get('syn:core:opts:secure',0)
        self.enforce = self.myfo[1].get('syn:core:opts:enforce',0)

        #forms = self.getTufosByProp('syn:form')

        #self.addTufoProp('syn:prop','ptype',ptype='str')
        #self.addTufoProp('syn:prop','title',ptype='str')
        #self.addTufoProp('syn:prop','defval') # ptype='any'

        #self.addTufoForm('syn:splice',ptype='guid')
        #self.addTufoProp('syn:splice','date',ptype='time:epoch',doc='Time that the splice was requested')
        #self.addTufoProp('syn:splice','user',ptype='str',doc='Time user/system which requested the splice')
        #self.addTufoProp('syn:splice','note',ptype='str',doc='Filthy humon notes about the change')
        #self.addTufoProp('syn:splice','status',ptype='str',doc='Enum for init,done,deny to show the splice status')
        #self.addTufoProp('syn:splice','action',ptype='str:lwr',doc='The requested splice action')

        # FIXME load forms / props / etc

        self.addTufoForm('syn:splice', ptype='guid')

        self.addTufoGlob('syn:splice','on:*')     # syn:splice:on:fqdn=woot.com
        self.addTufoGlob('syn:splice','act:*')    # action arguments

        self.addTufoProp('syn:splice','perm', ptype='str', doc='Permissions str for glob matching')
        self.addTufoProp('syn:splice','reqtime', ptype='time:epoch', doc='When was the splice requested')

        self.addTufoProp('syn:splice','user', ptype='str', defval='??', doc='What user is requesting the splice')
        self.addTufoProp('syn:splice','note', ptype='str', defval='', doc='Notes about the splice')
        self.addTufoProp('syn:splice','status', ptype='str', defval='new', doc='Splice status')
        self.addTufoProp('syn:splice','action', ptype='str', doc='What action is the splice requesting')
        #self.addTufoProp('syn:splice','actuser', ptype='str', doc='What user is activating the splice')
        #self.addTufoProp('syn:splice','acttime', ptype='time:epoch', doc='When was the splice activated')

        self.on('tufo:add:syn:tag', self._onAddSynTag)
        self.on('tufo:add:syn:type', self._onAddSynType)
        self.on('tufo:add:syn:prop', self._onAddSynProp)

        #self.on('tufo:add:syn:type', self._onAddSynType)
        #self.on('tufo:add:syn:form', self._onAddSynForm)
        #self.on('tufo:add:syn:prop', self._onAddSynProp)

        self.on('tufo:del:syn:tag', self._onDelSynTag)
        self.on('tufo:form:syn:tag', self._onFormSynTag)

        self.isok = True

        self.splicers = {}

        self.splicers['tufo:add'] = self._spliceTufoAdd
        self.splicers['tufo:del'] = self._spliceTufoDel
        self.splicers['tufo:set'] = self._spliceTufoSet
        self.splicers['tufo:tag:add'] = self._spliceTufoTagAdd
        self.splicers['tufo:tag:del'] = self._spliceTufoTagDel

    def _onSetEnforce(self, mesg):
        tufo = mesg[1].get('tufo')
        valu = mesg[1].get('valu')

        if tufo[0] != self.myfo[0]:
            return

        self.enforce = valu

    def _reqSpliceInfo(self, act, info, prop):
        valu = info.get(prop)
        if prop == None:
            raise Exception('Splice: %s requires %s' % (act,prop))
        return valu

    def _spliceTufoAdd(self, act, info, props):

        form = self._reqSpliceInfo(act,info,'form')
        valu = self._reqSpliceInfo(act,info,'valu')

        tprops = info.get('props',{})

        props['on:%s' % form] = valu

        perm = 'tufo:add:%s' % (form,)

        props['perm'] = perm
        props['status'] = 'done'

        # FIXME apply perm

        splice = None

        item = self.formTufoByProp(form,valu,**tprops)

        # if the tufo is newly formed, create a splice
        if item[1].get('.new'):
            splice = self.formTufoByProp('syn:splice',guid(),**props)

        return splice,item

    def _isSpliceAllow(self, props):
        props['status'] = 'done'

        if self.auth != None:
            user = props.get('user')
            perm = props.get('perm')
            if not self.auth.isUserAllowed(user,perm):
                props['status'] = 'pend'
                return False

        return True

    def _spliceTufoSet(self, act, info, props):
        form = self._reqSpliceInfo(act,info,'form')
        valu = self._reqSpliceInfo(act,info,'valu')
        prop = self._reqSpliceInfo(act,info,'prop')
        pval = self._reqSpliceInfo(act,info,'pval')

        props['on:%s' % form] = valu

        fullprop = '%s:%s' % (form,prop)

        props['perm'] = 'tufo:set:%s' % fullprop

        # FIXME apply perm

        item = self.getTufoByProp(form,valu=valu)
        if item == None:
            raise NoSuchTufo('%s=%r' % (form,valu))

        oval = item[1].get(fullprop)
        if oval == pval:
            return None,item

        if oval != None:
            props['act:oval'] = oval

        item = self.setTufoProp(item,prop,pval)
        splice = self.formTufoByProp('syn:splice',guid(),**props)

        return splice,item

    def _spliceTufoDel(self, act, info, props):

        form = self._reqSpliceInfo(act,info,'form')
        valu = self._reqSpliceInfo(act,info,'valu')

        item = self.getTufoByProp(form,valu=valu)
        if item == None:
            raise NoSuchTufo('%s=%r' % (form,valu))

        props['on:%s' % form] = valu
        props['status'] = 'done'

        props['perm'] = 'tufo:del:%s' % form

        self.delTufo(item)

        splice = self.formTufoByProp('syn:splice',guid(),**props)

        return splice,item

    def _spliceTufoTagAdd(self, act, info, props):
        tag = self._reqSpliceInfo(act,info,'tag')
        form = self._reqSpliceInfo(act,info,'form')
        valu = self._reqSpliceInfo(act,info,'valu')

        item = self.getTufoByProp(form,valu)
        if item == None:
            raise NoSuchTufo('%s=%r' % (form,valu))

        if s_tags.tufoHasTag(item,tag):
            return None,item

        props['on:%s' % form] = valu

        perm = 'tufo:tag:add:%s*%s' % (form,tag)

        props['perm'] = perm
        props['status'] = 'done'

        item = self.addTufoTag(item,tag)
        splice = self.formTufoByProp('syn:splice',guid(),**props)
        return splice,item

    def _spliceTufoTagDel(self, act, info, props):
        tag = self._reqSpliceInfo(act,info,'tag')
        form = self._reqSpliceInfo(act,info,'form')
        valu = self._reqSpliceInfo(act,info,'valu')

        item = self.getTufoByProp(form,valu)
        if item == None:
            raise NoSuchTufo('%s=%r' % (form,valu))

        if not s_tags.tufoHasTag(item,tag):
            return None,item

        props['on:%s' % form] = valu

        perm = 'tufo:tag:del:%s*%s' % (form,tag)

        props['perm'] = perm
        props['status'] = 'done'

        item = self.delTufoTag(item,tag)
        splice = self.formTufoByProp('syn:splice',guid(),**props)
        return splice,item

    def splice(self, user, act, actinfo, **props):
        '''
        Apply and track a modification to the cortex.

        The splice API will return a tuple of splice,retval.

        If the splice does not cause a change ( such as forming a tufo
        that exists already ) no splice is created and instead None,retval
        is returned (for example, tufo:add returns the tufo in retval )

        If the splice is pended ( due to perms ) the splice will have status
        set to "pend" retval will be None.

        Example:

            actinfo = {
                'form':'foo',
                'valu':'bar',
                'props':{
                    'size':20,
                    'name':'woot',
                },
            }

            splice,retval = core.splice('visi','tufo:add', form='foo', valu='bar')
            splice,retval = core.splice('tufo:add', actinfo, user='visi')

        Actions:
            'tufo:add' form=<name> valu=<valu> props=<props>
            'tufo:del' form=<name> valu=<valu>
            'tufo:set' form=<name> valu=<valu> props=<props>
            'tufo:tag:add' form=<name> valu=<valu> tag=<tag>
            'tufo:tag:del' form=<name> valu=<valu> tag=<tag>

        Returns:

            (splice,retval)

        '''
        props['user'] = user
        props['action'] = act
        props['reqtime'] = now()

        props.update( dict(self._primToProps('act', actinfo)) )

        func = self.splicers.get(act)
        if func == None:
            raise Exception('No Such Splice Action: %s' % (act,))

        return func(act,actinfo,props)

    def _fireCoreSync(self, mesg):
        self.fire('core:sync', mesg=mesg)

    def _actSyncTufoAdd(self, mesg):
        self.formTufoByTufo( mesg[1].get('tufo') )

    def _actSyncTufoDel(self, mesg):
        tufo = mesg[1].get('tufo')

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        tufo = self.getTufoByProp(form,valu=valu)
        if tufo == None:
            return

        self.delTufo(tufo)

    def _actSyncTufoTagAdd(self, mesg):

        tag = mesg[1].get('tag')
        tufo = mesg[1].get('tufo')
        asof = mesg[1].get('asof')

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        tufo = self.formTufoByProp(form,valu=valu)
        self.addTufoTag(tufo,tag,asof=asof)

    def _actSyncTufoTagDel(self, mesg):
        tag = mesg[1].get('tag')
        tufo = mesg[1].get('tufo')

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        tufo = self.formTufoByProp(form,valu=valu)
        self.delTufoTag(tufo,tag)

    #def _onAddSynForm(self, mesg):
        #pass

    #def _onAddSynType(self, mesg):
        #pass

    #def _onAddSynProp(self, mesg):
        #pass

    def syncs(self, msgs):
        '''
        Sync all core:sync events in a given list.
        '''
        [ self.sync(m) for m in msgs ]

    def sync(self, mesg):
        '''
        Feed the cortex a sync event to ingest changes from another.

        Example:

            core0.on('core:sync', core1.sync )

            # model changes to core0 will populate in core1

        '''
        self.syncact.react( mesg[1].get('mesg') )

    def _onDelSynTag(self, mesg):
        # deleting a tag.  delete all sub tags and wipe tufos.
        tufo = mesg[1].get('tufo')
        valu = tufo[1].get('syn:tag')

        [ self.delTufo(t) for t in self.getTufosByProp('syn:tag:up',valu) ]

        # do the (possibly very heavy) removal of the tag from all known forms.
        for form in self.getTufoForms():
            [ self.delTufoTag(t,valu) for t in self.getTufosByTag(form,valu) ]

    def _onAddSynProp(self, mesg):
        pass

    def _onAddSynType(self, mesg):
        pass

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

    def setSaveFd(self, fd, load=True, fini=False):
        '''
        Set a save fd for the cortex and optionally load.

        Example:

            core.setSaveFd(fd)

        '''
        if load:
            for mesg in msgpackfd(fd):
                self.loadbus.dist(mesg)

        self.onfini( fd.flush )
        if fini:
            self.onfini( fd.close )

        def savemesg(mesg):
            fd.write( msgenpack(mesg) )

        self.savebus.link(savemesg)

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

    def getTufosBy(self, name, prop, valu, limit=None):
        '''
        Retrieve tufos by either a specialized method or the lower getRowsBy api
        Specialized methods will be dependant on the storage backing and the data indexed

        Example:

            tufos = core.getTufosBy('in', 'foo', (47,3,8,22))

        '''
        meth = self.tufosbymeths.get(name)

        if not meth:
            rows = self.getRowsBy(name,prop,valu,limit=limit)
            return [ self.getTufoById(row[0]) for row in rows ]

        return meth(prop, valu, limit=limit)

    def getRowsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve rows by a specialized index within the cortex.

        Example:

            rows = core.getRowsBy('range','foo:bar',(20,30))

        Notes:
            * most commonly used to facilitate range searches

        '''
        meth = self._reqRowsByMeth(name)
        return meth(prop,valu,limit=limit)

    def getSizeBy(self, name, prop, valu, limit=None):
        '''
        Retrieve row count by a specialized index within the cortex.

        Example:

            size = core.getSizeBy('range','foo:bar',(20,30))
            print('there are %d rows where 20 <= foo < 30 ' % (size,))

        '''
        meth = self._reqSizeByMeth(name)
        return meth(prop,valu,limit=limit)

    def initTufosBy(self, name, meth):
        '''
        Initialize a "tufos by" handler for the Cortex.  This is useful
        when the index or storage backing can optimize tufo creation from
        raw rows.

        Example:
            def getbyin(prop,valus,limit=None):
                ret = []

                for valu in valus:
                    res = self.getTufosByProp(prop, valu=valu, limit=limit)
                    ret.extend(res)

                    if limit != None:
                        limit -= len(res)
                        if limit <= 0:
                            break

                return ret

            core.initTufos('in',getbyin)

        Notes:
            * Used by Cortex implementers to facilitate getTufosBy(...)
        '''
        self.tufosbymeths[name] = meth

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

    def _rowsToTufos(self, rows):
        res = collections.defaultdict(dict)
        [ res[i].__setitem__(p,v) for (i,p,v,t) in rows ]
        return list(res.items())

    def getTufosByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a list of tufos by property.

        Example:

            for tufo in core.getTufosByProp('foo:bar', 10):
                dostuff(tufo)

        '''
        rows = self.getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)

        return self._rowsToTufos(rows)

    def getTufosByPropType(self, name, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return tufos by interrogating the data model to find fields of the given type.

        Example:

            # return all tufos with an inet:email type property with value foo@bar.com

            for tufo in core.getTufosByPropType('inet:email', valu='foo@bar.com'):
                dostuff(tufo)

        '''
        ret = []

        for prop,info in self.propsbytype.get(name,()):

            pres = self.getTufosByProp(prop,valu=valu, mintime=mintime, maxtime=maxtime, limit=limit)
            ret.extend(pres)

            if limit != None:
                limit -= len(pres)
                if limit <= 0:
                    break

        return ret

    def _genTufoTag(self, tag):
        if not self.tagcache.get(tag):
            self.formTufoByProp('syn:tag',tag)
            self.tagcache[tag] = True

    def addTufoTag(self, tufo, tag, asof=None):
        '''
        Add a tag to a tufo.

        Example:

            tufo = core.formTufoByProp('foo','bar')
            core.addTufoTag(tufo,'baz.faz')

        '''
        self._genTufoTag(tag)
        rows = s_tags.genTufoRows(tufo,tag,valu=asof)
        if rows:
            self.addRows(map(lambda tup: tup[1], rows))
            for subtag,(i,p,v,t) in rows:
                tufo[1][p] = v
                self.fire('tufo:tag:add', tufo=tufo, tag=subtag, asof=asof)

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
        if props:
            [ self.delRowsByIdProp(iden,prop) for prop in props ]
            for p in props:
                if p in tufo[1]:
                    tufo[1].pop(p)
                    self.fire('tufo:tag:del', tufo=tufo, tag=s_tags.choptag(p))

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
            valu = self.getPropNorm(prop,val)

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
                props = [ (p,self.getPropNorm(p,v)) for (p,v) in props ]

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
        props = []

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
                [ todo.append((path,valu)) for valu in item ]
                continue

            if itype == dict:
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

                # sneaky ephemeral/hidden prop to identify newly created tufos
                props['.new'] = True
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
        prelen = len(prefix)
        props = { k[prelen:]:v for (k,v) in tufo[1].items() if k.startswith(prefix) }

        return self.formTufoByProp(form,valu,**props)

    def formTufoByProp(self, form, valu, **props):
        '''
        Form an (iden,info) tuple by atomically deconflicting
        the existance of prop=valu and creating it if not present.

        Example:

            tufo = core.formTufoByProp('fqdn','woot.com')

        Notes:

            * this will trigger an 'tufo:add' event if the
              tufo does not yet exist and is being construted.

        '''
        valu,subs = self.getPropChop(form,valu)

        with self.lock:
            tufo = self.getTufoByProp(form,valu=valu)
            if tufo != None:
                return tufo

            iden = guid()
            stamp = int(time.time())

            props.update(subs)

            props = self._normTufoProps(form,props)
            props[form] = valu

            self.fire('tufo:form', form=form, valu=valu, props=props)
            self.fire('tufo:form:%s' % form, form=form, valu=valu, props=props)

            rows = [ (iden,p,v,stamp) for (p,v) in props.items() ]

            self.addRows(rows)

            tufo = (iden,props)

        self.fire('tufo:add', tufo=tufo)
        self.fire('tufo:add:%s' % form, tufo=tufo)

        tufo[1]['.new'] = True
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
        valu = self.getPropNorm(form,valu)

        item = self.getTufoByProp(form,valu)
        if item != None:
            self.delTufo(item)

        return item

    def delTufosByProp(self, prop, valu=None):
        '''
        Delete multiple tufos by a single property.

        Example:

            core.delTufosByProp('foo:bar',valu=10)

        '''
        for item in self.getTufosByProp(prop,valu=valu):
            self.delTufo(item)

    def popTufosByProp(self, prop, valu=None):
        '''
        Delete and return multiple tufos by a property.

        Example:

            items = core.popTufosByProp('foo:bar',valu=10)

        '''
        items = self.getTufosByProp(prop,valu=valu)
        for item in items:
            self.delTufo(item)
        return items

    def _normTufoProps(self, form, inprops):

        props = {'tufo:form':form}

        for name,valu in inprops.items():
            prop = '%s:%s' % (form,name)

            if not self._okSetProp(prop):
                continue

            # do we have a DataType to normalize and carve sub props?
            valu,subs = self.getPropChop(prop,valu)

            # any sub-properties to populate?
            for sname,svalu in subs.items():

                subprop = '%s:%s' % (prop,sname)
                if self.getPropDef(subprop) == None:
                    continue

                props[subprop] = svalu

            props[prop] = valu

        for prop,valu in self.getFormDefs(form):
            props.setdefault(prop,valu)

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

    def _okSetProp(self, prop):
        # check for enforcement and validity of a full prop name
        if not self.enforce:
            return True

        return self.getPropDef(prop) != None

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
        props = { p:self.getPropNorm(p,v,oldval=tufo[1].get(p)) for (p,v) in props.items() if self._okSetProp(p) }

        # FIXME handle subprops here?

        tid = tufo[0]

        props = { p:v for (p,v) in props.items() if tufo[1].get(p) != v }

        if props:
            self.fire('tufo:set', tufo=tufo, props=props)
            self.fire('tufo:props:%s' % (form,), tufo=tufo, props=props)

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

    def incTufoProp(self, tufo, prop, incval=1):
        '''
        Atomically increment/decrement the value of a given tufo property.

        Example:

            tufo = core.incTufoProp(tufo,prop)

        '''
        form = tufo[1].get('tufo:form')
        prop = '%s:%s' % (form,prop)

        if not self._okSetProp(prop):
            return tufo

        return self._incTufoProp(tufo,prop,incval=incval)

    def _incTufoProp(self, tufo, prop, incval=1):

        # to allow storage layer optimization
        iden = tufo[0]

        with self.inclock:
            rows = self._getRowsByIdProp(iden,prop)
            if len(rows) == 0:
                raise NoSuchTufo(repr(tufo))

            oldv = rows[0][2]
            valu = oldv + incval

            self._setRowsByIdProp(iden,prop,valu)

            tufo[1][prop] = valu
            self.fire('tufo:set:%s' % (prop,), tufo=tufo, prop=prop, valu=valu, oldv=oldv)

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

