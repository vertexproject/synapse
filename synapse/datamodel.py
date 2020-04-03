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
            'stortype': self.type.stortype,
        }

    def getTagPropDef(self):
        return (self.name, self.tdef, self.info)

    def getStorNode(self, form):

        ndef = (form.name, form.type.norm(self.name)[0])
        buid = s_common.buid(ndef)

        props = {
            'doc': self.info.get('doc', ''),
            'type': self.type.name,
        }

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
            'ndef': ndef,
            'props': pnorms
        })

class Prop:
    '''
    The Prop class represents a property defined within the data model.
    '''
    def __init__(self, modl, form, name, typedef, info):

        self.onsets = []
        self.ondels = []

        self.modl = modl
        self.name = name
        self.info = info
        self.univ = None

        if form is not None:
            if name.startswith('.'):
                self.univ = modl.prop(name)
                self.full = '%s%s' % (form.name, name)
                self.isext = name.startswith('._')
            else:
                self.full = '%s:%s' % (form.name, name)
                self.isext = name.startswith('_')
            self.isuniv = False
            self.isrunt = form.isrunt
            self.compoffs = form.type.getCompOffs(self.name)
        else:
            self.full = name
            self.isuniv = True
            self.isrunt = False
            self.compoffs = None
            self.isext = name.startswith('._')
        self.isform = False     # for quick Prop()/Form() detection

        self.form = form
        self.type = None
        self.typedef = typedef

        self.type = self.modl.getTypeClone(typedef)

        if form is not None:
            form.setProp(name, self)
            self.modl.propsbytype[self.type.name].append(self)

    def __repr__(self):
        return f'DataModel Prop: {self.full}'

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

    def getCompOffs(self):
        '''
        Return the offset of this field within the compound primary prop or None.
        '''
        return self.compoffs

    def pack(self):
        info = {
            'type': self.typedef,
            'stortype': self.type.stortype,
        }
        info.update(self.info)
        return info

    def getPropDef(self):
        return (self.name, self.typedef, self.info)

    def getStorNode(self, form):

        ndef = (form.name, form.type.norm(self.full)[0])

        buid = s_common.buid(ndef)
        props = {
            'doc': self.info.get('doc', ''),
            'type': self.type.name,
            'relname': self.name,
            'univ': self.isuniv,
            'base': self.name.split(':')[-1],
            'ro': int(self.info.get('ro', False)),
            'extmodel': self.isext,
        }

        if self.form is not None:
            props['form'] = self.form.name

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {'props': pnorms, 'ndef': ndef})

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
        self.isrunt = bool(info.get('runt', False))

        self.onadds = []
        self.ondels = []

        self.type = modl.types.get(name)
        if self.type is None:
            raise s_exc.NoSuchType(name=name)

        self.type.form = self

        self.props = {}     # name: Prop()
        self.refsout = None

    def getStorNode(self, form):

        ndef = (form.name, form.type.norm(self.name)[0])
        buid = s_common.buid(ndef)

        props = {
            'doc': self.info.get('doc', self.type.info.get('doc', '')),
            'type': self.type.name,
        }

        if form.name == 'syn:form':
            props['runt'] = self.isrunt
        elif form.name == 'syn:prop':
            props['univ'] = False
            props['extmodel'] = False
            props['form'] = self.name

        pnorms = {}
        for prop, valu in props.items():
            formprop = form.props.get(prop)
            if formprop is not None and valu is not None:
                pnorms[prop] = formprop.type.norm(valu)[0]

        return (buid, {
                'ndef': ndef,
                'props': pnorms,
                })

    def setProp(self, name, prop):
        self.refsout = None
        self.props[name] = prop

    def delProp(self, name):
        self.refsout = None
        prop = self.props.pop(name, None)
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
        for func in self.onadds:
            try:
                retn = func(node)
                if s_coro.iscoro(retn):
                    await retn
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('error on onadd for %s' % (self.name,))

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
        info = {
            'props': props,
            'stortype': self.type.stortype,
        }
        info.update(self.info)
        return info

    def getFormDef(self):
        propdefs = [p.getPropDef() for p in self.props.values() if not p.isuniv]
        return (self.name, self.info, propdefs)

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
        self.modeldefs = []

        self.univs = {}

        self.propsbytype = collections.defaultdict(list) # name: Prop()
        self.arraysbytype = collections.defaultdict(list)

        self._type_pends = collections.defaultdict(list)
        self._modeldef = {
            'ctors': [],
            'types': [],
            'forms': [],
            'univs': []
        }

        # add the primitive base types
        info = {'doc': 'The base 64 bit signed integer type.'}
        item = s_types.Int(self, 'int', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base floating point type.'}
        item = s_types.Float(self, 'float', info, {})
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

    def getPropsByType(self, name):
        props = self.propsbytype.get(name, ())
        # TODO order props based on score...
        return props

    def getProps(self):
        return [pobj for pname, pobj in self.props.items()
                if not (isinstance(pname, tuple))]

    def getTypeClone(self, typedef):

        base = self.types.get(typedef[0])
        if base is None:
            raise s_exc.NoSuchType(name=typedef[0])

        return base.clone(typedef[1])

    def getModelDefs(self):
        '''
        Returns:
            A list of one model definition compatible with addDataModels that represents the current data model
        '''
        mdef = self._modeldef.copy()
        # dynamically generate form defs due to extended props
        mdef['forms'] = [f.getFormDef() for f in self.forms.values()]
        mdef['univs'] = [u.getPropDef() for u in self.univs.values()]
        mdef['tagprops'] = [t.getTagPropDef() for t in self.tagprops.values()]
        return [('all', mdef)]

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
                "tagprops":(
                    (tagpropname, (typename, typeopts), {info}),
                )
            }

        Args:
            mods (list):  The list of tuples.

        Returns:
            None

        '''

        self.modeldefs.extend(mods)

        # load all the base type ctors in order...
        for _, mdef in mods:

            for name, ctor, opts, info in mdef.get('ctors', ()):
                item = s_dyndeps.tryDynFunc(ctor, self, name, info, opts)
                self.types[name] = item
                self._modeldef['ctors'].append((name, ctor, opts, info))

        # load all the types in order...
        for _, mdef in mods:
            for typename, (basename, typeopts), typeinfo in mdef.get('types', ()):
                self.addType(typename, basename, typeopts, typeinfo)

        # Load all the universal properties
        for _, mdef in mods:
            for univname, typedef, univinfo in mdef.get('univs', ()):
                self.addUnivProp(univname, typedef, univinfo)

        # Load all the tagprops
        for _, mdef in mods:
            for tpname, typedef, tpinfo in mdef.get('tagprops', ()):
                self.addTagProp(tpname, typedef, tpinfo)

        # now we can load all the forms...
        for _, mdef in mods:

            for formname, forminfo, propdefs in mdef.get('forms', ()):
                self.addForm(formname, forminfo, propdefs)

    def addType(self, typename, basename, typeopts, typeinfo):
        base = self.types.get(basename)
        if base is None:
            raise s_exc.NoSuchType(name=basename)

        newtype = base.extend(typename, typeopts, typeinfo)
        self.types[typename] = newtype
        self._modeldef['types'].append(newtype.getTypeDef())

    def addForm(self, formname, forminfo, propdefs):

        if not s_grammar.isFormName(formname):
            mesg = f'Invalid form name {formname}'
            raise s_exc.BadFormDef(name=formname, mesg=mesg)

        _type = self.types.get(formname)
        if _type is None:
            raise s_exc.NoSuchType(name=formname)

        form = Form(self, formname, forminfo)

        self.forms[formname] = form
        self.props[formname] = form

        for univname, typedef, univinfo in (u.getPropDef() for u in self.univs.values()):
            self._addFormUniv(form, univname, typedef, univinfo)

        for propdef in propdefs:

            if len(propdef) != 3:
                raise s_exc.BadPropDef(valu=propdef)

            propname, typedef, propinfo = propdef
            self._addFormProp(form, propname, typedef, propinfo)

    def _addFormUniv(self, form, name, tdef, info):

        prop = Prop(self, form, name, tdef, info)

        full = f'{form.name}{name}'

        self.props[full] = prop
        self.props[(form.name, name)] = prop

    def addUnivProp(self, name, tdef, info):

        base = '.' + name
        univ = Prop(self, None, base, tdef, info)

        self.props[base] = univ
        self.univs[base] = univ

        for form in self.forms.values():
            self._addFormUniv(form, base, tdef, info)

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

        self.props[prop.full] = prop

    def delTagProp(self, name):
        return self.tagprops.pop(name)

    def addTagProp(self, name, tdef, info):
        if name in self.tagprops:
            raise s_exc.DupTagPropName(mesg=name)

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

        self.univs.pop(univname, None)

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
        return self.univs.get(name)

    def tagprop(self, name):
        return self.tagprops.get(name)
