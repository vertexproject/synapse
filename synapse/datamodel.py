'''
An API to assist with the creation and enforcement of cortex data models.
'''
import sys
import asyncio
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.types as s_types
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')

PREFIX_CACHE_SIZE = 1000

class TagProp:

    def __init__(self, model, name, tdef, info):

        self.name = name
        self.info = info
        self.tdef = tdef
        self.model = model
        self.locked = False

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

        self.delperms = [('node', 'prop', 'del', self.full)]
        self.setperms = [('node', 'prop', 'set', self.full)]

        if form is not None:
            self.setperms.append(('node', 'prop', 'set', form.name, self.name))
            self.delperms.append(('node', 'prop', 'del', form.name, self.name))

        self.setperms.reverse()  # Make them in precedence order
        self.delperms.reverse()  # Make them in precedence order

        self.form = form
        self.type = None
        self.typedef = typedef

        self.alts = None
        self.locked = False
        self.deprecated = self.info.get('deprecated', False)

        self.type = self.modl.getTypeClone(typedef)
        self.typehash = self.type.typehash

        if self.type.isarray:
            self.arraytypehash = self.type.arraytype.typehash

        if form is not None:
            form.setProp(name, self)
            self.modl.propsbytype[self.type.name][self.full] = self

        if self.deprecated or self.type.deprecated:
            async def depfunc(node, oldv):
                mesg = f'The property {self.full} is deprecated or using a deprecated type and will be removed in 3.0.0'
                await node.snap.warnonce(mesg)
                if __debug__:
                    sys.audit('synapse.datamodel.Prop.deprecated', mesg, self.full)

            self.onSet(depfunc)

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
            'name': self.name,
            'full': self.full,
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

    def getAlts(self):
        '''
        Return a list of Prop instances that are considered
        alternative locations for our property value, including
        self.
        '''
        if self.alts is None:
            self.alts = [self]
            for name in self.info.get('alts', ()):
                self.alts.append(self.form.reqProp(name))
        return self.alts

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

        self.addperm = ('node', 'add', self.name)
        self.delperm = ('node', 'del', self.name)

        self.type = modl.types.get(name)
        if self.type is None:
            raise s_exc.NoSuchType(name=name)

        self.typehash = self.type.typehash

        if self.type.isarray:
            self.arraytypehash = self.type.arraytype.typehash

        self.form = self

        self.props = {}     # name: Prop()
        self.ifaces = {}    # name: <ifacedef>

        self.refsout = None

        self.locked = False
        self.deprecated = self.type.deprecated

        if self.deprecated:
            async def depfunc(node):
                mesg = f'The form {self.full} is deprecated or using a deprecated type and will be removed in 3.0.0'
                await node.snap.warnonce(mesg)
                if __debug__:
                    sys.audit('synapse.datamodel.Form.deprecated', mesg, self.full)
            self.onAdd(depfunc)

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
                'ndefarray': [],
            }

            for name, prop in self.props.items():

                if isinstance(prop.type, s_types.Array):
                    if isinstance(prop.type.arraytype, s_types.Ndef):
                        self.refsout['ndefarray'].append(name)
                        continue

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

    def reqProp(self, name, extra=None):
        prop = self.props.get(name)
        if prop is not None:
            return prop

        full = f'{self.name}:{name}'
        exc = s_exc.NoSuchProp.init(full)
        if extra is not None:
            exc = extra(exc)

        raise exc

    def pack(self):
        props = {p.name: p.pack() for p in self.props.values()}
        info = {
            'name': self.name,
            'props': props,
            'stortype': self.type.stortype,
        }
        info.update(self.info)
        return info

    def getFormDef(self):
        propdefs = [p.getPropDef() for p in self.props.values() if not p.isuniv]
        return (self.name, self.info, propdefs)

class Edge:

    def __init__(self, modl, edgetype, edgeinfo):
        self.modl = modl
        self.edgetype = edgetype
        self.edgeinfo = edgeinfo

    def pack(self):
        return (self.edgetype, self.edgeinfo)

