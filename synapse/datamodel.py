'''
An API to assist with the creation and enforcement of cortex data models.
'''
import asyncio
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.types as s_types
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')

class TagProp:

    def __init__(self, model, name, tdef, info):

        self.name = name
        self.info = info
        self.tdef = tdef
        self.model = model

        self.utf8 = name.encode()
        self.nenc = name.encode() + b'\x00'

        self.base = self.model.types.get(tdef[0])
        if self.base is None:
            raise s_exc.NoSuchType(name=tdef[0])

        self.type = self.base.clone(tdef[1])

        if isinstance(self.type, s_types.Array):
            mesg = 'Tag props may not be array types (yet).'
            raise s_exc.BadPropDef(mesg=mesg)

    def pack(self):
        return {
            'name': self.name,
            'info': self.info,
            'type': self.tdef,
        }

class PropBase:

    def __init__(self):
        self.isrunt = False
        self.onsets = []
        self.ondels = []

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

    async def wasSet(self, node, oldv):
        '''
        Fire the onset() handlers for this property.

        Args:
            node (synapse.lib.node.Node): The node whose property was set.
            oldv (obj): The previous value of the property.
        '''
        for func in self.onsets:
            try:
                await s_coro.ornot(func, node, oldv)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('onset() error for %s' % (self.full,))

    async def wasDel(self, node, oldv):
        for func in self.ondels:
            try:
                await s_coro.ornot(func, node, oldv)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('ondel() error for %s' % (self.full,))

class Prop(PropBase):
    '''
    The Prop class represents a property defined within the data model.
    '''
    def __init__(self, modl, form, name, typedef, info):

        PropBase.__init__(self)

        self.modl = modl
        self.name = name
        self.info = info

        self.isform = False     # for quick Prop()/Form() detection
        self.isrunt = form.isrunt
        self.compoffs = form.type.getCompOffs(self.name)

        self.form = form
        self.type = None
        self.typedef = typedef

        self.storinfo = {
            'univ': name.startswith('.')
        }

        self.univ = None
        self.full = '%s:%s' % (form.name, name)
        if name.startswith('.'):
            self.univ = name
            self.full = '%s%s' % (form.name, name)

        self.utf8name = self.name.encode('utf8')
        self.encname = self.utf8name + b'\x00'

        self.pref = self.form.utf8name + b'\x00' + self.utf8name + b'\x00'
        self.dbname = 'byprop'

        self.type = self.modl.getTypeClone(typedef)

        self.form.setProp(name, self)

        self.modl.propsbytype[self.type.name].append(self)

        # if we have a defval, tell the form...
        defv = self.info.get('defval')
        if defv is not None:
            self.form.defvals[name] = defv

    def getCompOffs(self):
        '''
        Return the offset of this field within the compound primary prop or None.
        '''
        return self.compoffs

    def getLiftOps(self, valu, cmpr='='):

        if self.type._lift_v2:
            return self.type.getLiftOpsV2(self, valu, cmpr=cmpr)

        if valu is None:
            iops = (('pref', b''),)
            return (
                ('indx', ('byprop', self.pref, iops)),
            )

        # TODO: In an ideal world, this would get smashed down into the self.type.getLiftOps
        # but since doing so breaks existing types, and fixing those could cause a cascade
        # of fun failures, we'll put this off until another flag day
        if cmpr == '~=':
            return (
                ('prop:re', (self.form.name, self.name, valu, {})),
            )

        lops = self.type.getLiftOps('prop', cmpr, (self.form.name, self.name, valu))
        if lops is not None:
            return lops

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

    def pack(self):
        info = {'type': self.typedef}
        info.update(self.info)
        return info

