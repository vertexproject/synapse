from __future__ import absolute_import,unicode_literals
'''
An API to assist with the creation and enforcement of cortex data models.
'''
import re
import time
import socket
import struct
import fnmatch
import datetime
import functools
import collections
import logging

import synapse.lib.tags as s_tags
import synapse.lib.types as s_types

from synapse.common import *

logger = logging.getLogger(__name__)

hexre = re.compile('^[0-9a-z]+$')
propre = re.compile('^[0-9a-z:_]+$')

tlib = s_types.TypeLib()
def getTypeRepr(name, valu):
    '''
    Return the humon readable form of the given type value.
    '''
    return tlib.reqDataType(name).repr(valu)

def getTypeNorm(name, valu):
    '''
    Normalize a type specific value in system mode.
    '''
    return tlib.reqDataType(name).norm(valu)

def getTypeParse(name, text):
    '''
    Parse input text for the given type into it's system form.
    '''
    return tlib.reqDataType(name).parse(text)

def parsetypes(*atypes, **kwtypes):
    '''
    Decorator to parse input args from humon to system values.

    Example:

        class Woot:

            @parsetypes('int','hash:md5')
            def getFooBar(self, size, md5):
                # size will be an int and md5 will be lower
                dostuff()

        woot = Woot()

        # call with user input strings...
        woot.getFooBar('20','0a0a0a0a0B0B0B0B0c0c0c0c0D0D0D0D')

    '''
    #typeargs = [ basetypes.get(a) for a in atypes ]
    #typekwargs = { k:basetypes.get(v) for (k,v) in kwtypes.items() }

    def wrapfunc(f):

        def runfunc(self, *args, **kwargs):

            try:
                args = [ getTypeParse(atypes[i],args[i])[0] for i in range(len(args)) ]
                kwargs = { k:getTypeParse(kwtypes[k],v)[0] for (k,v) in kwargs.items() }

            except IndexError as e:
                raise Exception('parsetypes() too many args in: %s' % (f.__name__,))

            except KeyError as e:
                raise Exception('parsetypes() no such kwtype in: %s' % (f.__name__,))

            return f(self, *args, **kwargs)

        functools.update_wrapper(runfunc,f)
        return runfunc

    return wrapfunc

