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

        # Static runt data for triggers
        self._triggerRuntsByBuid = {}
        self._triggerRuntsByPropValu = collections.defaultdict(list)

        # Static runt data for commands
        self._cmdRuntsByBuid = {}
        self._cmdRuntsByPropValu = collections.defaultdict(list)

        # Add runt lift helpers
        for form, lifter in (('syn:type', self._synModelLift),
                             ('syn:form', self._synModelLift),
                             ('syn:prop', self._synModelLift),
                             ('syn:tagprop', self._synModelLift),
                             ('syn:trigger', self._synTriggerLift),
                             ('syn:cmd', self._synCmdLift),
                             ):
            form = self.model.form(form)
            self.core.addRuntLift(form.full, lifter)
            for name, prop in form.props.items():
                pfull = prop.full
                self.core.addRuntLift(pfull, lifter)

        # add event registration for model changes to allow for new models to reset the runtime model data
        self.core.on('core:module:load', self._onCoreModelChange)
        self.core.on('core:tagprop:change', self._onCoreModelChange)
        self.core.on('core:extmodel:change', self._onCoreModelChange)
        self.core.on('core:trigger:action', self._onCoreTriggerMod)
        self.core.on('core:cmd:change', self._onCoreCmdChange)

    def _onCoreCmdChange(self, event):
        '''
        Clear the cached command rows.
        '''
        if not self._cmdRuntsByBuid:
            return
        # Discard previously cached data. It will be computed upon the next
        # lift that needs it.
        self._cmdRuntsByBuid.clear()
        self._cmdRuntsByPropValu.clear()

    def _onCoreTriggerMod(self, event):
        '''
        Clear the cached trigger rows.
        '''
        if not self._triggerRuntsByBuid:
            return
        # Discard previously cached data. It will be computed upon the next
        # lift that needs it.
        self._triggerRuntsByBuid.clear()
        self._triggerRuntsByPropValu.clear()

    def _onCoreModelChange(self, event):
        '''
        Clear the cached model rows.
        '''
        if not self._modelRuntsByBuid:
            return
        # Discard previously cached data. It will be computed upon the next
        # lift that needs it.
        self._modelRuntsByBuid.clear()
        self._modelRuntsByPropValu.clear()

    async def _synCmdLift(self, full, valu=None, cmpr=None):
        if not self._cmdRuntsByBuid:
            await self._initCmdRunts()

        if cmpr is not None and cmpr != '=':
            raise s_exc.BadCmprValu(mesg='Command runtime nodes only support equality comparator.',
                                    cmpr=cmpr)

        if valu is None:
            buids = self._cmdRuntsByPropValu.get(full, ())
        else:
            prop = self.model.prop(full)
            valu, _ = prop.type.norm(valu)
            buids = self._cmdRuntsByPropValu.get((full, valu), ())

        rowsets = [(buid, self._cmdRuntsByBuid.get(buid, ())) for buid in buids]
        for buid, rows in rowsets:
            yield buid, rows

    async def _synTriggerLift(self, full, valu=None, cmpr=None):
        if not self._triggerRuntsByBuid:
            await self._initTriggerRunts()

        if cmpr is not None and cmpr != '=':
            raise s_exc.BadCmprValu(mesg='Trigger runtime nodes only support equality comparator.',
                                    cmpr=cmpr)

        if valu is None:
            buids = self._triggerRuntsByPropValu.get(full, ())
        else:
            prop = self.model.prop(full)
            valu, _ = prop.type.norm(valu)
            buids = self._triggerRuntsByPropValu.get((full, valu), ())

        rowsets = [(buid, self._triggerRuntsByBuid.get(buid, ())) for buid in buids]
        for buid, rows in rowsets:
            yield buid, rows

    async def _synModelLift(self, full, valu=None, cmpr=None):
        if not self._modelRuntsByBuid:
            self._initModelRunts()

        if cmpr is not None and cmpr != '=':
            raise s_exc.BadCmprValu(mesg='Model runtime nodes only support equality comparator.',
                                    cmpr=cmpr)

        if valu is None:
            buids = self._modelRuntsByPropValu.get(full, ())
        else:
            prop = self.model.prop(full)
            valu, _ = prop.type.norm(valu)
            buids = self._modelRuntsByPropValu.get((full, valu), ())

        rowsets = [(buid, self._modelRuntsByBuid.get(buid, ())) for buid in buids]
        for buid, rows in rowsets:
            yield buid, rows

    def _addRuntRows(self, form, valu, props, buidcache, propcache):
        buid = s_common.buid((form, valu))
        if buid in buidcache:
            return

        rows = [('*' + form, valu)]
        props.setdefault('.created', s_common.now())
        for k, v in props.items():
            rows.append((k, v))

        buidcache[buid] = rows

        propcache[form].append(buid)
        propcache[(form, valu)].append(buid)

        for k, propvalu in props.items():
            prop = form + ':' + k
            if k.startswith('.'):
                prop = form + k
            propcache[prop].append(buid)
            # Can the secondary property be indexed for lift?
            if self.model.prop(prop).type.indx(propvalu):
                propcache[(prop, propvalu)].append(buid)

    async def _initCmdRunts(self):
        now = s_common.now()
        typeform = self.model.form('syn:cmd')

        for name, ctor in self.core.getStormCmds():
            tnorm, _ = typeform.type.norm(name)

            props = {'.created': now,
                     'doc': ctor.getCmdBrief(),
                     }

            forms = ctor.forms

            inputs = forms.get('input')
            if inputs:
                props['input'] = tuple(inputs)

            outputs = forms.get('output')
            if outputs:
                props['output'] = tuple(outputs)

            if ctor.svciden:
                props['svciden'] = ctor.svciden

            if ctor.pkgname:
                props['package'] = ctor.pkgname

            self._addRuntRows('syn:cmd', tnorm, props,
                              self._cmdRuntsByBuid, self._cmdRuntsByPropValu)

    async def _initTriggerRunts(self):
        now = s_common.now()
        typeform = self.model.form('syn:trigger')
        for iden, trig in await self.core.listTriggers():

            tnorm, _ = typeform.type.norm(iden)

            props = {'.created': now,
                     'doc': trig.doc,
                     'name': trig.name,
                     'vers': trig.ver,
                     'cond': trig.cond,
                     'storm': trig.storm,
                     'enabled': trig.enabled,
                     'user': self.core.getUserName(trig.useriden),
                     }

            if trig.tag is not None:
                props['tag'] = trig.tag
            if trig.form is not None:
                props['form'] = trig.form
            if trig.prop is not None:
                props['prop'] = trig.prop

            self._addRuntRows('syn:trigger', tnorm, props,
                              self._triggerRuntsByBuid, self._triggerRuntsByPropValu)

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
            self._addRuntRows('syn:type', tnorm, props,
                              self._modelRuntsByBuid, self._modelRuntsByPropValu)

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

            self._addRuntRows('syn:form', fnorm, props,
                              self._modelRuntsByBuid, self._modelRuntsByPropValu)

        propform = self.model.form('syn:prop')

        for pname, pobj in self.model.props.items():
            if isinstance(pname, tuple):
                continue

            pnorm, _ = propform.type.norm(pname)

            ro, _ = self.model.prop('syn:prop:ro').type.norm(pobj.info.get('ro', False))

            ptype, _ = self.model.prop('syn:prop:type').type.norm(pobj.type.name)

            univ = False
            extmodel = False

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
                if pobj.name.startswith('._'):
                    extmodel = True

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
                univ = pobj.storinfo.get('univ', False)
                if relname.startswith(('_', '._')):
                    extmodel = True

            univ, _ = self.model.prop('syn:prop:univ').type.norm(univ)
            extmodel, _ = self.model.prop('syn:prop:extmodel').type.norm(extmodel)
            props['univ'] = univ
            props['extmodel'] = extmodel

            self._addRuntRows('syn:prop', pnorm, props,
                              self._modelRuntsByBuid, self._modelRuntsByPropValu)

        tpform = self.model.form('syn:tagprop')
        for tpname, tpobj in self.model.tagprops.items():
            tpnorm, _ = tpform.type.norm(tpname)
            tptype, _ = self.model.prop('syn:tagprop:type').type.norm(tpobj.type.name)
            doc = tpobj.info.get('doc', 'no docstring')

            props = {'doc': doc, 'type': tptype}
            self._addRuntRows('syn:tagprop', tpnorm, props,
                              self._modelRuntsByBuid, self._modelRuntsByPropValu)

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
                }),
                ('syn:tagprop', ('str', {'strip': True}), {
                    'doc': 'A user defined tag property.'
                }),
                ('syn:cron', ('guid', {}), {
                    'doc': 'A Cortex cron job.',
                }),
                ('syn:trigger', ('guid', {}), {
                    'doc': 'A Cortex trigger.'
                }),
                ('syn:cmd', ('str', {'strip': True}), {
                    'doc': 'A Synapse storm command.'
                }),
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
                    ('extmodel', ('bool', {}), {
                        'doc': 'If the property is an extended model property or not.', 'ro': True}),
                )),
                ('syn:tagprop', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'Description of the tagprop definition.'}),
                    ('type', ('syn:type', {}), {
                        'doc': 'The synapse type for this tagprop.', 'ro': True}),
                )),
                ('syn:trigger', {'runt': True}, (
                    ('vers', ('int', {}), {
                        'doc': 'Trigger version', 'ro': True,
                    }),
                    ('doc', ('str', {}), {
                        'doc': 'A documentation string describing the trigger.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'A user friendly name/alias for the trigger.',
                    }),
                    ('cond', ('str', {'strip': True, 'lower': True}), {
                        'doc': 'The trigger condition', 'ro': True,
                    }),
                    ('user', ('str', {}), {
                        'doc': 'User who owns the trigger', 'ro': True,
                    }),
                    ('storm', ('str', {}), {
                        'doc': 'The Storm query for the trigger.', 'ro': True,
                    }),
                    ('enabled', ('bool', {}), {
                        'doc': 'Trigger enabled status', 'ro': True,
                    }),
                    ('form', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Form the trigger is watching for.'
                    }),
                    ('prop', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Property the trigger is watching for.'
                    }),
                    ('tag', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Tag the trigger is watching for.'
                    }),
                )),
                ('syn:cron', {'runt': True}, (

                    ('doc', ('str', {}), {
                        'doc': 'A description of the cron job.'}),

                    ('name', ('str', {}), {
                        'doc': 'A user friendly name/alias for the cron job.'}),

                    ('storm', ('str', {}), {
                        'ro': True,
                        'doc': 'The storm query executed by the cron job.'}),

                )),
                ('syn:cmd', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'Description of the command.'}),
                    ('package', ('str', {'strip': True}), {
                        'doc': 'Storm package which provided the command.'}),
                    ('svciden', ('guid', {'strip': True}), {
                        'doc': 'Storm service iden which provided the package.'}),
                    ('input', ('array', {'type': 'syn:form'}), {
                        'doc': 'The list of forms accepted by the command as input.', 'ro': True}),
                    ('output', ('array', {'type': 'syn:form'}), {
                        'doc': 'The list of forms produced by the command as output.', 'ro': True}),
                )),
            ),
        }),)
