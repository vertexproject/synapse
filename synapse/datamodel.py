'''
An API to assist with the creation and enforcement of cortex data models.
'''
import fnmatch
import functools
import collections
import logging

import regex

import synapse.common as s_common

import synapse.lib.tags as s_tags
import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')
propre = regex.compile('^[0-9a-z:_]+$')

tlib = s_types.TypeLib()

def rebuildTlib():
    '''
    Rebuild the datamodel's global TypeLib instance.

    The datamodel.py module maintains a instance of the TypeLib object.  If there are new models dynamically loaded
    into Synapse, this can be used to rebuild the TypeLib object with those additions.

    Returns:
        (None): Returns None.
    '''
    global tlib
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
                args = [getTypeParse(atypes[i], args[i])[0] for i in range(len(args))]
                kwargs = {k: getTypeParse(kwtypes[k], v)[0] for (k, v) in kwargs.items()}

            except IndexError as e:
                raise Exception('parsetypes() too many args in: %s' % (f.__name__,))

            except KeyError as e:
                raise Exception('parsetypes() no such kwtype in: %s' % (f.__name__,))

            return f(self, *args, **kwargs)

        functools.update_wrapper(runfunc, f)
        return runfunc

    return wrapfunc

class DataModel(s_types.TypeLib):

    def __init__(self, load=True):
        self.props = {}
        self.forms = set()

        self.reqprops = collections.defaultdict(list)
        self.defvals = collections.defaultdict(list)
        self.subprops = collections.defaultdict(list)
        self.propsbytype = collections.defaultdict(list)
        self.propsdtyp = {}
        self.uniprops = set()
        self.unipropsreq = set()

        self._type_hooks = collections.defaultdict(list)

        self.globs = []
        self.cache = {} # for globs
        self.model = {
            'ver': (0, 0, 0),
            'enums': {},
            'props': {},
            'globs': {},
            'forms': [],
        }

        s_types.TypeLib.__init__(self, load=load)
        self._initUniversalProps()

    def _initUniversalProps(self):
        '''
        Initialize universal properties in the DataModel.
        These properties are not bound to a specific form and may be present on a node.
        '''
        self.addPropDef('tufo:form',
                        ptype='str',
                        doc='The form of the node',
                        ro=1,
                        req=1,
                        univ=1,
                        )
        self.addPropDef('node:created',
                        ptype='time',
                        doc='The time the node was created',
                        ro=1,
                        req=1,
                        univ=1,
                        )
        self.addPropDef('node:ndef',
                        ptype='ndef',
                        doc='The unique guid representing the combination of the node form and primary property.',
                        ro=1,
                        req=1,
                        univ=1)

    def getModelDict(self):
        '''
        Returns a dictionary which represents the data model.
        '''
        return dict(self.model)

    def _addDataModels(self, modtups):
        '''
        Load a list of (name,modl) tuples into the DataModel.
        '''
        # first load all the types...
        s_types.TypeLib._addDataModels(self, modtups)

        for name, modl in modtups:

            for form, info, props in modl.get('forms', ()):
                self.addTufoForm(form, **info)

                for prop, pnfo in props:
                    self.addTufoProp(form, prop, **pnfo)

    def addTufoForm(self, form, **info):
        '''
        Add a tufo form to the data model

        Example:

            # must add tufo before adding tufo props
            model.addTufoForm('woot')

        Raises:
            BadPropName: If the property name is poorly formed.
        '''
        if not propre.match(form):
            raise s_common.BadPropName(name=form)

        if info.get('ptype') is None:
            if self.isDataType(form):
                info['ptype'] = form
            else:
                info['ptype'] = 'str'

        self.forms.add(form)

        info['form'] = form
        self.model['forms'].append(form)
        return self.addPropDef(form, **info)

    def isTufoForm(self, name):
        '''
        Check if a form is a valid form.

        Args:
            name (str): Form to check

        Returns:
            bool: True if the form is a valid form. False otherwise.
        '''
        return name in self.forms

    def reqTufoForm(self, name):
        '''
        Check if a form is a valid form, raise an exception otherwise.

        Args:
            name (str): Form to check

        Raises:
            NoSuchForm: If the form does not exist in the datamodel.
        '''
        ret = self.isTufoForm(name)
        if not ret:
            raise s_common.NoSuchForm(name=name)

    def getTufoForms(self):
        '''
        Get a list of the currently loaded tufo forms.

        Returns:
            list: List of forms.
        '''
        return list(self.forms)

    def getUnivProps(self):
        '''
        Get a list of the universal tufo props.

        Returns:
            list: List of universal tufo props
        '''
        return list(self.uniprops)

    def addTufoProp(self, form, prop, **info):
        '''
        Add a property to the data model.

        Example:

            # all foo tufos must have a foo:bar property
            model.addTufoProp('foo', 'bar', ptype='int', defval=0)

        '''
        pdef = self.getPropDef(form)
        if pdef is None:
            raise s_common.NoSuchForm(name=form)

        if info.get('glob'):
            self._addPropGlob(form, prop, **info)
            return

        info['form'] = form
        fullprop = '%s:%s' % (form, prop)

        if not propre.match(fullprop):
            raise s_common.BadPropName(name=fullprop)

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
        if pdef is None:
            raise s_common.NoSuchProp(name=prop)

        return pdef[1].get('form'), pdef[1].get('base')

    def addPropDef(self, prop, **info):
        '''
        Add a property definition to the DataModel.

        Example:

            model.addPropDef('foo:bar', ptype='int', defval=30)

        Returns:
            ((str, dict)): Retuns the prop, property definition tuple.

        Raises:
            DupPropName: If the property name is already present in the data model.
            BadPropConf: If the propety has an invalid configuration.
        '''
        if self.props.get(prop) is not None:
            raise s_common.DupPropName(name=prop)

        info.setdefault('ptype', None)
        info.setdefault('doc', self.getTypeInfo(info.get('ptype'), 'doc', ''))
        info.setdefault('req', False)
        info.setdefault('title', self.getTypeInfo(info.get('ptype'), 'title', ''))
        info.setdefault('defval', None)
        info.setdefault('univ', False)

        univ = info.get('univ')
        form = info.get('form')
        if form and univ:
            raise s_common.BadPropConf(mesg='Universal props cannot be set on forms.',
                                       prop=prop, form=form,)
        relname = None
        if form:
            relname = prop[len(form) + 1:]
            if relname:
                info['relname'] = relname

        if ':' in prop:
            _, base = prop.rsplit(':', 1)
            info.setdefault('base', base)

        defval = info.get('defval')

        if defval is not None:
            self.defvals[form].append((prop, defval))

        req = info.get('req')
        if req:
            self.reqprops[form].append(prop)

        pdef = (prop, info)

        ptype = info.get('ptype')
        if ptype is not None:
            dtyp = self.reqDataType(ptype)
            pdtyp = dtyp.extend(dtyp.name, prop=prop)
            self.propsbytype[ptype].append(pdef)
            self.propsdtyp[prop] = pdtyp

        self.props[prop] = pdef
        if relname:
            self.props[(form, relname)] = pdef

        self.model['props'][prop] = pdef

        if univ:
            self.uniprops.add(prop)
            if info.get('req'):
                self.unipropsreq.add(prop)

        self._addSubRefs(pdef)

        if ptype is not None:
            for func in self._type_hooks.get(ptype, ()):
                func(pdef)

        return pdef

    def addPropTypeHook(self, name, func):
        '''
        Add a callback function for props declared from a given type.

        Args:
            name (str): The name of a type to hook props
            func (function): A function callback

        Example:
            def func(pdef):
                dostuff(pdef)

            modl.addPropTypeHook('foo:bar', func)

        NOTE: This will be called immediately for existing props and
              incrementally as future props are declared using the type.
        '''
        for pdef in self.propsbytype.get(name, ()):
            func(pdef)

        self._type_hooks[name].append(func)

    def getFormDefs(self, form):
        '''
        Return a list of (prop,valu) tuples for the default values of a form.
        '''
        return self.defvals.get(form, ())

    def getFormReqs(self, form):
        '''
        Return a list of prop values which are required form a form.

        Args:
            form (str): Form to request values for.

        Returns:
            list: List of required properties needed for making the given form.
        '''
        return self.reqprops.get(form, ())

    def _addSubRefs(self, pdef):
        name = pdef[0]
        for prop in s_tags.iterTagUp(pdef[0], div=':'):
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
        return self.propsbytype.get(name, ())

    def _addPropGlob(self, form, prop, **info):
        prop = '%s:%s' % (form, prop)
        info['form'] = form
        self.globs.append((prop, info))

    def getSubProps(self, prop):
        '''
        Return a list of (name,info) prop defs for all sub props.

        Example:

            for pdef in model.getSubProps('foo:bar'):
                dostuff(pdef)

        '''
        return self.subprops.get(prop, ())

    def getSubPropDefs(self, prop):
        '''
        Return a dict of defvals for props under prop.
        '''
        ret = {}
        for pdef in self.getSubProps(prop):
            valu = pdef[1].get('defval')
            if valu is None:
                continue

            ret[pdef[0]] = valu

        return ret

    def getPropRepr(self, prop, valu):
        '''
        Return the humon readable representation for a property.

        Example:
            valu = tufo[1].get(prop)
            x = model.getPropRepr(prop, valu)

        '''
        dtype = self.getPropType(prop)
        if dtype is None:
            return str(valu)

        return dtype.repr(valu)

    def getPropTypeName(self, prop):
        '''
        Retrieve the name of the type for the given property.

        Args:
            prop (str): The property

        Returns:
            (str):  The type name (or None)
        '''
        pdef = self.getPropDef(prop)
        if pdef is None:
            return None

        return pdef[1].get('ptype')

    def getTypeOfs(self, name):
        '''
        Return a list of type inheritence (including specified name).

        Args:
            name (str): The name of a type

        Returns:
            ([str, ...]):   The list of type names it inherits from
        '''
        retn = []
        while name is not None:
            retn.append(name)
            name = self.getTypeInfo(name, 'subof')
        return retn

    def getPropNorm(self, prop, valu, oldval=None):
        '''
        Return a normalized system mode value for the given property.

        Args:
            prop (str): Property to normalize.
            valu: Input value to normalize.
            oldval: Optional previous version of the value.

        Examples:
            Normalize an IPV4 address::

                valu, subs = model.getPropNorm('inet:ipv4', '1.2.3.4')
                # valu = 16909060

            Normalize a DNS A record::

                valu, subs = model.getPropNorm('inet:dns:a', 'woot.com/1.2.3.4')
                # valu = 'woot.com/1.2.3.4'
                # subs['fqdn'] = 'woot.com'
                # subs['fqdn:domain'] = 'com'
                # subs['fqdn:host'] = 'woot'
                # subs['ipv4'] = 16909060

        Notes:
            If the requested property is not part of the data model, this returns the input valu. If this is not
            desired behavior, the reqPropNorm() function can be used to throw a NoSuchProp exception.

        Returns:
            tuple: A tuple of two items. The first item is the system normalized valu, as an integer or string. The
                   second item is a dictionary of subproperties for the input.
        '''
        dtype = self.getPropType(prop)
        if dtype is None:
            return valu, {}

        return dtype.norm(valu, oldval=oldval)

    def getPropParse(self, prop, valu):
        '''
        Parse a humon input string into a system mode property value.

        Example:

            valu,subs = model.getPropParse(prop, text)

        '''
        dtype = self.getPropType(prop)
        if dtype is None:
            return valu

        return dtype.parse(valu)

    def getPropDef(self, prop, glob=True):
        '''
        Return a property definition tufo by property name.

        Example:

            pdef = model.getPropDef('foo:bar')

        '''
        pdef = self.props.get(prop)
        if pdef is not None:
            return pdef

        if not glob:
            return None

        # check the cache
        pdef = self.cache.get(prop)
        if pdef is not None:
            return pdef

        # no match, lets check the globs...
        for glob, pinfo in self.globs:
            if fnmatch.fnmatch(prop, glob):
                pdef = (prop, dict(pinfo))
                self.cache[prop] = pdef
                return pdef

    def getPropType(self, prop):
        '''
        Return the data model type instance for the given property, or
        None if the data model doesn't have an entry for the property.

        Args:
            prop (str): Property to get the DataType instance for.

        Returns:
            s_types.DataType: A DataType for a given property.
        '''

        # Default to pulling dtype from the propsdtyp dict
        dtyp = self.propsdtyp.get(prop)
        if dtyp:
            return dtyp

        # Otherwise, fall back on getPropDef/getDataType methods.
        pdef = self.getPropDef(prop)
        if pdef is None:
            return None

        return self.getDataType(pdef[1].get('ptype'))

    def getPropInfo(self, prop, name):
        '''
        A helper function to resolve a prop info from either the
        property itself or the first type it inherits from which
        contains the info.

        Example:

            ex = modl.getPropInfo('inet:dns:a:fqdn','ex')

        '''
        pdef = self.getPropDef(prop)
        if pdef is None:
            return None

        valu = pdef[1].get(name)
        if valu is not None:
            return valu

        ptype = pdef[1].get('ptype')
        if ptype is None:
            return None

        return self.getTypeInfo(ptype, name)

    def reqPropNorm(self, prop, valu, oldval=None):
        '''
        Return a normalized system mode value for the given property. This throws an exception if the property does
        not exist.

        Args:
            prop (str): Property to normalize.
            valu: Input value to normalize.
            oldval: Optional previous version of the value.

        Examples:
            Normalize an IPV4 address::

                valu, subs = model.reqPropNorm('inet:ipv4', '1.2.3.4')
                # valu = 16909060

            Normalize a DNS A record::

                valu, subs = model.reqPropNorm('inet:dns:a', 'woot.com/1.2.3.4')
                # valu = 'woot.com/1.2.3.4'
                # subs['fqdn'] = 'woot.com'
                # subs['fqdn:domain'] = 'com'
                # subs['fqdn:host'] = 'woot'
                # subs['ipv4'] = 16909060

        Notes:
            This is similar to the getPropNorm() function, however it throws an exception on a missing property
            instead of returning the valu to the caller.

        Returns:
            tuple: A tuple of two items. The first item is the system normalized valu, as an integer or string. The
                   second item is a dictionary of subproperties for the input.

        Raises:
            NoSuchProp: If the requested property is not part of the data model.
        '''
        dtype = self.getPropType(prop)
        if dtype is None:
            raise s_common.NoSuchProp(mesg='Prop does not exist.',
                                      prop=prop, valu=valu)

        return dtype.norm(valu, oldval=oldval)
