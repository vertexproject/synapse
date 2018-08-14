'''
An API to assist with the creation and enforcement of cortex data models.
'''
import regex
import logging
import collections

import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps

import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')
propre = regex.compile('^[0-9a-z:_]+$')

class Prop:
    '''
    The Prop class represents a property defined within the data model.
    '''

    def __init__(self, modl, form, name, typedef, info):

        self.modl = modl
        self.name = name
        self.info = info

        self.isform = False     # for quick Prop()/Form() detection

        self.form = form
        self.type = None
        self.typedef = typedef

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

        # TODO: make types control this more tightly...
        if cmpr == '~=':
            return (
                ('prop:re', (self.form.name, self.name, valu, {})),
            )

        iops = self.type.getIndxOps(valu, cmpr=cmpr)
        return (
            ('indx', ('byprop', self.pref, iops)),
        )

    def getSetOps(self, buid, norm):
        indx = self.type.getStorIndx(norm)
        return (
            ('prop:set', (buid, self.form.name, self.name, norm, indx, self.storinfo)),
        )

    def getDelOps(self, buid):
        '''
        Get a list of storage operations to delete this property from the buid.

        Args:
            buid (bytes): The node buid.

        Returns:
            (tuple): The storage operations
        '''
        return (
            ('prop:del', (buid, self.form.name, self.name, self.storinfo)),
        )

    def filt(self, text, cmpr='='):
        '''
        Construct a filter function for nodes by property.
        '''
        typefilt = self.type.getFiltFunc(text=text, cmpr=cmpr)
        if typefilt is None:
            return

        def func(node):
            valu = node[1]['props'].get(self.name)
            return typefilt(valu)

        return func

    def pack(self):
        info = {'type': self.typedef}
        info.update(self.info)
        return info

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
            iops = (('pref', b''),)
            return (
                ('indx', ('byuniv', self.pref, iops)),
            )

        # TODO: make types control this more tightly...
        if cmpr == '~=':
            return (
                ('univ:re', (self.name, valu, {})),
            )

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
        self.full = name    # so a Form() can act like a Prop().
        self.info = info

        self.isform = True

        self.onadds = []
        self.ondels = []

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

    def onDel(self, func):
        self.ondels.append(func)

    def wasAdded(self, node):
        '''
        Fire the onAdd() callbacks for node creation.
        '''
        for func in self.onadds:
            try:
                func(node)
            except Exception as e:
                logger.exception('error on onadd for %s' % (self.name,))

    def wasDeleted(self, node):
        '''
        Fire the onDel() callbacks for node deletion.
        '''
        for func in self.ondels:
            try:
                func(node)
            except Exception as e:
                logger.exception('error on onadel for %s' % (self.name,))

    def getSetOps(self, buid, norm):
        indx = self.type.getStorIndx(norm)
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

        if cmpr == '~=':
            return (
                ('form:re', (self.name, valu, {})),
            )

        iops = self.type.getIndxOps(valu, cmpr=cmpr)
        return (
            ('indx', ('byprop', self.pref, iops)),
        )

    def prop(self, name: str):
        '''
        Return a secondary property for this form by relative prop name.

        Args:
            name (str): The relative property name.
        Returns:
            (synapse.datamodel.Prop): The property or None.
        '''
        return self.props.get(name)

    def pack(self):
        props = {p.name: p.pack() for p in self.props.values()}
        info = {'props': props}
        info.update(self.info)
        return info

class Model:
    '''
    The data model used by a Cortex hypergraph.
    '''
    def __init__(self):

        self.types = {} # name: Type()
        self.forms = {} # name: Form()
        self.props = {} # (form,name): Prop() and full: Prop()
        self.formabbr = {} # name: [Form(), ... ]

        self.univs = []

        self.propsbytype = collections.defaultdict(list) # name: Prop()

        self._type_pends = collections.defaultdict(list)

        # add the primitive base types
        info = {'doc': 'The base 64 bit signed integer type.'}
        item = s_types.Int(self, 'int', info, {})
        self.addBaseType(item)

        info = {'doc': 'A base range type.'}
        item = s_types.Range(self, 'range', info, {'type': ('int', {})})
        self.addBaseType(item)

        info = {'doc': 'The base string type.'}
        item = s_types.Str(self, 'str', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base hex type.'}
        item = s_types.Hex(self, 'hex', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base boolean type.'}
        item = s_types.Bool(self, 'bool', info, {})
        self.addBaseType(item)

        info = {'doc': 'A date/time value.'}
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

        #info = {'doc': 'A list type for storing multiple values of the same type.'}
        #item = s_types.List(self, 'list', info, {'type': 'str'})
        #self.addBaseType(item)

        info = {'doc': 'An digraph edge base type.'}
        item = s_types.Edge(self, 'edge', info, {})
        self.addBaseType(item)

        info = {'doc': 'An digraph edge base type with a unique time.'}
        item = s_types.TimeEdge(self, 'timeedge', info, {})
        self.addBaseType(item)

        info = {'doc': 'Arbitrary msgpack compatible data stored without an index.'}
        item = s_types.Data(self, 'data', info, {})
        self.addBaseType(item)

        info = {'doc': 'The nodeprop type for a (prop,valu) compound field.'}
        item = s_types.NodeProp(self, 'nodeprop', info, {})
        self.addBaseType(item)

        # add the base universal properties...
        self.addUnivProp('seen', ('ival', {}), {
            'doc': 'The time interval for first/last observation of the node.',
        })
        self.addUnivProp('created', ('time', {}), {
            'doc': 'The time the node was created in the cortex.',
        })

    def getPropsByType(self, name):
        props = self.propsbytype.get(name, ())
        # TODO order props based on score...
        return props

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

    def getModelDict(self):

        retn = {
            'types': {},
            'forms': {},
        }

        for tobj in self.types.values():
            retn['types'][tobj.name] = tobj.pack()

        for fobj in self.forms.values():
            retn['forms'][fobj.name] = fobj.pack()

        return retn

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
                item = s_dyndeps.tryDynFunc(ctor, self, name, info, opts)
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
                    self._addFormUniv(form, univname, typedef, univinfo)

                for propdef in propdefs:

                    if len(propdef) != 3:
                        raise s_exc.BadPropDef(valu=propdef)

                    propname, typedef, propinfo = propdef

                    prop = Prop(self, form, propname, typedef, propinfo)

                    full = f'{formname}:{propname}'
                    self.props[full] = prop
                    self.props[(formname, propname)] = prop

    def _addFormUniv(self, form, name, tdef, info):

        base = '.' + name
        prop = Prop(self, form, base, tdef, info)

        full = f'{form.name}.{name}'

        self.props[full] = prop
        self.props[(form.name, base)] = prop

    def addUnivProp(self, name, tdef, info):

        base = '.' + name
        univ = Univ(self, base, tdef, info)

        self.props[base] = univ

        self.univs.append((name, tdef, info))

        for form in self.forms.values():
            self._addFormUniv(form, name, tdef, info)

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
