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

import synapse.lib.tags as s_tags
import synapse.lib.types as s_types

from synapse.common import *

hexre = re.compile('^[0-9a-z]+$')
propre = re.compile('^[0-9a-zA-Z:_]+$')

def propdef(name, **info):
    return (name,info)

tlib = s_types.TypeLib()
def getTypeRepr(name, valu):
    '''
    '''
    return tlib.reqDataType(name).repr(valu)

def getTypeNorm(name, valu):
    '''
    '''
    return tlib.reqDataType(name).norm(valu)

def getTypeParse(name, text):
    '''
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
                args = [ getTypeParse(atypes[i],args[i]) for i in range(len(args)) ]
                kwargs = { k:getTypeParse(kwtypes[k],v) for (k,v) in kwargs.items() }

            except IndexError as e:
                raise Exception('parsetypes() too many args in: %s' % (f.__name__,))

            except KeyError as e:
                raise Exception('parsetypes() no such kwtype in: %s' % (f.__name__,))

            return f(self, *args, **kwargs)

        functools.update_wrapper(runfunc,f)
        return runfunc

    return wrapfunc

class DataModel(s_types.TypeLib):

    def __init__(self):
        s_types.TypeLib.__init__(self)

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

        info['form'] = form
        fullprop = '%s:%s' % (form,prop)

        if not propre.match(fullprop):
            raise BadPropName(name=fullprop)

        self.addPropDef(fullprop, **info)

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
        defval = info.get('defval')

        if defval != None:
            self.defvals[form].append( (prop,defval) )

        pdef = (prop,info)

        ptype = info.get('ptype')
        if ptype != None:
            self.reqDataType(ptype)
            self.propsbytype[ptype].append(pdef)

        self.props[ prop ] = pdef
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

    def addTufoGlob(self, form, glob, **propinfo):
        '''
        Add a property to the given tufo form.
        '''
        glob = '%s:%s' % (form,glob)
        propinfo['form'] = form
        return self.addPropGlob(glob, **propinfo)

    def addPropGlob(self, glob, **info):
        '''
        Add a property glob to the data model.
        '''
        self.globs.append( (glob,info) )
        self.model['globs'][glob] = info

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

    def getPropType(self, prop):
        '''
        Retrieve the DataType instance for the given property.

        Example:

            dtype = modl.getPropType('foo:bar')

        '''
        pdef = self.getPropDef(prop)
        if pdef == None:
            return None

        ptype = pdef[1].get('ptype')
        if ptype == None:
            return None

        return self.getDataType(ptype)

    def getPropNorm(self, prop, valu, oldval=None):
        '''
        Return a normalized system mode value for the given property.

        Example:

            valu = model.getPropNorm(prop,valu)

        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return valu

        return dtype.norm(valu,oldval=oldval)

    def getPropChop(self, prop, valu):
        '''
        Return norm,{'sub':subval} tuple for the given property.
        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return valu,{}

        return dtype.chop(valu)

    #def getPropNorms(self, props):
        #return { p:self.getPropNorm(p,v) for (p,v) in props.items() }

    def getPropParse(self, prop, valu):
        '''
        Parse a humon input string into a system mode property value.

        Example:

            valu = model.getPropParse(prop, text)

        '''
        dtype = self.getPropType(prop)
        if dtype == None:
            return valu

        return dtype.parse(valu)

    def getParseProps(self, props):
        return { p:self.getPropParse(p,v) for (p,v) in props.items() }

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
