import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types
import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class SynUser(s_types.Guid):

    def _normPyStr(self, text):

        core = self.modl.core
        if core is not None:

            # direct use of an iden takes precedence...
            user = core.auth.user(text)
            if user is not None:
                return user.iden, {}

            user = core.auth._getUserByName(text)
            if user is not None:
                return user.iden, {}

        if text == '*':
            mesg = f'{self.name} values must be a valid username or a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        try:
            return s_types.Guid._normPyStr(self, text)
        except s_exc.BadTypeValu:
            mesg = f'No user named {text} and value is not a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

    def repr(self, iden):

        core = self.modl.core
        if core is not None:
            user = core.auth.user(iden)
            if user is not None:
                return user.name

        return iden

class SynRole(s_types.Guid):

    def _normPyStr(self, text):

        core = self.modl.core
        if core is not None:

            # direct use of an iden takes precedence...
            role = core.auth.role(text)
            if role is not None:
                return role.iden, {}

            role = core.auth._getRoleByName(text)
            if role is not None:
                return role.iden, {}

        if text == '*':
            mesg = f'{self.name} values must be a valid rolename or a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        try:
            return s_types.Guid._normPyStr(self, text)
        except s_exc.BadTypeValu:
            mesg = f'No role named {text} and value is not a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

    def repr(self, iden):

        core = self.modl.core
        if core is not None:
            role = core.auth.role(iden)
            if role is not None:
                return role.name

        return iden

