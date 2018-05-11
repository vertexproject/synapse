'''
An API to assist with the creation and enforcement of cortex data models.
'''
import regex
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps

import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')
propre = regex.compile('^[0-9a-z:_]+$')

import synapse.lib.types as s_types

class Prop:
    '''
    The Prop class represents a property defined within the data model.
    '''

    def __init__(self, modl, form, name, typedef, info):

        self.modl = modl
        self.name = name
        self.info = info

        self.form = form
        self.type = None

        self.storinfo = {
            'univ': name.startswith('.')
        }

        self.full = '%s:%s' % (form.name, name)

        self.onsets = []
        self.ondels = []

        self.utf8name = self.name.encode('utf8')
        self.utf8full = self.full.encode('utf8')

        self.pref = self.form.utf8name + b'\x00' + self.utf8name + b'\x00'

        self.type = self.modl.getTypeClone(typedef)

        self.form.props[name] = self

        self.modl.propsbytype[self.type.name].append(self)

        # if we have a defval, tell the form...
        defv = self.info.get('defval')
        if defv is not None:
            self.form.defvals[name] = defv

        # if we are required, tell the form...
        if self.info.get('req'):
            self.form.reqprops.append(self)

    def onSet(self, func):
        '''
        Add a callback for setting this property.

        The callback is executed after the property is set.

        Args:
            func (function): A prop set callback.

        The callback is called within the current transaction,
        with the node, and the old property value (or None).

        def func(node, oldv):
            dostuff()
        '''
        self.onsets.append(func)

    def onDel(self, func):
        '''
        Add a callback for deleting this property.

        The callback is executed after the property is deleted.

        Args:
            func (function): A prop del callback.

        The callback is called within the current transaction,
        with the node, and the old property value (or None).

        def func(node, oldv):
            dostuff()
        '''
        self.ondels.append(func)

    def wasSet(self, node, oldv):
        '''
        Fire the onset() handlers for this property.

        Args:
            node (synapse.lib.node.Node): The node whose property was set.
            oldv (obj): The previous value of the property.
        '''
        for func in self.onsets:
            try:
                func(node, oldv)
            except Exception as e:
                logger.exception('onset() error for %s' % (self.full,))

    def wasDel(self, node, oldv):
        for func in self.ondels:
            try:
                func(node, oldv)
            except Exception as e:
                logger.exception('ondel() error for %s' % (self.full,))

    def getLiftOps(self, valu, cmpr='='):

        if valu is None:
            iops = (('pref', b''),)
            return (
                ('indx', ('byprop', self.pref, iops)),
            )

        iops = self.type.getIndxOps(valu, cmpr=cmpr)
        return (
            ('indx', ('byprop', self.pref, iops)),
        )

    def getSetOps(self, buid, norm):
        indx = self.type.indx(norm)
        return (
            ('prop:set', (buid, self.form.name, self.name, norm, indx, self.storinfo)),
        )

    def getDelOps(self, buid):
        return (
            ('prop:del', (buid, self.form.name, self.name, self.storinfo)),
        )

    def filt(self, text, cmpr='='):
        '''
        Construct a filter function for nodes by property.
        '''
        typefilt = self.type().filt(text, cmpr=cmpr)
        if typefilt is None:
            return

        def func(node):
            valu = node[1]['props'].get(self._prop_name)
            return typefilt(valu)

        return func

class Univ:
    '''
    A property-like object that can lift without Form().
    '''
    def __init__(self, modl, name, typedef, propinfo):
        self.modl = modl
        self.name = name
        self.type = modl.getTypeClone(typedef)
        self.info = propinfo
        self.pref = name.encode('utf8') + b'\x00'

    def getLiftOps(self, valu, cmpr='='):

        if valu is None:
            iops = (
                ('pref', b''),
            )
        else:
            iops = self.type.getIndxOps(valu)

        return (
            ('indx', ('byuniv', self.pref, iops)),
        )

class Form:
    '''
    The Form class implements data model logic for a node form.
    '''
    def __init__(self, modl, name, info):

        self.modl = modl
        self.name = name
        self.info = info

        self.onadds = []

        self.type = modl.types.get(name)
        if self.type is None:
            raise s_exc.NoSuchType(name=name)

        self.type.form = self

        # pre-compute our byprop table prefix
        self.pref = name.encode('utf8') + b'\x00\x00'
        self.utf8name = name.encode('utf8')

        self.props = {}     # name: Prop()
        self.defvals = {}   # name: valu
        self.reqprops = []  # [ Prop(), ... ]

    def onAdd(self, func):
        '''
        Add a callback for adding this type of node.

        The callback is executed after node construction.

        Args:
            func (function): A node add callback.

        The callback is called with the current transaction
        and the new node.

        def func(xact, node):
            dostuff()
        '''
        self.onadds.append(func)

    def wasAdded(self, node):
        '''
        Fire the onAdd() callbacks for node creation.
        '''
        for func in self.onadds:
            try:
                func(node)
            except Exception as e:
                logger.exception('error on onadd for %s' % (self.name,))

    def getSetOps(self, buid, norm):
        indx = self.type.indx(norm)
        return (
            ('prop:set', (buid, self.name, '', norm, indx, {})),
        )

    def getDelOps(self, buid):
        return (
            ('prop:del', (buid, self.name, '', {})),
        )

    def getLiftOps(self, valu, cmpr='='):
        '''
        Get a set of lift operations for use with an Xact.
        '''
        if valu is None:
            iops = (('pref', b''),)
            return (
                ('indx', ('byprop', self.pref, iops)),
            )

        iops = self.type.getIndxOps(valu, cmpr=cmpr)
        return (
            ('indx', ('byprop', self.pref, iops)),
        )

    def prop(self, name):
        '''
        Return a secondary property for this form by relative prop name.

        Args:
            name (str): The relative property name.
        Returns:
            (synapse.datamodel.Prop): The property or None.
        '''
        return self.props.get(name)

