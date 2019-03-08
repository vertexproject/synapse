import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class SynModule(s_module.CoreModule):

    def initCoreModule(self):

        # Static runt data for model data
        self._modelRuntsByBuid = {}
        self._modelRuntsByPropValu = collections.defaultdict(list)

        # Add runt lift helpers
        for form in ('syn:type', 'syn:form', 'syn:prop'):
            form = self.model.form(form)
            self.core.addRuntLift(form.full, self._synModelLift)
            for name, prop in form.props.items():
                pfull = prop.full
                self.core.addRuntLift(pfull, self._synModelLift)

        # add event registration for model changes to allow for new models to reset the runtime model data
        self.core.on('core:module:load', self._onCoreModuleLoad)

    def _onCoreModuleLoad(self, event):
        '''
        Clear the cached model rows and rebuild them only if they have been loaded already.
        '''
        if not self._modelRuntsByBuid:
            return
        # Discard previously cached data. It will be computed upon the next
        # lift that needs it.
        self._modelRuntsByBuid = {}
        self._modelRuntsByPropValu = collections.defaultdict(list)

    async def _synModelLift(self, full, valu=None, cmpr=None):
        if not self._modelRuntsByBuid:
            self._initModelRunts()

        # runt lift helpers must decide what comparators they support
        if cmpr is not None and cmpr != '=':
            raise s_exc.BadCmprValu(mesg='Model runtime nodes only support equality comparator.',
                                    cmpr=cmpr)

        # Runt lift helpers must support their own normalization for data retrieval
        if valu is not None:
            prop = self.model.prop(full)
            valu, _ = prop.type.norm(valu)

        # runt lift helpers must then yield buid/rows pairs for Node object creation.
        if valu is None:
            buids = self._modelRuntsByPropValu.get(full, ())
        else:
            buids = self._modelRuntsByPropValu.get((full, valu), ())

        rowsets = [(buid, self._modelRuntsByBuid.get(buid, ())) for buid in buids]
        for buid, rows in rowsets:
            yield buid, rows

    def _addModelRuntRows(self, form, valu, props):
        buid = s_common.buid((form, valu))
        if buid in self._modelRuntsByBuid:
            return

        rows = [('*' + form, valu)]
        props.setdefault('.created', s_common.now())
        for k, v in props.items():
            rows.append((k, v))

        self._modelRuntsByBuid[buid] = rows

        self._modelRuntsByPropValu[form].append(buid)
        self._modelRuntsByPropValu[(form, valu)].append(buid)

        for k, propvalu in props.items():
            prop = form + ':' + k
            if k.startswith('.'):
                prop = form + k
            self._modelRuntsByPropValu[prop].append(buid)
            # Can the secondary property be indexed for lift?
            if self.model.prop(prop).type.indx(propvalu):
                self._modelRuntsByPropValu[(prop, propvalu)].append(buid)

    def _initModelRunts(self):

        tdocs = {}

        now = s_common.now()
        typeform = self.model.form('syn:type')
        for tname, tobj in self.model.types.items():
            tnorm, _ = typeform.type.norm(tname)
            ctor = '.'.join([tobj.__class__.__module__, tobj.__class__.__qualname__])
            ctor, _ = self.model.prop('syn:type:ctor').type.norm(ctor)

            doc = tobj.info.get('doc', 'no docstring')
            doc, _ = self.model.prop('syn:type:doc').type.norm(doc)
            tdocs[tname] = doc
            opts = {k: v for k, v in tobj.opts.items()}

            props = {'doc': doc,
                     'ctor': ctor,
                     '.created': now}
            if opts:
                opts, _ = self.model.prop('syn:type:opts').type.norm(opts)
                props['opts'] = opts
            subof = tobj.subof
            if subof is not None:
                subof, _ = self.model.prop('syn:type:subof').type.norm(subof)
                props['subof'] = subof
            self._addModelRuntRows('syn:type', tnorm, props)

        formform = self.model.form('syn:form')
        for fname, fobj in self.model.forms.items():
            fnorm, _ = formform.type.norm(fname)

            runt, _ = self.model.prop('syn:form:runt').type.norm(fobj.isrunt)

            ptype, _ = self.model.prop('syn:form:type').type.norm(fobj.type.name)

            doc = fobj.info.get('doc', tdocs.get(ptype))
            doc, _ = self.model.prop('syn:form:doc').type.norm(doc)
            tdocs[fnorm] = doc

            props = {'doc': doc,
                     'runt': runt,
                     'type': ptype,
                     '.created': now,
                     }

            self._addModelRuntRows('syn:form', fnorm, props)

        propform = self.model.form('syn:prop')

        for pname, pobj in self.model.props.items():
            if isinstance(pname, tuple):
                continue

            pnorm, _ = propform.type.norm(pname)

            ro, _ = self.model.prop('syn:prop:ro').type.norm(pobj.info.get('ro', False))

            ptype, _ = self.model.prop('syn:prop:type').type.norm(pobj.type.name)

            univ = False

            doc = pobj.info.get('doc', 'no docstring')
            doc, _ = self.model.prop('syn:prop:doc').type.norm(doc)

            props = {'doc': doc,
                     'type': ptype,
                     '.created': now,
                     }

            defval = pobj.info.get('defval', s_common.novalu)
            if defval is not s_common.novalu:
                if not isinstance(defval, (str, int)):
                    defval = repr(defval)
                defval, _ = self.model.prop('syn:prop:defval').type.norm(defval)
                props['defval'] = defval

            if isinstance(pobj, s_datamodel.Univ):
                univ = True
                props['ro'] = ro

            elif isinstance(pobj, s_datamodel.Form):
                fnorm, _ = self.model.prop('syn:prop:form').type.norm(pobj.full)
                props['form'] = fnorm
                # All smashing a docstring in for a prop which is a form
                if doc == 'no docstring':
                    doc = tdocs.get(ptype, 'no docstring')
                    doc, _ = self.model.prop('syn:prop:doc').type.norm(doc)
                    props['doc'] = doc

            else:
                fnorm, _ = self.model.prop('syn:prop:form').type.norm(pobj.form.full)
                relname, _ = self.model.prop('syn:prop:relname').type.norm(pobj.name)
                base, _ = self.model.prop('syn:prop:base').type.norm(pobj.name.rsplit(':', 1)[-1])
                props['ro'] = ro
                props['form'] = fnorm
                props['base'] = base
                props['relname'] = relname

            univ, _ = self.model.prop('syn:prop:univ').type.norm(univ)
            props['univ'] = univ

            self._addModelRuntRows('syn:prop', pnorm, props)

    def getModelDefs(self):

        return (('syn', {

            'types': (
                ('syn:type', ('str', {'strip': True}), {
                    'doc': 'A Synapse type used for normalizing nodes and properties.',
                }),
                ('syn:form', ('str', {'strip': True}), {
                    'doc': 'A Synapse form used for representing nodes in the graph.',
                }),
                ('syn:prop', ('str', {'strip': True}), {
                    'doc': 'A Synapse property.'
                })
            ),

            'forms': (

                ('syn:tag', {}, (

                    ('up', ('syn:tag', {}), {'ro': 1,
                        'doc': 'The parent tag for the tag.'}),

                    ('isnow', ('syn:tag', {}), {
                        'doc': 'Set to an updated tag if the tag has been renamed.'}),

                    ('doc', ('str', {}), {'defval': '',
                        'doc': 'A short definition for the tag.'}),

                    ('depth', ('int', {}), {'ro': 1,
                        'doc': 'How deep the tag is in the hierarchy.'}),

                    ('title', ('str', {}), {'defval': '',
                        'doc': 'A display title for the tag.'}),

                    ('base', ('str', {}), {'ro': 1,
                        'doc': 'The tag base name. Eg baz for foo.bar.baz'}),
                )),
                ('syn:type', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'The docstring for the type.', 'ro': True}),
                    ('ctor', ('str', {'strip': True}), {
                        'doc': 'The python ctor path for the type object.', 'ro': True}),
                    ('subof', ('syn:type', {}), {
                        'doc': 'Type which this inherits from.', 'ro': True}),
                    ('opts', ('data', {}), {
                        'doc': 'Arbitrary type options.', 'ro': True})
                )),
                ('syn:form', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'The docstring for the form.', 'ro': True}),
                    ('type', ('syn:type', {}), {
                        'doc': 'Synapse type for this form.', 'ro': True}),
                    ('runt', ('bool', {}), {
                        'doc': 'Whether or not the form is runtime only.', 'ro': True})
                )),
                ('syn:prop', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'Description of the property definition.'}),
                    ('form', ('syn:form', {}), {
                        'doc': 'The form of the property.', 'ro': True}),
                    ('type', ('syn:type', {}), {
                        'doc': 'The synapse type for this property.', 'ro': True}),
                    ('relname', ('str', {'strip': True}), {
                        'doc': 'Relative property name.', 'ro': True}),
                    ('univ', ('bool', {}), {
                        'doc': 'Specifies if a prop is universal.', 'ro': True}),
                    ('defval', ('str', {}), {
                        'doc': 'Set to the python repr of the default value for this property', 'ro': True}),
                    ('base', ('str', {'strip': True}), {
                        'doc': 'Base name of the property', 'ro': True}),
                    ('ro', ('bool', {}), {
                        'doc': 'If the property is read-only after being set.', 'ro': True}),
                )),

            ),
        }),)