class SynModule(s_module.CoreModule):

    def initCoreModule(self):

        for form, lifter in (('syn:cmd', self._liftRuntSynCmd),
                             ('syn:cron', self._liftRuntSynCron),
                             ('syn:form', self._liftRuntSynForm),
                             ('syn:prop', self._liftRuntSynProp),
                             ('syn:type', self._liftRuntSynType),
                             ('syn:tagprop', self._liftRuntSynTagProp),
                             ('syn:trigger', self._liftRuntSynTrigger),
                             ):
            form = self.model.form(form)
            self.core.addRuntLift(form.full, lifter)
            for _, prop in form.props.items():
                pfull = prop.full
                self.core.addRuntLift(pfull, lifter)

    async def _liftRuntSynCmd(self, full, valu=None, cmpr=None, view=None):

        def iterStormCmds():
            for item in self.core.getStormCmds():
                yield item[1]

        async for node in self._doRuntLift(iterStormCmds, full, valu, cmpr):
            yield node

    async def _liftRuntSynCron(self, full, valu=None, cmpr=None, view=None):

        def iterAppts():
            for item in self.core.agenda.list():
                yield item[1]

        async for node in self._doRuntLift(iterAppts, full, valu, cmpr):
            yield node

    async def _liftRuntSynForm(self, full, valu=None, cmpr=None, view=None):

        def getForms():
            return list(self.model.forms.values())

        async for node in self._doRuntLift(getForms, full, valu, cmpr):
            yield node

    async def _liftRuntSynProp(self, full, valu=None, cmpr=None, view=None):

        genr = self.model.getProps

        async for node in self._doRuntLift(genr, full, valu, cmpr):
            yield node

    async def _liftRuntSynType(self, full, valu=None, cmpr=None, view=None):

        def getTypes():
            return list(self.model.types.values())

        async for node in self._doRuntLift(getTypes, full, valu, cmpr):
            yield node

    async def _liftRuntSynTagProp(self, full, valu=None, cmpr=None, view=None):

        def getTagProps():
            return list(self.model.tagprops.values())

        async for node in self._doRuntLift(getTagProps, full, valu, cmpr):
            yield node

    async def _liftRuntSynTrigger(self, full, valu=None, cmpr=None, view=None):

        view = self.core.getView(iden=view)

        def iterTriggers():
            for item in view.triggers.list():
                yield item[1]

        async for node in self._doRuntLift(iterTriggers, full, valu, cmpr):
            yield node

    async def _doRuntLift(self, genr, full, valu=None, cmpr=None):

        if cmpr is not None:
            filt = self.model.prop(full).type.getCmprCtor(cmpr)(valu)
            if filt is None:
                raise s_exc.BadCmprValu(cmpr=cmpr)

        fullprop = self.model.prop(full)
        if fullprop.isform:

            if cmpr is None:
                for obj in genr():
                    yield obj.getStorNode(fullprop)
                return

            for obj in genr():
                sode = obj.getStorNode(fullprop)
                if filt(sode[1]['ndef'][1]):
                    yield sode
        else:
            for obj in genr():
                sode = obj.getStorNode(fullprop.form)
                propval = sode[1]['props'].get(fullprop.name)

                if propval is not None and (cmpr is None or filt(propval)):
                    yield sode

    def getModelDefs(self):

        return (('syn', {

            'ctors': (
                ('syn:user', 'synapse.models.syn.SynUser', {}, {
                    'doc': 'A Synapse user.'}),

                ('syn:role', 'synapse.models.syn.SynRole', {}, {
                    'doc': 'A Synapse role.'}),
            ),
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
                ('syn:nodedata', ('comp', {'fields': (('key', 'str'), ('form', 'syn:form'))}), {
                    'doc': 'A nodedata key and the form it may be present on.',
                }),
            ),

            'forms': (

                ('syn:tag', {}, (

                    ('up', ('syn:tag', {}), {'ro': True,
                        'doc': 'The parent tag for the tag.'}),

                    ('isnow', ('syn:tag', {}), {
                        'doc': 'Set to an updated tag if the tag has been renamed.'}),

                    ('doc', ('str', {}), {
                        'doc': 'A short definition for the tag.',
                        'disp': {'hint': 'text'},
                    }),

                    ('doc:url', ('inet:url', {}), {
                        'doc': 'A URL link to additional documentation about the tag.'}),

                    ('depth', ('int', {}), {'ro': True,
                        'doc': 'How deep the tag is in the hierarchy.'}),

                    ('title', ('str', {}), {'doc': 'A display title for the tag.'}),

                    ('base', ('str', {}), {'ro': True,
                        'doc': 'The tag base name. Eg baz for foo.bar.baz .'}),
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
                    ('base', ('str', {'strip': True}), {
                        'doc': 'Base name of the property.', 'ro': True}),
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
                        'doc': 'Trigger version.', 'ro': True,
                    }),
                    ('doc', ('str', {}), {
                        'doc': 'A documentation string describing the trigger.',
                        'disp': {'hint': 'text'},
                    }),
                    ('name', ('str', {}), {
                        'doc': 'A user friendly name/alias for the trigger.',
                    }),
                    ('cond', ('str', {'strip': True, 'lower': True}), {
                        'doc': 'The trigger condition.', 'ro': True,
                    }),
                    ('user', ('str', {}), {
                        'doc': 'User who owns the trigger.', 'ro': True,
                    }),
                    ('storm', ('str', {}), {
                        'doc': 'The Storm query for the trigger.', 'ro': True,
                        'disp': {'hint': 'text'},
                    }),
                    ('enabled', ('bool', {}), {
                        'doc': 'Trigger enabled status.', 'ro': True,
                    }),
                    ('form', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Form the trigger is watching for.'
                    }),
                    ('verb', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Edge verb the trigger is watching for.'
                    }),
                    ('n2form', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'N2 form the trigger is watching for.'
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
                        'doc': 'A description of the cron job.',
                        'disp': {'hint': 'text'},
                    }),

                    ('name', ('str', {}), {
                        'doc': 'A user friendly name/alias for the cron job.'}),

                    ('storm', ('str', {}), {
                        'ro': True,
                        'doc': 'The storm query executed by the cron job.',
                        'disp': {'hint': 'text'},
                    }),

                )),
                ('syn:cmd', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'Description of the command.',
                        'disp': {'hint': 'text'},
                    }),
                    ('package', ('str', {'strip': True}), {
                        'doc': 'Storm package which provided the command.'}),
                    ('svciden', ('guid', {'strip': True}), {
                        'doc': 'Storm service iden which provided the package.'}),
                    ('input', ('array', {'type': 'syn:form'}), {
                        'deprecated': True,
                        'doc': 'The list of forms accepted by the command as input.', 'uniq': True, 'sorted': True, 'ro': True}),
                    ('output', ('array', {'type': 'syn:form'}), {
                        'deprecated': True,
                        'doc': 'The list of forms produced by the command as output.', 'uniq': True, 'sorted': True, 'ro': True}),
                    ('nodedata', ('array', {'type': 'syn:nodedata'}), {
                        'deprecated': True,
                        'doc': 'The list of nodedata that may be added by the command.', 'uniq': True, 'sorted': True, 'ro': True}),
                )),
            ),
        }),)