class Model:
    '''
    The data model used by a Cortex hypergraph.
    '''
    def __init__(self):

        self.types = {} # name: Type()
        self.forms = {} # name: Form()
        self.props = {} # (form,name): Prop() and full: Prop()

        self.univs = (
            ('created', ('time', {}), {'ro': 1,
                'doc': 'The time the node was created in the cortex.',
            }),
        )

        self.propsbytype = collections.defaultdict(list) # name: Prop()

        self._type_pends = collections.defaultdict(list)

        # add the primitive base types
        info = {'doc': 'The base 64 bit signed integer type.', 'ex': 0}
        item = s_types.Int(self, 'int', info, {})
        self.addBaseType(item)

        info = {'doc': 'A base range type.'}
        item = s_types.Range(self, 'range', info, {'type': ('int', {})})
        self.addBaseType(item)

        info = {'doc': 'The base string type.', 'ex': 'a string'}
        item = s_types.Str(self, 'str', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base hex type.'}
        item = s_types.Hex(self, 'hex', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base boolean type.'}
        item = s_types.Bool(self, 'bool', info, {})
        self.addBaseType(item)

        info = {'doc': 'A date/time value.', 'ex': 0}
        item = s_types.Time(self, 'time', info, {})
        self.addBaseType(item)

        info = {'doc': 'A time window/interval.'}
        item = s_types.Ival(self, 'ival', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base GUID type.'}
        item = s_types.Guid(self, 'guid', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base type for a synapse tag.'}
        item = s_types.Tag(self, 'syn:tag', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base type for compound node fields.'}
        item = s_types.Comp(self, 'comp', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base geo political location type.'}
        item = s_types.Loc(self, 'loc', info, {})
        self.addBaseType(item)

        info = {'doc': 'The node definition type for a (form,valu) compound field.'}
        item = s_types.Ndef(self, 'ndef', info, {})
        self.addBaseType(item)

        info = {'doc': 'The nodeprop type for a (prop,valu) compound field.'}
        item = s_types.NodeProp(self, 'nodeprop', info, {})
        self.addBaseType(item)

        for name, typedef, propinfo in self.univs:
            name = '.' + name
            self.props[name] = Univ(self, name, typedef, propinfo)

    def _addTypeDecl(self, decl):

        typename, basename, typeopts, typeinfo = decl

        base = self.types.get(basename)
        if base is None:
            self._type_pends[typename].append(tdef)
            return

        item = base.extend(name, info, opts)
        self.types[name] = item

        pends = self._type_pends.pop(name, None)
        if pends is not None:
            for name, subof, info, opts in pends:
                self.types[name] = item.clone(name, info, opts)

    def getTypeClone(self, typedef):

        base = self.types.get(typedef[0])
        if base is None:
            raise s_exc.NoSuchType(name=typedef[0])

        return base.clone(typedef[1])

    def addDataModels(self, mods):
        '''
        Add a list of (name, mdef) tuples.

        A model definition (mdef) is structured as follows:

        {
            "ctors":(
                ('name', 'class.path.ctor', {}, {'doc': 'The foo thing.'}),
            ),

            "types":(
                ('name', ('basetype', {typeopts}), {info}),
            ),

            "forms":(
                (formname, (typename, typeopts), {info}, (
                    (propname, (typename, typeopts), {info}),
                )),
            ),
        }
        '''

        # load all the base type ctors in order...
        for modlname, mdef in mods:

            for name, ctor, opts, info in mdef.get('ctors', ()):
                item = s_dyndeps.tryDynFunc(ctor, self, name, opts, info)
                self.types[name] = item

        # load all the types in order...
        for modlname, mdef in mods:

            for typename, (basename, opts), info in mdef.get('types', ()):

                base = self.types.get(basename)
                if base is None:
                    raise s_exc.NoSuchType(name=basename)

                self.types[typename] = base.extend(typename, opts, info)

        # now we can load all the forms...
        for modlname, mdef in mods:

            for formname, forminfo, propdefs in mdef.get('forms', ()):

                _type = self.types.get(formname)
                if _type is None:
                    raise s_exc.NoSuchType(name=formname)

                form = Form(self, formname, forminfo)

                self.forms[formname] = form
                self.props[formname] = form

                for univname, typedef, univinfo in self.univs:

                    prop = Prop(self, form, '.' + univname, typedef, univinfo)

                    full = f'{formname}.{univname}'
                    self.props[full] = prop
                    self.props[(formname, univname)] = prop

                for propname, typedef, propinfo in propdefs:

                    prop = Prop(self, form, propname, typedef, propinfo)

                    full = f'{formname}:{propname}'
                    self.props[full] = prop
                    self.props[(formname, propname)] = prop

    def addBaseType(self, item):
        '''
        Add a Type instance to the data model.
        '''
        self.types[item.name] = item

    def type(self, name):
        '''
        Return a synapse.lib.types.Type by name.
        '''
        return self.types.get(name)

    def prop(self, name):
        return self.props.get(name)

    def form(self, name):
        return self.forms.get(name)