class Model:
    '''
    The data model used by a Cortex hypergraph.
    '''
    def __init__(self, core=None):

        self.core = core
        self.types = {}  # name: Type()
        self.forms = {}  # name: Form()
        self.props = {}  # (form,name): Prop() and full: Prop()
        self.edges = {}  # (n1form, verb, n2form): Edge()
        self.ifaces = {}  # name: <ifdef>
        self.tagprops = {}  # name: TagProp()
        self.formabbr = {}  # name: [Form(), ... ]
        self.modeldefs = []

        self.univs = {}
        self.allunivs = collections.defaultdict(list)

        self.propsbytype = collections.defaultdict(dict)  # name: Prop()
        self.arraysbytype = collections.defaultdict(dict)
        self.ifaceprops = collections.defaultdict(list)
        self.formsbyiface = collections.defaultdict(list)
        self.edgesbyn1 = collections.defaultdict(set)
        self.edgesbyn2 = collections.defaultdict(set)

        self.formprefixcache = s_cache.LruDict(PREFIX_CACHE_SIZE)

        self._type_pends = collections.defaultdict(list)
        self._modeldef = {
            'ctors': [],
            'types': [],
            'forms': [],
            'univs': [],
            'edges': [],
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

        info = {'doc': 'A duration value.'}
        item = s_types.Duration(self, 'duration', info, {})
        self.addBaseType(item)

        info = {'doc': 'A time window/interval.'}
        item = s_types.Ival(self, 'ival', info, {})
        self.addBaseType(item)

        info = {'doc': 'The base GUID type.'}
        item = s_types.Guid(self, 'guid', info, {})
        self.addBaseType(item)

        info = {'doc': 'A tag component string.'}
        item = s_types.TagPart(self, 'syn:tag:part', info, {})
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

        info = {'doc': 'An digraph edge base type.', 'deprecated': True}
        item = s_types.Edge(self, 'edge', info, {})
        self.addBaseType(item)

        info = {'doc': 'An digraph edge base type with a unique time.', 'deprecated': True}
        item = s_types.TimeEdge(self, 'timeedge', info, {})
        self.addBaseType(item)

        info = {'doc': 'Arbitrary json compatible data.'}
        item = s_types.Data(self, 'data', info, {})
        self.addBaseType(item)

        info = {'doc': 'The nodeprop type for a (prop,valu) compound field.'}
        item = s_types.NodeProp(self, 'nodeprop', info, {})
        self.addBaseType(item)

        info = {'doc': 'A potentially huge/tiny number. [x] <= 730750818665451459101842 with a fractional '
                       'precision of 24 decimal digits.'}
        item = s_types.HugeNum(self, 'hugenum', info, {})
        self.addBaseType(item)

        info = {'doc': 'A component of a hierarchical taxonomy.'}
        item = s_types.Taxon(self, 'taxon', info, {})
        self.addBaseType(item)

        info = {'doc': 'A hierarchical taxonomy.'}
        item = s_types.Taxonomy(self, 'taxonomy', info, {})
        self.addBaseType(item)

        info = {'doc': 'A velocity with base units in mm/sec.'}
        item = s_types.Velocity(self, 'velocity', info, {})
        self.addBaseType(item)

        # add the base universal properties...
        self.addUnivProp('seen', ('ival', {}), {
            'doc': 'The time interval for first/last observation of the node.',
        })
        self.addUnivProp('created', ('time', {'ismin': True}), {
            'ro': True,
            'doc': 'The time the node was created in the cortex.',
        })

    def getPropsByType(self, name):
        props = self.propsbytype.get(name)
        if props is None:
            return ()
        # TODO order props based on score...
        return list(props.values())

    def getArrayPropsByType(self, name):
        props = self.arraysbytype.get(name)
        if props is None:
            return ()
        return list(props.values())

    def getProps(self):
        return [pobj for pname, pobj in self.props.items()
                if not (isinstance(pname, tuple))]

    def getFormsByPrefix(self, prefix):
        forms = self.formprefixcache.get(prefix)
        if forms is not None:
            return forms

        forms = []
        for form in self.forms:
            if form.startswith(prefix):
                forms.append(form)

        if forms:
            forms.sort()
            self.formprefixcache[prefix] = forms
        return forms

    def reqProp(self, name, extra=None):
        prop = self.prop(name)
        if prop is not None:
            return prop

        exc = s_exc.NoSuchProp.init(name)
        if extra is not None:
            exc = extra(exc)

        raise exc

    def reqUniv(self, name):
        prop = self.univ(name)
        if prop is not None:
            return prop

        mesg = f'No universal property named {name}.'
        raise s_exc.NoSuchUniv(mesg=mesg, name=name)

    def reqTagProp(self, name):
        prop = self.getTagProp(name)
        if prop is not None:
            return prop

        mesg = f'No tag property named {name}.'
        raise s_exc.NoSuchTagProp(mesg=mesg, name=name)

    def reqFormsByPrefix(self, prefix, extra=None):
        forms = self.getFormsByPrefix(prefix)
        if not forms:
            mesg = f'No forms match prefix {prefix}.'
            exc = s_exc.NoSuchForm(name=prefix, mesg=mesg)
            if extra is not None:
                exc = extra(exc)
            raise exc

        return forms

    def reqFormsByLook(self, name, extra=None):
        if (form := self.form(name)) is not None:
            return (form.name,)

        if (forms := self.formsbyiface.get(name)) is not None:
            return forms

        if name.endswith('*'):
            return self.reqFormsByPrefix(name[:-1], extra=extra)

        exc = s_exc.NoSuchForm.init(name)
        if extra is not None:
            exc = extra(exc)

        raise exc

    def reqPropsByLook(self, name, extra=None):
        if (forms := self.formsbyiface.get(name)) is not None:
            return forms

        if (props := self.ifaceprops.get(name)) is not None:
            return props

        if name.endswith('*'):
            return self.reqFormsByPrefix(name[:-1], extra=extra)

        exc = s_exc.NoSuchProp.init(name)
        if extra is not None:
            exc = extra(exc)

        raise exc

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
        mdef['interfaces'] = list(self.ifaces.items())
        mdef['edges'] = [e.pack() for e in self.edges.values()]
        return [('all', mdef)]

    def getModelDict(self):
        retn = {
            'types': {},
            'forms': {},
            'edges': [],
            'univs': {},
            'tagprops': {},
            'interfaces': self.ifaces.copy()
        }

        for tobj in self.types.values():
            retn['types'][tobj.name] = tobj.pack()

        for fobj in self.forms.values():
            retn['forms'][fobj.name] = fobj.pack()

        for uobj in self.univs.values():
            retn['univs'][uobj.name] = uobj.pack()

        for pobj in self.tagprops.values():
            retn['tagprops'][pobj.name] = pobj.pack()

        for eobj in self.edges.values():
            retn['edges'].append(eobj.pack())

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
                "interfaces":(
                    (ifacename, {
                        'props': ((propname, (typename, typeopts), {info}),),
                        'doc': docstr,
                        'interfaces': (ifacename,)
                    }),
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
            custom = mdef.get('custom', False)
            for typename, (basename, typeopts), typeinfo in mdef.get('types', ()):
                typeinfo['custom'] = custom
                self.addType(typename, basename, typeopts, typeinfo)

        # load all the interfaces...
        for _, mdef in mods:
            for name, info in mdef.get('interfaces', ()):
                self.addIface(name, info)

        # Load all the universal properties
        for _, mdef in mods:
            for univname, typedef, univinfo in mdef.get('univs', ()):
                univinfo['custom'] = custom
                self.addUnivProp(univname, typedef, univinfo)

        # Load all the tagprops
        for _, mdef in mods:
            for tpname, typedef, tpinfo in mdef.get('tagprops', ()):
                self.addTagProp(tpname, typedef, tpinfo)

        # now we can load all the forms...
        for _, mdef in mods:

            for formname, forminfo, propdefs in mdef.get('forms', ()):
                self.addForm(formname, forminfo, propdefs, checks=False)

        # now we can load edge definitions...
        for _, mdef in mods:
            for etype, einfo in mdef.get('edges', ()):
                self.addEdge(etype, einfo)

        # now we can check the forms display settings...
        for form in self.forms.values():
            self._checkFormDisplay(form)

    def addEdge(self, edgetype, edgeinfo):

        n1form, verb, n2form = edgetype

        if n1form is not None:
            self._reqFormName(n1form)

        if n2form is not None:
            self._reqFormName(n2form)

        if not isinstance(verb, str):
            mesg = f'Edge definition verb must be a string: {edgetype}.'
            raise s_exc.BadArg(mesg=mesg)

        if self.edges.get(edgetype) is not None:
            mesg = f'Duplicate edge declared: {edgetype}.'
            raise s_exc.BadArg(mesg=mesg)

        edge = Edge(self, edgetype, edgeinfo)

        self.edges[edgetype] = edge
        self.edgesbyn1[n1form].add(edge)
        self.edgesbyn2[n2form].add(edge)

    def delEdge(self, edgetype):
        if self.edges.get(edgetype) is None:
            return

        n1form, verb, n2form = edgetype

        self.edges.pop(edgetype, None)
        self.edgesbyn1[n1form].discard(edgetype)
        self.edgesbyn2[n2form].discard(edgetype)

    def _reqFormName(self, name):
        form = self.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm.init(name)
        return form

    def addType(self, typename, basename, typeopts, typeinfo):
        base = self.types.get(basename)
        if base is None:
            raise s_exc.NoSuchType(name=basename)

        newtype = base.extend(typename, typeopts, typeinfo)

        if newtype.deprecated and typeinfo.get('custom'):
            mesg = f'The type {typename} is based on a deprecated type {newtype.name} which ' \
                   f'will be removed in 3.0.0.'
            logger.warning(mesg)

        self.types[typename] = newtype
        self._modeldef['types'].append(newtype.getTypeDef())

    def addForm(self, formname, forminfo, propdefs, checks=True):

        if not s_grammar.isFormName(formname):
            mesg = f'Invalid form name {formname}'
            raise s_exc.BadFormDef(name=formname, mesg=mesg)

        _type = self.types.get(formname)
        if _type is None:
            raise s_exc.NoSuchType(name=formname)

        form = Form(self, formname, forminfo)

        self.forms[formname] = form
        self.props[formname] = form

        if isinstance(form.type, s_types.Array):
            self.arraysbytype[form.type.arraytype.name][form.name] = form

        for univname, typedef, univinfo in (u.getPropDef() for u in self.univs.values()):
            self._addFormUniv(form, univname, typedef, univinfo)

        for propdef in propdefs:

            if len(propdef) != 3:
                raise s_exc.BadPropDef(valu=propdef)

            propname, typedef, propinfo = propdef
            self._addFormProp(form, propname, typedef, propinfo)

        # interfaces are listed in typeinfo for the form to
        # maintain backward compatibility for populated models
        for ifname in form.type.info.get('interfaces', ()):
            self._addFormIface(form, ifname)

        if checks:
            self._checkFormDisplay(form)

        self.formprefixcache.clear()

        return form

    def _checkFormDisplay(self, form):

        formtype = self.types.get(form.full)

        display = formtype.info.get('display')
        if display is None:
            return

        for column in display.get('columns', ()):
            coltype = column.get('type')
            colopts = column.get('opts')

            if coltype == 'prop':
                curf = form
                propname = colopts.get('name')
                parts = propname.split('::')

                for partname in parts:
                    prop = curf.prop(partname)
                    if prop is None:
                        mesg = (f'Form {form.name} defines prop column {propname}'
                               f' but {curf.full} has no property named {partname}.')
                        raise s_exc.BadFormDef(mesg=mesg)

                    curf = self.form(prop.type.name)

            else:
                mesg = f'Form {form.name} defines column with invalid type ({coltype}).'
                raise s_exc.BadFormDef(mesg=mesg)

    def delForm(self, formname):

        form = self.forms.get(formname)
        if form is None:
            return

        ifaceprops = set()
        for iface in form.ifaces.values():
            for prop in iface.get('props', ()):
                ifaceprops.add(prop[0])

        formprops = []
        for propname, prop in form.props.items():
            if prop.univ is not None or propname in ifaceprops:
                continue
            formprops.append(prop)

        if formprops:
            propnames = ', '.join(prop.name for prop in formprops)
            mesg = f'Form has extended properties: {propnames}'
            raise s_exc.CantDelForm(mesg=mesg)

        if isinstance(form.type, s_types.Array):
            self.arraysbytype[form.type.arraytype.name].pop(form.name, None)

        for ifname in form.type.info.get('interfaces', ()):
            self._delFormIface(form, ifname)

        self.forms.pop(formname, None)
        self.props.pop(formname, None)

        self.formprefixcache.clear()

    def addIface(self, name, info):
        # TODO should we add some meta-props here for queries?
        self.ifaces[name] = info

    def delType(self, typename):

        _type = self.types.get(typename)
        if _type is None:
            return

        if self.propsbytype.get(typename):
            mesg = f'Cannot delete type {typename} as it is still in use by properties.'
            raise s_exc.CantDelType(mesg=mesg, name=typename)

        for _type in self.types.values():
            if typename in _type.info['bases']:
                mesg = f'Cannot delete type {typename} as it is still in use by other types.'
                raise s_exc.CantDelType(mesg=mesg, name=typename)

            if _type.isarray and _type.arraytype.name == typename:
                mesg = f'Cannot delete type {typename} as it is still in use by array types.'
                raise s_exc.CantDelType(mesg=mesg, name=typename)

        self.types.pop(typename, None)
        self.propsbytype.pop(typename, None)
        self.arraysbytype.pop(typename, None)

    def _addFormUniv(self, form, name, tdef, info):

        univ = self.reqUniv(name)

        prop = Prop(self, form, name, tdef, info)
        prop.locked = univ.locked

        full = f'{form.name}{name}'

        self.props[full] = prop
        self.props[(form.name, name)] = prop

        self.allunivs[name].append(prop)

    def addUnivProp(self, name, tdef, info):

        base = '.' + name
        univ = Prop(self, None, base, tdef, info)

        if univ.type.deprecated:
            mesg = f'The universal property {univ.full} is using a deprecated type {univ.type.name} which will' \
                   f' be removed in 3.0.0'
            logger.warning(mesg)

        self.props[base] = univ
        self.univs[base] = univ

        self.allunivs[base].append(univ)

        for form in self.forms.values():
            prop = self._addFormUniv(form, base, tdef, info)

    def getAllUnivs(self, name):
        return list(self.allunivs.get(name, ()))

    def addFormProp(self, formname, propname, tdef, info):
        form = self.forms.get(formname)
        if form is None:
            raise s_exc.NoSuchForm.init(formname)
        return self._addFormProp(form, propname, tdef, info)

    def _addFormProp(self, form, name, tdef, info):

        prop = Prop(self, form, name, tdef, info)

        # index the array item types
        if isinstance(prop.type, s_types.Array):
            self.arraysbytype[prop.type.arraytype.name][prop.full] = prop

        self.props[prop.full] = prop
        return prop

    def _prepFormIface(self, form, iface):

        template = s_msgpack.deepcopy(iface.get('template', {}))
        template.update(form.type.info.get('template', {}))

        def convert(item):

            if isinstance(item, str):

                if item == '$self':
                    return form.name

                item = s_common.format(item, **template)

                # warn but do not blow up. there may be extended model elements
                # with {}s which are not used for templates...
                if item.find('{') != -1: # pragma: no cover
                    logger.warning(f'Missing template specifier in: {item} on {form.name}')

                return item

            if isinstance(item, dict):
                return {convert(k): convert(v) for (k, v) in item.items()}

            if isinstance(item, (list, tuple)):
                return tuple([convert(v) for v in item])

            return item

        return convert(iface)

    def _addFormIface(self, form, name, subifaces=None):

        iface = self.ifaces.get(name)

        if iface is None:
            mesg = f'Form {form.name} depends on non-existent interface: {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        if iface.get('deprecated'):
            mesg = f'Form {form.name} depends on deprecated interface {name} which will be removed in 3.0.0'
            logger.warning(mesg)

        iface = self._prepFormIface(form, iface)

        for propname, typedef, propinfo in iface.get('props', ()):

            # allow form props to take precedence
            if (prop := form.prop(propname)) is None:
                prop = self._addFormProp(form, propname, typedef, propinfo)

            self.ifaceprops[f'{name}:{propname}'].append(prop.full)

            if subifaces is not None:
                for subi in subifaces:
                    self.ifaceprops[f'{subi}:{propname}'].append(prop.full)

        form.ifaces[name] = iface
        self.formsbyiface[name].append(form.name)

        if (ifaces := iface.get('interfaces')) is not None:
            if subifaces is None:
                subifaces = []
            else:
                subifaces = list(subifaces)

            subifaces.append(name)

            for ifname in ifaces:
                self._addFormIface(form, ifname, subifaces=subifaces)

    def _delFormIface(self, form, name, subifaces=None):

        if (iface := self.ifaces.get(name)) is None:
            return

        iface = self._prepFormIface(form, iface)

        for propname, typedef, propinfo in iface.get('props', ()):
            fullprop = f'{form.name}:{propname}'
            self.delFormProp(form.name, propname)
            self.ifaceprops[f'{name}:{propname}'].remove(fullprop)

            if subifaces is not None:
                for subi in subifaces:
                    self.ifaceprops[f'{subi}:{propname}'].remove(fullprop)

        form.ifaces.pop(name, None)
        self.formsbyiface[name].remove(form.name)

        if (ifaces := iface.get('interfaces')) is not None:
            if subifaces is None:
                subifaces = []
            else:
                subifaces = list(subifaces)

            subifaces.append(name)

            for ifname in ifaces:
                self._delFormIface(form, ifname, subifaces=subifaces)

    def delTagProp(self, name):
        return self.tagprops.pop(name)

    def addTagProp(self, name, tdef, info):
        if name in self.tagprops:
            raise s_exc.DupTagPropName(mesg=name)

        prop = TagProp(self, name, tdef, info)
        self.tagprops[name] = prop

        if prop.type.deprecated:
            mesg = f'The tag property {prop.name} is using a deprecated type {prop.type.name} which will' \
                   f' be removed in 3.0.0'
            logger.warning(mesg)

        return prop

    def getTagProp(self, name):
        return self.tagprops.get(name)

    def delFormProp(self, formname, propname):

        form = self.forms.get(formname)
        if form is None:
            raise s_exc.NoSuchForm.init(formname)

        prop = form.delProp(propname)
        if prop is None:
            name = f'{formname}:{propname}'
            mesg = f'No prop {name}'
            raise s_exc.NoSuchProp(mesg=mesg, name=name)

        if isinstance(prop.type, s_types.Array):
            self.arraysbytype[prop.type.arraytype.name].pop(prop.full, None)

        self.props.pop(prop.full, None)
        self.props.pop((form.name, prop.name), None)

        self.propsbytype[prop.type.name].pop(prop.full, None)

    def delUnivProp(self, propname):

        univname = '.' + propname

        univ = self.props.pop(univname, None)
        if univ is None:
            raise s_exc.NoSuchUniv(name=propname)

        self.univs.pop(univname, None)
        self.allunivs.pop(univname, None)

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

    def reqForm(self, name):
        form = self.forms.get(name)
        if form is not None:
            return form

        mesg = f'No form named {name}.'
        raise s_exc.NoSuchForm(mesg=mesg, name=name)

    def univ(self, name):
        return self.univs.get(name)

    def tagprop(self, name):
        return self.tagprops.get(name)

    def edge(self, edgetype):
        return self.edges.get(edgetype)
