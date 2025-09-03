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
import synapse.lib.scope as s_scope
import synapse.lib.types as s_types
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

hexre = regex.compile('^[0-9a-z]+$')

PREFIX_CACHE_SIZE = 1000
CHILDFORM_CACHE_SIZE = 1000
CHILDPROP_CACHE_SIZE = 1000

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

    def getRuntPode(self):
        ndef = ('syn:tagprop', self.name)
        return (ndef, {
            'props': {
                'doc': self.info.get('doc', ''),
                'type': self.type.name,
            },
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
        self.isform = False     # for quick Prop()/Form() detection

        self.full = '%s:%s' % (form.name, name)
        self.isext = name.startswith('_')
        self.isrunt = form.isrunt
        self.compoffs = form.type.getCompOffs(self.name)

        self.setperm = ('node', 'prop', 'set', form.name, self.name)
        self.delperm = ('node', 'prop', 'del', form.name, self.name)

        self.form = form
        self.type = None
        self.typedef = typedef
        self.ifaces = []

        self.alts = None
        self.locked = False
        self.deprecated = self.info.get('deprecated', False)

        self.type = self.modl.getTypeClone(typedef)
        self.typehash = self.type.typehash

        if self.type.isarray:
            self.arraytypehash = self.type.arraytype.typehash

        form.setProp(name, self)
        self.modl.propsbytype[self.type.name][self.full] = self

        if self.deprecated or self.type.deprecated:
            async def depfunc(node):
                mesg = f'The property {self.full} is deprecated or using a deprecated type and will be removed in 4.0.0'
                if (runt := s_scope.get('runt')) is not None:
                    await runt.warnonce(mesg)

                if __debug__:
                    sys.audit('synapse.datamodel.Prop.deprecated', mesg, self.full)

            self.onSet(depfunc)

    def __repr__(self):
        return f'DataModel Prop: {self.full}'

    def reqProtoDef(self, name):

        pdefs = self.info.get('protocols')
        if pdefs is None or (pdef := pdefs.get(name)) is None:
            mesg = f'Property {self.full} does not implement protocol {name}.'
            raise s_exc.NoSuchName(mesg=mesg)

        return pdef

    def onSet(self, func):
        '''
        Add a callback for setting this property.

        The callback is executed after the property is set.

        Args:
            func (function): A prop set callback.

        The callback is called within the current transaction,
        with the node, and the old property value (or None).

        def func(node):
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

        def func(node):
            dostuff()
        '''
        self.ondels.append(func)

    async def wasSet(self, node):
        '''
        Fire the onset() handlers for this property.

        Args:
            node (synapse.lib.node.Node): The node whose property was set.
        '''
        for func in self.onsets:
            try:
                await s_coro.ornot(func, node)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('onset() error for %s' % (self.full,))

    async def wasDel(self, node):
        for func in self.ondels:
            try:
                await s_coro.ornot(func, node)
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

    def getRuntPode(self):

        ndef = ('syn:prop', self.full)

        pode = (ndef, {
            'props': {
                'doc': self.info.get('doc', ''),
                'type': self.type.name,
                'form': self.form.name,
                'relname': self.name,
                'base': self.name.split(':')[-1],
                'ro': int(self.info.get('ro', False)),
                'extmodel': self.isext,
            },
        })

        return pode

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

        self.isext = name.startswith('_')
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
        self._full_ifaces = collections.defaultdict(int)

        self.refsout = None

        self.formtypes = (name,)
        pform = self
        while (pform := modl.form(pform.type.subof)) is not None:
            self.formtypes += (pform.name,)

        self.locked = False
        self.deprecated = self.type.deprecated

        if self.deprecated:
            async def depfunc(node):
                mesg = f'The form {self.full} is deprecated or using a deprecated type and will be removed in 4.0.0'
                if (runt := s_scope.get('runt')) is not None:
                    await runt.warnonce(mesg)

                if __debug__:
                    sys.audit('synapse.datamodel.Form.deprecated', mesg, self.full)

            self.onAdd(depfunc)

        if self.isrunt and (liftfunc := self.info.get('liftfunc')) is not None:
            func = s_dyndeps.tryDynLocal(liftfunc)
            modl.core.addRuntLift(name, func)

    def implements(self, ifname):
        return bool(self._full_ifaces.get(ifname))

    def reqProtoDef(self, name, propname=None):

        if propname is not None:
            return self.reqProp(propname).reqProtoDef(name)

        pdefs = self.info.get('protocols')
        if pdefs is None or (pdef := pdefs.get(name)) is None:
            mesg = f'Form {self.full} does not implement protocol {name}.'
            raise s_exc.NoSuchName(mesg=mesg)

        return pdef

    def getRuntPode(self):

        return (('syn:form', self.full), {
            'props': {
                'doc': self.info.get('doc', self.type.info.get('doc', '')),
                'runt': self.isrunt,
                'type': self.type.name,
            },
        })

    def getRuntPropPode(self):

        return (('syn:prop', self.full), {
            'props': {
                'doc': self.info.get('doc', self.type.info.get('doc', '')),
                'type': self.type.name,
                'extmodel': self.isext,
                'form': self.name,
            },
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
                    if prop.type.name in self.type.pivs:
                        continue
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
        mesg = f'No property named {full}.'

        if (prevname := self.modl.propprevnames.get(full)) is not None:
            mesg += f' Did you mean {prevname}?'

        exc = s_exc.NoSuchProp.init(full, mesg=mesg)
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
        propdefs = [p.getPropDef() for p in self.props.values()]
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
        self._valid_edges = {} #  (n1form, verb, n2form): Edge()
        self.ifaces = {}  # name: <ifdef>
        self.tagprops = {}  # name: TagProp()
        self.formabbr = {}  # name: [Form(), ... ]
        self.modeldefs = []

        self.formprevnames = {}
        self.propprevnames = {}

        self.metatypes = {}  # name: Type()

        self.propsbytype = collections.defaultdict(dict)  # name: Prop()
        self.arraysbytype = collections.defaultdict(dict)
        self.ifaceprops = collections.defaultdict(list)
        self.formsbyiface = collections.defaultdict(list)
        self.edgesbyn1 = collections.defaultdict(set)
        self.edgesbyn2 = collections.defaultdict(set)

        self.childforms = collections.defaultdict(list)
        self.childformcache = s_cache.LruDict(CHILDFORM_CACHE_SIZE)
        self.childpropcache = s_cache.LruDict(CHILDPROP_CACHE_SIZE)

        self.formprefixcache = s_cache.LruDict(PREFIX_CACHE_SIZE)

        self._type_pends = collections.defaultdict(list)
        self._modeldef = {
            'ctors': [],
            'types': [],
            'forms': [],
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

        info = {'doc': 'A time precision value.'}
        item = s_types.TimePrecision(self, 'timeprecision', info, {})
        self.addBaseType(item)

        info = {
            'doc': 'A date/time value.',
            'virts': (
                ('precision', ('timeprecision', {}), {
                    'doc': 'The precision for display and rounding the time.'}),
            ),
        }
        item = s_types.Time(self, 'time', info, {})
        self.addBaseType(item)

        info = {'doc': 'A duration value.'}
        item = s_types.Duration(self, 'duration', info, {})
        self.addBaseType(item)

        info = {
            'virts': (

                ('min', ('time', {}), {
                    'doc': 'The starting time of the interval.'}),

                ('max', ('time', {}), {
                    'doc': 'The ending time of the interval.'}),

                ('duration', ('duration', {}), {
                    'doc': 'The duration of the interval.'}),

                ('precision', ('timeprecision', {}), {
                    'doc': 'The precision for display and rounding the times.'}),
            ),
            'doc': 'A time window or interval.',
        }
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

        info = {
            'virts': (
                ('form', ('syn:form', {}), {
                    'ro': True,
                    'doc': 'The form of node which is referenced.'}),
            ),
            'doc': 'The node definition type for a (form,valu) compound field.',
        }
        item = s_types.Ndef(self, 'ndef', info, {})
        self.addBaseType(item)

        info = {
            'virts': (
                ('size', ('int', {}), {
                    'ro': True,
                    'doc': 'The number of elements in the array.'}),
            ),
            'doc': 'A typed array which indexes each field.'
        }
        item = s_types.Array(self, 'array', info, {'type': 'int'})
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

        self.metatypes['created'] = self.getTypeClone(('time', {'ismin': True}))
        self.metatypes['updated'] = self.getTypeClone(('time', {}))

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

        forms = set()
        for form in self.forms:
            if form.startswith(prefix):
                forms.update(self.getChildForms(form))

        forms = list(forms)
        if forms:
            forms.sort()
            self.formprefixcache[prefix] = forms
        return forms

    def reqProp(self, name, extra=None):
        prop = self.prop(name)
        if prop is not None:
            return prop

        mesg = None
        if (prevname := self.propprevnames.get(name)) is not None:
            mesg = f'No property named {name}. Did you mean {prevname}?'

        exc = s_exc.NoSuchProp.init(name, mesg=mesg)
        if extra is not None:
            raise extra(exc)
        raise exc

    def reqPropList(self, name, extra=None):
        if (prop := self.prop(name)) is not None:
            return self.getChildProps(prop)

        if (props := self.ifaceprops.get(name)) is not None:
            return [self.props.get(prop) for prop in props]

        mesg = None

        if ((prevname := self.propprevnames.get(name)) is not None or
            (prevname := self.formprevnames.get(name)) is not None):
            mesg = f'No property named {name}. Did you mean {prevname}?'

        exc = s_exc.NoSuchProp.init(name, mesg=mesg)
        if extra is not None:
            exc = extra(exc)

        raise exc

    def reqMetaType(self, name, extra=None):
        if (mtyp := self.metatypes.get(name)) is not None:
            return mtyp

        exc = s_exc.NoSuchProp.init(name, mesg=f'No meta property named {name}.')
        if extra is not None:
            exc = extra(exc)

        raise exc

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
            return self.getChildForms(form.name)

        if (forms := self.formsbyiface.get(name)) is not None:
            return forms

        if name.endswith('*'):
            return self.reqFormsByPrefix(name[:-1], extra=extra)

        mesg = None
        if (prevname := self.formprevnames.get(name)) is not None:
            mesg = f'No form named {name}. Did you mean {prevname}?'

        exc = s_exc.NoSuchForm.init(name, mesg=mesg)
        if extra is not None:
            exc = extra(exc)

        raise exc

    def getChildForms(self, formname, depth=0):
        if depth == 0 and (forms := self.childformcache.get(formname)) is not None:
            return forms

        if (kids := self.childforms.get(formname)) is None:
            if depth == 0:
                return (formname,)
            return [(depth, formname)]

        childforms = [(depth, formname)]
        for kid in kids:
            childforms.extend(self.getChildForms(kid, depth=(depth + 1)))

        if depth == 0:
            childforms.sort(reverse=True)
            childforms = [cform[1] for cform in childforms]
            self.childformcache[formname] = childforms

        return childforms

    def getChildProps(self, prop, depth=0):
        if depth == 0 and (props := self.childpropcache.get(prop.full)) is not None:
            return props

        if (kids := self.childforms.get(prop.form.name)) is None:
            if depth == 0:
                return [prop]
            return [(depth, prop)]

        suffix = ''
        if not prop.isform:
            suffix = f':{prop.name}'

        childprops = [(depth, prop)]
        for kid in kids:
            childprop = self.props[f'{kid}{suffix}']
            childprops.extend(self.getChildProps(childprop, depth=(depth + 1)))

        if depth == 0:
            childprops.sort(reverse=True, key=lambda x: (x[0], x[1].name))
            childprops = [cprop[1] for cprop in childprops]
            self.childpropcache[prop.full] = childprops

        return childprops

    def reqPropsByLook(self, name, extra=None):
        if (prop := self.prop(name)) is not None:
            return self.getChildProps(prop)

        if (forms := self.formsbyiface.get(name)) is not None:
            return [self.prop(name) for name in forms]

        if (props := self.ifaceprops.get(name)) is not None:
            return [self.prop(name) for name in props]

        if name.endswith('*'):
            forms = self.reqFormsByPrefix(name[:-1], extra=extra)
            return [self.prop(name) for name in forms]

        mesg = None
        if (prevname := self.propprevnames.get(name)) is not None:
            mesg = f'No property named {name}. Did you mean {prevname}?'

        exc = s_exc.NoSuchProp.init(name, mesg=mesg)
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
        mdef['tagprops'] = [t.getTagPropDef() for t in self.tagprops.values()]
        mdef['interfaces'] = list(self.ifaces.items())
        mdef['edges'] = [e.pack() for e in self.edges.values()]
        return [('all', mdef)]

    def getModelDict(self):
        retn = {
            'metas': (
                ('created', ('time', {}), {
                    'doc': 'The time that the node was created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time that the node was most recently modified.'}),
            ),
            'types': {},
            'forms': {},
            'edges': [],
            'tagprops': {},
            'interfaces': self.ifaces.copy()
        }

        for tobj in self.types.values():
            retn['types'][tobj.name] = tobj.pack()

        for fobj in self.forms.values():
            retn['forms'][fobj.name] = fobj.pack()

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

        ctors = {}

        # load all the base type ctors in order...
        for _, mdef in mods:

            for name, ctor, opts, info in mdef.get('ctors', ()):
                item = s_dyndeps.tryDynFunc(ctor, self, name, info, opts, skipinit=True)
                self.types[name] = item
                ctors[name] = (name, ctor, opts, info)

        # load all the types in order...
        for _, mdef in mods:
            for typename, (basename, typeopts), typeinfo in mdef.get('types', ()):
                self.addType(typename, basename, typeopts, typeinfo, skipinit=True)

        # finish initializing types
        for name, tobj in self.types.items():
            tobj._initType()
            if (info := ctors.get(name)) is not None:
                self._modeldef['ctors'].append(info)
            else:
                self._modeldef['types'].append(tobj.getTypeDef())

        # load all the interfaces...
        for _, mdef in mods:
            for name, info in mdef.get('interfaces', ()):
                self.addIface(name, info)

        # Load all the tagprops
        for _, mdef in mods:
            for tpname, typedef, tpinfo in mdef.get('tagprops', ()):
                self.addTagProp(tpname, typedef, tpinfo)

        formchildren = collections.defaultdict(list)
        formnames = set()
        childforms = set()

        for _, mdef in mods:
            for formname, forminfo, propdefs in mdef.get('forms', ()):
                formnames.add(formname)

            for formname, forminfo, propdefs in mdef.get('forms', ()):
                if (ftyp := self.types.get(formname)) is not None and ftyp.subof in formnames:
                    formchildren[ftyp.subof].append((formname, forminfo, propdefs))
                    childforms.add(formname)

        def addForms(infos, children=False):
            for formname, forminfo, propdefs in infos:
                if formname in childforms and not children:
                    continue

                self.addForm(formname, forminfo, propdefs, checks=False)

                if (cinfos := formchildren.pop(formname, None)) is not None:
                    addForms(cinfos, children=True)

        # now we can load all the forms...
        for _, mdef in mods:
            addForms(mdef.get('forms', ()))

        # load form/prop hooks
        for _, mdef in mods:

            if (hdef := mdef.get('hooks')) is not None:
                if (prehooks := hdef.get('pre')) is not None:
                    for propname, func in prehooks.get('props', ()):
                        self.core._setPropSetHook(propname, func)

                if (posthooks := hdef.get('post')) is not None:
                    for formname, func in posthooks.get('forms', ()):
                        self.form(formname).onAdd(func)

                    for propname, func in posthooks.get('props', ()):
                        self.prop(propname).onSet(func)

        # now we can load edge definitions...
        for _, mdef in mods:
            for etype, einfo in mdef.get('edges', ()):
                self.addEdge(etype, einfo)

        # now we can check the forms display settings...
        for form in self.forms.values():
            self._checkFormDisplay(form)

    def _getFormsMaybeIface(self, name):

        form = self.forms.get(name)
        if form is not None:
            return self.getChildForms(name)

        forms = self.formsbyiface.get(name)
        if forms is None:
            mesg = f'No form or interface named {name}.'
            raise s_exc.NoSuchForm(mesg=mesg, name=name)

        return tuple(forms)

    def addEdge(self, edgetype, edgeinfo):

        n1form, verb, n2form = edgetype

        if not isinstance(verb, str):
            mesg = f'Edge definition verb must be a string: {edgetype}.'
            raise s_exc.BadArg(mesg=mesg)

        if (edge := self.edges.get(edgetype)) is not None:
            # this extra check allows more specific edges to be defined
            # while less specific interface based edges are also present.
            if edge.edgetype == edgetype:
                mesg = f'Duplicate edge declared: {edgetype}.'
                raise s_exc.BadArg(mesg=mesg)

        n1forms = (None,)
        if n1form is not None:
            n1forms = self._getFormsMaybeIface(n1form)

        n2forms = (None,)
        if n2form is not None:
            n2forms = self._getFormsMaybeIface(n2form)

        edge = Edge(self, edgetype, edgeinfo)
        self.edges[edgetype] = edge

        [self.edgesbyn1[n1form].add(edge) for n1form in n1forms]
        [self.edgesbyn2[n2form].add(edge) for n2form in n2forms]

        self._valid_edges[edgetype] = edge
        for n1form in n1forms:
            for n2form in n2forms:
                self._valid_edges[(n1form, verb, n2form)] = edge

    def delEdge(self, edgetype):

        edge = self.edges.get(edgetype)
        if edge is None:
            return

        n1form, verb, n2form = edgetype

        n1forms = (None,)
        if n1form is not None:
            n1forms = self._getFormsMaybeIface(n1form)

        n2forms = (None,)
        if n2form is not None:
            n2forms = self._getFormsMaybeIface(n2form)

        self.edges.pop(edgetype, None)

        [self.edgesbyn1[n1form].discard(edge) for n1form in n1forms]
        [self.edgesbyn2[n2form].discard(edge) for n2form in n2forms]

        self._valid_edges.pop(edgetype, None)
        for n1form in n1forms:
            for n2form in n2forms:
                self._valid_edges.pop((n1form, verb, n2form), None)

    def _reqFormName(self, name):
        form = self.forms.get(name)
        if form is None:
            raise s_exc.NoSuchForm.init(name)
        return form

    def addType(self, typename, basename, typeopts, typeinfo, skipinit=False):
        assert typename not in self.types, f'{typename} type already present in model'
        base = self.types.get(basename)
        if base is None:
            raise s_exc.NoSuchType(name=basename)

        newtype = base.extend(typename, typeopts, typeinfo, skipinit=skipinit)

        if newtype.deprecated:
            mesg = f'The type {typename} is based on a deprecated type {newtype.name} which ' \
                   f'will be removed in 4.0.0.'
            logger.warning(mesg)

        self.types[typename] = newtype

        if not skipinit:
            self._modeldef['types'].append(newtype.getTypeDef())

    def reqVirtTypes(self, virts):

        for (name, tdef, info) in virts:
            if self.types.get(tdef[0]) is None:
                raise s_exc.NoSuchType(name=tdef[0])

    def mergeVirts(self, v0, v1):
        types = {}
        infos = {}

        for (name, typedef, info) in v0:

            if typedef is not None:
                types[name] = typedef

            infos.setdefault(name, {})
            infos[name].update(info)

        for (name, typedef, info) in v1:

            if typedef is not None:
                types[name] = typedef

            infos.setdefault(name, {})
            infos[name].update(info)

        virts = []
        for name, info in infos.items():
            virts.append((name, types.get(name), info))

        return tuple(virts)

    def addForm(self, formname, forminfo, propdefs, checks=True):
        assert formname not in self.forms, f'{formname} form already present in model'

        if not s_grammar.isFormName(formname):
            mesg = f'Invalid form name {formname}'
            raise s_exc.BadFormDef(name=formname, mesg=mesg)

        if (_type := self.types.get(formname)) is None:
            raise s_exc.NoSuchType(name=formname)

        if (pform := self.form(_type.subof)) is not None:
            self.childforms[pform.name].append(formname)
            forminfo = pform.info | forminfo
            propdefs = tuple((prop.name, prop.typedef, prop.info) for prop in pform.props.values()) + propdefs

        virts = []

        if (typevirts := _type.info.get('virts')) is not None:
            virts = self.mergeVirts(virts, typevirts)

        if (formvirts := forminfo.get('virts')) is not None:
            virts = self.mergeVirts(virts, formvirts)

        if virts:
            self.reqVirtTypes(virts)
            forminfo['virts'] = virts

        form = Form(self, formname, forminfo)

        self.forms[formname] = form
        self.props[formname] = form

        if (prevnames := forminfo.get('prevnames')) is not None:
            for prevname in prevnames:
                self.formprevnames[prevname] = formname

        if (prevnames := form.type.info.get('prevnames')) is not None:
            for prevname in prevnames:
                self.formprevnames[prevname] = formname

        if isinstance(form.type, s_types.Array):
            self.arraysbytype[form.type.arraytype.name][form.name] = form

        for propdef in propdefs:

            if len(propdef) != 3:
                raise s_exc.BadPropDef(valu=propdef)

            propname, typedef, propinfo = propdef
            self._addFormProp(form, propname, typedef, propinfo)

        # interfaces are listed in typeinfo for the form to
        # maintain backward compatibility for populated models
        for ifname, ifinfo in form.type.info.get('interfaces', ()):
            self._addFormIface(form, ifname, ifinfo)

        if checks:
            self._checkFormDisplay(form)

        self.childformcache.clear()
        self.formprefixcache.clear()

        return form

    def _checkFormDisplay(self, form):

        formtype = self.types.get(form.type.name)

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

                for i, partname in enumerate(parts):

                    if curf is None and i == (len(parts) - 1):
                        mesg = f'No form named {prop.type.name} for property {prop.full}.'  # noqa: F821
                        raise s_exc.NoSuchForm(mesg=mesg)

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

        if len(childforms := self.getChildForms(formname)) > 1:
            names = ', '.join(childforms[:-1])
            mesg = f'Form has child forms: {names}'
            raise s_exc.CantDelForm(mesg=mesg)

        ifaceprops = set()
        for iface in form.ifaces.values():
            for prop in iface.get('props', ()):
                ifaceprops.add(prop[0])

        parentform = None
        parentprops = set()
        if len(form.formtypes) > 1:
            parentform = self.forms.get(form.formtypes[1])
            parentprops.update([name for name in parentform.props.keys() if name not in ifaceprops])

        formprops = []
        for propname, prop in form.props.items():
            if propname in ifaceprops or propname in parentprops:
                continue
            formprops.append(prop)

        if formprops:
            propnames = ', '.join(prop.name for prop in formprops)
            mesg = f'Form has extended properties: {propnames}'
            raise s_exc.CantDelForm(mesg=mesg)

        if isinstance(form.type, s_types.Array):
            self.arraysbytype[form.type.arraytype.name].pop(form.name, None)

        for ifname, ifinfo in form.type.info.get('interfaces', ()):
            self._delFormIface(form, ifname, ifinfo)

        for propname in parentprops:
            self.delFormProp(formname, propname)

        self.forms.pop(formname, None)
        self.props.pop(formname, None)

        self.childformcache.clear()
        self.formprefixcache.clear()

        if parentform:
            self.childforms[parentform.name].remove(formname)

    def addIface(self, name, info):
        # TODO should we add some meta-props here for queries?
        assert name not in self.ifaces, f'{name} interface already present in model'
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

    def addFormProp(self, formname, propname, tdef, info):
        form = self.forms.get(formname)
        if form is None:
            raise s_exc.NoSuchForm.init(formname)
        return self._addFormProp(form, propname, tdef, info)

    def _addFormProp(self, form, name, tdef, info):

        # TODO - implement resolving tdef from inherited interfaces
        # if omitted from a prop or iface definition to allow doc edits

        _type = self.types.get(tdef[0])
        if _type is None:
            mesg = f'No type named {tdef[0]} while declaring prop {form.name}:{name}.'
            raise s_exc.NoSuchType(mesg=mesg, name=name)

        virts = []
        if (typevirts := _type.info.get('virts')) is not None:
            virts = self.mergeVirts(virts, typevirts)

        if (propvirts := info.get('virts')) is not None:
            virts = self.mergeVirts(virts, propvirts)

        if virts:
            self.reqVirtTypes(virts)
            info['virts'] = virts

        for formname in self.getChildForms(form.name):
            form = self.form(formname)
            prop = Prop(self, form, name, tdef, info)

            # index the array item types
            if isinstance(prop.type, s_types.Array):
                self.arraysbytype[prop.type.arraytype.name][prop.full] = prop

            self.props[prop.full] = prop

            if (prevnames := info.get('prevnames')) is not None:
                for prevname in prevnames:
                    prevfull = f'{form.name}:{prevname}'
                    self.propprevnames[prevfull] = prop.full

        self.childpropcache.clear()

        return prop

    def _reqIface(self, name):
        iface = self.ifaces.get(name)
        if iface is None:
            raise s_exc.NoSuchIface.init(name)
        return iface

    def _prepIfaceTemplate(self, iface, ifinfo, template=None):

        # outer interface templates take precedence
        if template is None:
            template = {}

        for subname, subinfo in iface.get('interfaces', ()):
            subi = self._reqIface(subname)
            self._prepIfaceTemplate(subi, subinfo, template=template)

        template.update(iface.get('template', {}))
        template.update(ifinfo.get('template', {}))

        return template

    def _prepFormIface(self, form, iface, ifinfo):

        prefix = iface.get('prefix')
        prefix = ifinfo.get('prefix', prefix)

        # TODO decide if/how to handle subinterface prefixes
        template = self._prepIfaceTemplate(iface, ifinfo)
        template.update(form.type.info.get('template', {}))
        template['$self'] = form.full

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

        iface = convert(iface)

        if prefix is not None:

            props = []
            for propname, typeinfo, propinfo in iface.get('props'):

                if prefix:
                    if propname:
                        propname = f'{prefix}:{propname}'
                    else:
                        propname = prefix

                # allow a property named by the prefix to fall away if prefix is ""
                if propname:
                    props.append((propname, typeinfo, propinfo))

            iface['props'] = tuple(props)

        return iface

    def _addFormIface(self, form, name, ifinfo, ifaceparents=None):

        iface = self.ifaces.get(name)

        form._full_ifaces[name] += 1

        if iface is None:
            mesg = f'Form {form.name} depends on non-existent interface: {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        if iface.get('deprecated'):
            mesg = f'Form {form.name} depends on deprecated interface {name} which will be removed in 4.0.0'
            logger.warning(mesg)

        iface = self._prepFormIface(form, iface, ifinfo)

        for propname, typedef, propinfo in iface.get('props', ()):

            # allow form props to take precedence
            if (prop := form.prop(propname)) is None:
                prop = self._addFormProp(form, propname, typedef, propinfo)

            iprop = f'{name}:{propname}'
            prop.ifaces.append(iprop)
            self.ifaceprops[iprop].append(prop.full)

            if ifaceparents is not None:
                for iname in ifaceparents:
                    subiprop = f'{iname}:{propname}'
                    prop.ifaces.append(subiprop)
                    self.ifaceprops[subiprop].append(prop.full)

        form.ifaces[name] = iface
        self.formsbyiface[name].append(form.name)

        for subname, subinfo in iface.get('interfaces', ()):

            if ifaceparents is None:
                ifaceparents = [name]
            else:
                ifaceparents.append(name)

            self._addFormIface(form, subname, subinfo, ifaceparents=ifaceparents)

    def _delFormIface(self, form, name, ifinfo, ifaceparents=None):

        if (iface := self.ifaces.get(name)) is None:
            return

        form._full_ifaces[name] -= 1
        iface = self._prepFormIface(form, iface, ifinfo)

        for propname, typedef, propinfo in iface.get('props', ()):
            fullprop = f'{form.name}:{propname}'
            self.delFormProp(form.name, propname)
            self.ifaceprops[f'{name}:{propname}'].remove(fullprop)

            if ifaceparents is not None:
                for iname in ifaceparents:
                    self.ifaceprops[f'{iname}:{propname}'].remove(fullprop)

        form.ifaces.pop(name, None)
        self.formsbyiface[name].remove(form.name)

        for subname, subinfo in iface.get('interfaces', ()):

            if ifaceparents is None:
                ifaceparents = [name]
            else:
                ifaceparents.append(name)

            self._delFormIface(form, subname, subinfo, ifaceparents=ifaceparents)

    def delTagProp(self, name):
        return self.tagprops.pop(name)

    def addTagProp(self, name, tdef, info):
        if name in self.tagprops:
            raise s_exc.DupTagPropName(mesg=name)

        prop = TagProp(self, name, tdef, info)
        self.tagprops[name] = prop

        if prop.type.deprecated:
            mesg = f'The tag property {prop.name} is using a deprecated type {prop.type.name} which will' \
                   f' be removed in 4.0.0'
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

        if (kids := self.childforms.get(formname)) is not None:
            for kid in kids:
                self.delFormProp(kid, propname)

        self.childpropcache.clear()

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
        if (prevname := self.formprevnames.get(name)) is not None:
            mesg += f' Did you mean {prevname}?'

        raise s_exc.NoSuchForm(mesg=mesg, name=name)

    def tagprop(self, name):
        return self.tagprops.get(name)

    def edge(self, edgetype):
        return self._valid_edges.get(edgetype)

    def edgeIsValid(self, n1form, verb, n2form):
        if self._valid_edges.get((n1form, verb, n2form)):
            return True
        if self._valid_edges.get((None, verb, None)):
            return True
        if self._valid_edges.get((None, verb, n2form)):
            return True
        if self._valid_edges.get((n1form, verb, None)):
            return True
        return False