class DataModel(s_types.TypeLib):

    def __init__(self,load=True):
        self.props = {}
        self.forms = set()

        self.defvals = collections.defaultdict(list)
        self.subprops = collections.defaultdict(list)
        self.propsbytype = collections.defaultdict(list)

        self.globs = []
        self.cache = {} # for globs
        self.model = {
            'ver':(0,0,0),
            'enums':{},
            'props':{},
            'globs':{},
            'forms':[],
        }

        s_types.TypeLib.__init__(self,load=load)

        self.addTufoForm('syn:core')

        self.addTufoForm('syn:form',ptype='syn:prop')
        self.addTufoProp('syn:form','doc', ptype='str', doc='basic form definition')
        self.addTufoProp('syn:form','ver', ptype='int', doc='form version within the model')
        self.addTufoProp('syn:form','model', ptype='str', doc='which model defines a given form')

        self.addTufoForm('syn:prop',ptype='syn:prop')
        self.addTufoProp('syn:prop','doc',ptype='str',req=1,doc='Description of the property definition')
        self.addTufoProp('syn:prop','form',ptype='syn:prop',req=1,doc='Synapse form which contains this property')
        self.addTufoProp('syn:prop','ptype',ptype='syn:type',req=1,doc='Synapse type for this field')
        self.addTufoProp('syn:prop','req',ptype='bool',defval=0,doc='Set to 1 if this property is required')
        self.addTufoProp('syn:prop','glob',ptype='bool',defval=0,doc='Set to 1 if this property defines a glob')
        self.addTufoProp('syn:prop','defval',doc='Set to the default value for this property')

        self.addTufoForm('syn:tag', ptype='syn:tag')
        self.addTufoProp('syn:tag','up',ptype='syn:tag')
        self.addTufoProp('syn:tag','doc',defval='',ptype='str')
        self.addTufoProp('syn:tag','depth',defval=0,ptype='int')
        self.addTufoProp('syn:tag','title',defval='',ptype='str')
        self.addTufoProp('syn:tag', 'base', ptype='str', ro=1)

        self.addType('syn:tagform', subof='comp', fields='tag,syn:tag|form,syn:prop', ex="(foo.bar,baz:faz)")

        self.addTufoForm('syn:tagform', ptype='syn:tagform', fields='tag,syn:tag|form,syn:prop')
        self.addTufoProp('syn:tagform', 'tag', ptype='syn:tag', ro=1, doc='The tag being documented')
        self.addTufoProp('syn:tagform', 'form', ptype='syn:prop', ro=1, doc='The the form that the tag applies to.')

        self.addTufoProp('syn:tagform', 'doc', ptype='str:txt', defval='??', doc='The long form description for what the tag means on the given node form')
        self.addTufoProp('syn:tagform', 'title', ptype='str:txt', defval='??', doc='The short name for what the tag means on the given node form')

        self.addTufoForm('syn:model',ptype='syn:tag', doc='prefix for all forms within the model')
        self.addTufoProp('syn:model','hash', ptype='guid', doc='version hash for the current model')
        self.addTufoProp('syn:model','prefix', ptype='syn:prop', doc='prefix used by types/forms in the model')

        self.addTufoForm('syn:type',ptype='syn:type')
        self.addTufoProp('syn:type','*',glob=1)

        # used most commonly for sequential tag generation
        self.addTufoForm('syn:seq',ptype='str:lwr',doc='A sequential id generation tracker')
        self.addTufoProp('syn:seq','width', ptype='int', defval=0, doc='How many digits to use to represent the number')
        self.addTufoProp('syn:seq','nextvalu', ptype='int', defval=0, doc='The next sequential value')

    def getModelDict(self):
        '''
        Returns a dictionary which represents the data model.
        '''
        return dict(self.model)

    def addTufoForm(self, form, **info):
        '''
        Add a tufo form to the data model

        Example:

            # must add tufo before adding tufo props
            model.addTufoForm('woot')

        '''
        if not propre.match(form):
            raise BadPropName(name=form)

        self.forms.add(form)

        info['form'] = form
        self.model['forms'].append(form)
        return self.addPropDef(form, **info)

    def isTufoForm(self, name):
        '''
        Returns True if the given name is a form.
        '''
        return name in self.forms

    def getTufoForms(self):
        '''
        Return a list of the tufo forms.
        '''
        return list(self.forms)

    def addTufoProp(self, form, prop, **info):
        '''
        Add a property to the data model.

        Example:

            # all foo tufos must have a foo:bar property
            model.addTufoProp('foo', 'bar', ptype='int', defval=0)

        '''
        pdef = self.getPropDef(form)
        if pdef == None:
            raise NoSuchForm(name=form)

        if info.get('glob'):
            self._addPropGlob(form,prop,**info)
            return

        info['form'] = form
        fullprop = '%s:%s' % (form,prop)

        if not propre.match(fullprop):
            raise BadPropName(name=fullprop)

        self.addPropDef(fullprop, **info)

    def getPropFormBase(self, prop):
        '''
        Return a form,base tuple for the name parts of a given property.

        Example:

        Args:
            prop (str): The fully qualified property name

        Returns:
            ((str,str)):  The (form,base) name tuple for the prop.

        '''
        pdef = self.getPropDef(prop)
        if pdef == None:
            raise NoSuchProp(name=prop)

        return pdef[1].get('form'),pdef[1].get('base')

    def addPropDef(self, prop, **info):
        '''
        Add a property definition to the DataModel.

        Example:

            model.addPropDef('foo:bar', ptype='int', defval=30)

        '''
        if self.props.get(prop) != None:
            raise DupPropName(name=prop)

        info.setdefault('doc',None)
        info.setdefault('uniq',False)
        info.setdefault('ptype',None)
        info.setdefault('title',None)
        info.setdefault('defval',None)

        form = info.get('form')
        base = prop[len(form)+1:]

        info['base'] = base

        defval = info.get('defval')

        if defval != None:
            self.defvals[form].append( (prop,defval) )

        pdef = (prop,info)

        ptype = info.get('ptype')
        if ptype != None:
            self.reqDataType(ptype)
            self.propsbytype[ptype].append(pdef)

        self.props[ prop ] = pdef
        self.props[ (form,base) ] = pdef

        self.model['props'][prop] = pdef

        self._addSubRefs(pdef)

    def getFormDefs(self, form):
        '''
        Return a list of (prop,valu) tuples for the default values of a form.
        '''
        return self.defvals.get(form,())

    def _addSubRefs(self, pdef):
        name = pdef[0]
        for prop in s_tags.iterTagUp(pdef[0],div=':'):
            if prop == pdef[0]:
                continue
            self.subprops[prop].append(pdef)

    def getPropsByType(self, name):
        '''
        Return a list of prop def tuples (name,info) for all props of the given type.

        Example:

            for prop,info in modl.getPropsByType('guid'):
                dostuff()

        '''
        return self.propsbytype.get(name,())

    def _addPropGlob(self, form, prop, **info):
        prop = '%s:%s' % (form,prop)
        info['form'] = form
        self.globs.append( (prop,info) )

    def getSubProps(self, prop):
        '''
        Return a list of (name,info) prop defs for all sub props.

        Example:

            for pdef in model.getSubProps('foo:bar'):
                dostuff(pdef)

        '''
        return self.subprops.get(prop,())

    def getSubPropDefs(self, prop):
        '''
        Return a dict of defvals for props under prop.
        '''
        ret = {}
        for pdef in self.getSubProps(prop):
            valu = pdef[1].get('defval')
            if valu == None:
                continue

            ret[ pdef[0] ] = valu

        return ret

    def getPropRepr(self, prop, valu):
        '''
        Return the humon readable representation for a property.

        Example:
            valu = tufo[1].get(prop)
            x = model.getPropRepr(prop, valu)

        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return str(valu)

        return dtype.repr(valu)

    def getPropTypeName(self, prop):
        pdef = self.getPropDef(prop)
        if pdef == None:
            return None

        return pdef[1].get('ptype')

    def getPropNorm(self, prop, valu, oldval=None):
        '''
        Return a normalized system mode value for the given property.

        Example:

            valu,subs = model.getPropNorm(prop,valu)

        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return valu,{}

        return dtype.norm(valu,oldval=oldval)

    def getPropParse(self, prop, valu):
        '''
        Parse a humon input string into a system mode property value.

        Example:

            valu,subs = model.getPropParse(prop, text)

        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return valu

        return dtype.parse(valu)

    def getPropDef(self, prop, glob=True):
        '''
        Return a property definition tufo by property name.

        Example:

            pdef = model.getPropDef('foo:bar')

        '''
        pdef = self.props.get(prop)
        if pdef != None:
            return pdef

        if not glob:
            return None

        # check the cache
        pdef = self.cache.get(prop)
        if pdef != None:
            return pdef

        # no match, lets check the globs...
        for glob,pinfo in self.globs:
            if fnmatch.fnmatch(prop,glob):
                pdef = (prop,dict(pinfo))
                self.cache[prop] = pdef
                return pdef

    def getPropType(self, prop):
        '''
        Return the data model type instance for the given property,
         or None if the data model doesn't have an entry for the property.

        Example:
            ptype = model.getPropType('foo:bar')
        '''
        pdef = self.getPropDef(prop)
        if pdef == None:
            return None

        return self.getDataType( pdef[1].get('ptype') )

    def getPropInfo(self, prop, name):
        '''
        A helper function to resolve a prop info from either the
        property itself or the first type it inherits from which
        contains the info.

        Example:

            ex = modl.getPropInfo('inet:dns:a:fqdn','ex')

        '''
        pdef = self.getPropDef(prop)
        if pdef == None:
            return None

        valu = pdef[1].get(name)
        if valu != None:
            return valu

        ptype = pdef[1].get('ptype')
        if ptype == None:
            return None

        return self.getTypeInfo(ptype,name)