class Univ(PropBase):
    '''
    A property-like object that can lift without Form().
    '''
    def __init__(self, modl, name, typedef, propinfo):
        PropBase.__init__(self)
        self.modl = modl
        self.name = name
        self.isform = False     # for quick Prop()/Form() detection
        self.type = modl.getTypeClone(typedef)
        self.info = propinfo
        self.pref = name.encode('utf8') + b'\x00'
        self.dbname = 'byuniv'

    def getLiftOps(self, valu, cmpr='='):

        if valu is None:
            iops = (('pref', b''),)
            return (
                ('indx', ('byuniv', self.pref, iops)),
            )

        # TODO: In an ideal world, this would get smashed down into the self.type.getLiftOps
        # but since doing so breaks existing types, and fixing those could cause a cascade
        # of fun failures, we'll put this off until another flag day
        if cmpr == '~=':
            return (
                ('univ:re', (self.name, valu, {})),
            )

        lops = self.type.getLiftOps('univ', cmpr, (None, self.name, valu))
        if lops is not None:
            return lops

        iops = self.type.getIndxOps(valu, cmpr)

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

        self.waits = collections.defaultdict(list)

        self.isform = True
        self.isrunt = bool(info.get('runt', False))

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
        self.refsout = None

    def setProp(self, name, prop):
        self.refsout = None
        self.props[name] = prop

    def delProp(self, name):
        self.refsout = None
        prop = self.props.pop(name, None)
        self.defvals.pop(name, None)
        return prop

    def getRefsOut(self):

        if self.refsout is None:

            self.refsout = {
                'prop': [],
                'ndef': [],
                'array': [],
            }

            for name, prop in self.props.items():

                if isinstance(prop.type, s_types.Array):
                    typename = prop.type.arraytype.name
                    if self.modl.forms.get(typename) is not None:
                        self.refsout['array'].append((name, typename))

                elif isinstance(prop.type, s_types.Ndef):
                    self.refsout['ndef'].append(name)

                elif self.modl.forms.get(prop.type.name) is not None:
                    self.refsout['prop'].append((name, prop.type.name))

        return self.refsout

    def getWaitFor(self, valu):
        norm, info = self.type.norm(valu)
        buid = s_common.buid((self.name, norm))
        evnt = asyncio.Event()
        self.waits[buid].append(evnt)
        return evnt

    def onAdd(self, func):
        '''
        Add a callback for adding this type of node.

        The callback is executed after node construction.

        Args:
            func (function): A callback func(node)

        def func(xact, node):
            dostuff()
        '''
        self.onadds.append(func)

    def offAdd(self, func):
        '''
        Unregister a callback for tag addition.

        Args:
            name (str): The name of the tag.
            func (function): The callback func(node)

        '''
        try:
            self.onadds.remove(func)
        except ValueError:  # pragma: no cover
            pass

    def onDel(self, func):
        self.ondels.append(func)

    async def wasAdded(self, node):
        '''
        Fire the onAdd() callbacks for node creation.
        '''
        waits = self.waits.pop(node.buid, None)
        if waits is not None:
            [e.set() for e in waits]

        for func in self.onadds:
            try:
                retn = func(node)
                if s_coro.iscoro(retn):
                    await retn
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('error on onadd for %s' % (self.name,))

        await node.snap.view.runNodeAdd(node)

    async def wasDeleted(self, node):
        '''
        Fire the onDel() callbacks for node deletion.
        '''
        for func in self.ondels:
            try:
                retn = func(node)
                if s_coro.iscoro(retn):
                    await retn
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('error on ondel for %s' % (self.name,))

        await node.snap.view.runNodeDel(node)

    def getSetOps(self, buid, norm):

        indx = self.type.indx(norm)
        if len(indx) > 256:
            raise s_exc.BadIndxValu(name=self.name, norm=norm, indx=indx)

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
        if self.type._lift_v2:
            return self.type.getLiftOpsV2(self, valu, cmpr=cmpr)

        if valu is None:
            iops = (('pref', b''),)
            return (
                ('indx', ('byprop', self.pref, iops)),
            )

        # TODO: In an ideal world, this would get smashed down into the self.type.getLiftOps
        # but since doing so breaks existing types, and fixing those could cause a cascade
        # of fun failures, we'll put this off until another flag day
        if cmpr == '~=':
            return (
                ('form:re', (self.name, valu, {})),
            )

        lops = self.type.getLiftOps('form', cmpr, (None, self.name, valu))
        if lops is not None:
            return lops

        iops = self.type.getIndxOps(valu, cmpr)
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

