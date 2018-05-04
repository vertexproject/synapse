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

        self.full = '%s:%s' % (form.name, name)
        self.onsets = []

        self.utf8name = self.name.encode('utf8')
        self.utf8full = self.full.encode('utf8')

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

        The callback is called with the current transaction,
        the node, and the old property value (or None).

        def func(xact, node, oldv):
            dostuff()
        '''
        self.onsets.append(func)

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

    def lift(self, xact, valu, cmpr='='):
        '''
        Lift nodes by the given property valu and comparator.

        Args:
            xact (synapse.lib.xact.Xact): A Cortex transaction.
            valu (obj): A lift valu for the given property type.
            cmpr (str): An optional alternate comparator to specify.

        Yields:

            (tuple, synapse.lib.nodeNode): Tuples of (row, Node) pairs.
        '''
        return self.type.liftByProp(xact, self, valu, cmpr=cmpr)

    def stor(self, buid, norm):
        '''
        Retrieve a set of storage operations needed to set this property to
        the given pre-normalized value.

        Args:
            buid (bytes): The binary GUID for the node.
            norm (obj): The normalized property value.
        '''
        # setup a standard prop:set stor operation
        sops = (
            ('node:prop:set', {
                'buid': buid,
                'form': self.form.utf8name,
                'prop': self.utf8name,
                'valu': norm,
                'indx': self.type.indx(norm),
            }),
        )

        return sops

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

    def stor(self, buid, norm):
        '''
        Ask for the storage operations needed to add a node by value.

        Args:
            buid (bytes): The buid for the node to create.
            norm (obj): The normalized value for the primary property.

        Returns:
            (list): A list of storage operation tuples.
        '''
        indx = self.type.indx(norm)
        return [
            ('node:add', {'buid': buid, 'form': self.utf8name, 'valu': norm, 'indx': indx}),
        ]

    def lift(self, xact, valu, cmpr='='):
        '''
        Perform a lift operation and yield row,Node tuples.
        '''
        return self.type.liftByForm(xact, self, valu, cmpr=cmpr)

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

        self.propsbytype = collections.defaultdict(list) # name: Prop()

        self._type_pends = collections.defaultdict(list)

        # add the primitive base types
        info = {'doc': 'The base 64 bit signed integer type.'}
        item = s_types.Int(self, 'int', info, {})
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

                for propname, typedef, propinfo in propdefs:

                    prop = Prop(self, form, propname, typedef, propinfo)

                    full = '%s:%s' % (formname, propname)
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