class ModelInfo:
    '''
    A summary of the information in a DataModel, sufficent for parsing storm queries.
    '''
    def __init__(self):
        self.formnames = set()
        self.propnames = set()
        self.univnames = set()

    def addDataModels(self, mods):
        '''
        Adds a model definition (same format as input to Model.addDataModels and output of Model.getModelDef).
        '''
        # Load all the universal properties
        for _, mdef in mods:
            for univname, _, _ in mdef.get('univs', ()):
                self.addUnivName(univname)

        # Load all the forms
        for _, mdef in mods:
            for formname, formopts, propdefs in mdef.get('forms', ()):

                self.formnames.add(formname)
                self.propnames.add(formname)

                for univname in self.univnames:
                    full = f'{formname}{univname}'
                    self.propnames.add(full)

                for propname, _, _ in propdefs:
                    full = f'{formname}:{propname}'
                    self.propnames.add(full)

    def addUnivName(self, univname):
        self.univnames.add('.' + univname)
        self.propnames.add('.' + univname)

    def addUnivForm(self, univname, form):
        self.propnames.add('.'.join([form, univname]))

    def isprop(self, name):
        return name in self.propnames

    def isform(self, name):
        return name in self.formnames

    def isuniv(self, name):
        return name in self.univnames

class Model:
    '''
    The data model used by a Cortex hypergraph.
    '''
    def __init__(self):

        self.types = {} # name: Type()
        self.forms = {} # name: Form()
        self.props = {} # (form,name): Prop() and full: Prop()
        self.tagprops = {} # name: TagProp()
        self.formabbr = {} # name: [Form(), ... ]

        self.univs = []
        self.univlook = {}

        self.propsbytype = collections.defaultdict(list) # name: Prop()
        self.arraysbytype = collections.defaultdict(list)

        self._type_pends = collections.defaultdict(list)
        self._modeldef = {
            'ctors': [],
            'types': [],
            'forms': [],
            'univs': []
        }
        self._modelinfo = ModelInfo()

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

        info = {'doc': 'A typed array which indexes each field.'}
        item = s_types.Array(self, 'array', info, {'type': 'int'})
        self.addBaseType(item)

        # info = {'doc': 'A list type for storing multiple values of the same type.'}
        # item = s_types.List(self, 'list', info, {'type': 'str'})
        # self.addBaseType(item)

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
            'ro': True,
            'doc': 'The time the node was created in the cortex.',
        })

    def getModelInfo(self):
        return self._modelinfo

    def getPropsByType(self, name):
        props = self.propsbytype.get(name, ())
        # TODO order props based on score...
        return props

    def getTypeClone(self, typedef):

        base = self.types.get(typedef[0])
        if base is None:
            raise s_exc.NoSuchType(name=typedef[0])

        return base.clone(typedef[1])

    def getModelDef(self):
        '''
        Returns:
            A list of one model definition compatible with addDataModels that represents the current data model
        '''
        return [('all', self._modeldef)]

    def getModelDict(self):
        retn = {
            'types': {},
            'forms': {},
            'tagprops': {},
        }

        for tobj in self.types.values():
            retn['types'][tobj.name] = tobj.pack()

        for fobj in self.forms.values():
            retn['forms'][fobj.name] = fobj.pack()

        for pobj in self.tagprops.values():
            retn['tagprops'][pobj.name] = pobj.pack()

        return retn

    def addDataModels(self, mods):
        '''
        Add a list of (name, mdef) tuples.

        A model definition (mdef) is structured as follows::

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
                "univs":(
                    (propname, (typename, typeopts), {info}),
                )
            }

        Args:
            mods (list):  The list of tuples.

        Returns:
            None

        '''

        # load all the base type ctors in order...
        for modlname, mdef in mods:

            for name, ctor, opts, info in mdef.get('ctors', ()):
                item = s_dyndeps.tryDynFunc(ctor, self, name, info, opts)
                self.types[name] = item
                self._modeldef['ctors'].append((name, ctor, opts, info))

        # load all the types in order...
        for modlname, mdef in mods:
            for typename, (basename, typeopts), typeinfo in mdef.get('types', ()):
                self.addType(typename, basename, typeopts, typeinfo)

        # Load all the universal properties
        for modlname, mdef in mods:
            for univname, typedef, univinfo in mdef.get('univs', ()):
                self.addUnivProp(univname, typedef, univinfo)

        # now we can load all the forms...
        for modlname, mdef in mods:

            for formname, forminfo, propdefs in mdef.get('forms', ()):
                self.addForm(formname, forminfo, propdefs)

        self._modelinfo.addDataModels(mods)

    def addType(self, typename, basename, typeopts, typeinfo):
        base = self.types.get(basename)
        if base is None:
            raise s_exc.NoSuchType(name=basename)

        self.types[typename] = base.extend(typename, typeopts, typeinfo)
        self._modeldef['types'].append((typename, (basename, typeopts), typeinfo))

    def addForm(self, formname, forminfo, propdefs):

        if not s_grammar.isFormName(formname):
            mesg = f'Invalid form name {formname}'
            raise s_exc.BadFormDef(name=formname, mesg=mesg)

        _type = self.types.get(formname)
        if _type is None:
            raise s_exc.NoSuchType(name=formname)

        self._modeldef['forms'].append((formname, forminfo, propdefs))

        form = Form(self, formname, forminfo)

        self.forms[formname] = form
        self.props[formname] = form

        for univname, typedef, univinfo in self.univs:
            self._addFormUniv(form, univname, typedef, univinfo)

        for propdef in propdefs:

            if len(propdef) != 3:
                raise s_exc.BadPropDef(valu=propdef)

            propname, typedef, propinfo = propdef
            self._addFormProp(form, propname, typedef, propinfo)

    def _addFormUniv(self, form, name, tdef, info):

        self._modelinfo.addUnivForm(name, form.name)
        base = '.' + name
        prop = Prop(self, form, base, tdef, info)

        full = f'{form.name}.{name}'

        self.props[full] = prop
        self.props[(form.name, base)] = prop

    def addUnivProp(self, name, tdef, info):

        self._modelinfo.addUnivName(name)

        base = '.' + name
        univ = Univ(self, base, tdef, info)

        self.props[base] = univ
        self.univlook[base] = univ

        self.univs.append((name, tdef, info))
        self._modeldef['univs'].append((name, tdef, info))

        for form in self.forms.values():
            self._addFormUniv(form, name, tdef, info)

    def addFormProp(self, formname, propname, tdef, info):
        form = self.forms.get(formname)
        if form is None:
            raise s_exc.NoSuchForm(name=formname)
        self._addFormProp(form, propname, tdef, info)

    def _addFormProp(self, form, name, tdef, info):

        prop = Prop(self, form, name, tdef, info)

        # index the array item types
        if isinstance(prop.type, s_types.Array):
            self.arraysbytype[prop.type.arraytype.name].append(prop)

        full = f'{form.name}:{name}'
        self.props[full] = prop
        self.props[(form.name, name)] = prop

    def delTagProp(self, name):
        return self.tagprops.pop(name)

    def addTagProp(self, name, tdef, info):
        prop = TagProp(self, name, tdef, info)
        self.tagprops[name] = prop
        return prop

    def getTagProp(self, name):
        return self.tagprops.get(name)

    def delFormProp(self, formname, propname):

        form = self.forms.get(formname)
        if form is None:
            raise s_exc.NoSuchForm(name=formname)

        prop = form.delProp(propname)
        if prop is None:
            raise s_exc.NoSuchProp(name=f'{formname}:{propname}')

        if isinstance(prop.type, s_types.Array):
            self.arraysbytype[prop.type.arraytype.name].remove(prop)

        self.props.pop(prop.full, None)
        self.props.pop((form.name, prop.name), None)

        self.propsbytype[prop.type.name].remove(prop)

    def delUnivProp(self, propname):

        univname = '.' + propname

        univ = self.props.pop(univname, None)
        if univ is None:
            raise s_exc.NoSuchUniv(name=propname)

        self.univlook.pop(univname, None)

        for form in self.forms.values():
            self.delFormProp(form.name, univname)

    def addBaseType(self, item):
        '''
        Add a Type instance to the data model.
        '''
        ctor = '.'.join([item.__class__.__module__, item.__class__.__qualname__])
        self._modeldef['ctors'].append(((item.name, ctor, dict(item.opts), dict(item.info))))
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

    def univ(self, name):
        return self.univlook.get(name)

    def tagprop(self, name):
        return self.tagprops.get(name)
