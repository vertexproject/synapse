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

        self.core.addRuntLift('syn:cmd', self._liftRuntSynCmd)
        self.core.addRuntLift('syn:form', self._liftRuntSynForm)
        self.core.addRuntLift('syn:prop', self._liftRuntSynProp)
        self.core.addRuntLift('syn:type', self._liftRuntSynType)
        self.core.addRuntLift('syn:tagprop', self._liftRuntSynTagProp)

    async def _liftRuntSynCmd(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.core.stormcmds.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.core.getStormCmds():
            yield item[1].getRuntPode()

    async def _liftRuntSynForm(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.form(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in list(self.model.forms.values()):
            yield item.getRuntPode()

    async def _liftRuntSynProp(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.prop(cmprvalu[1])
            if item is not None:
                if item.isform:
                    yield item.getRuntPropPode()
                else:
                    yield item.getRuntPode()
            return

        for item in self.model.getProps():
            if item.isform:
                yield item.getRuntPropPode()
            else:
                yield item.getRuntPode()

    async def _liftRuntSynType(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.type(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in list(self.model.types.values()):
            yield item.getRuntPode()

    async def _liftRuntSynTagProp(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.tagprops.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in list(self.model.tagprops.values()):
            yield item.getRuntPode()

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
                ('syn:cmd', ('str', {'strip': True}), {
                    'doc': 'A Synapse storm command.'
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
                ('syn:cmd', {'runt': True}, (
                    ('doc', ('str', {'strip': True}), {
                        'doc': 'Description of the command.',
                        'disp': {'hint': 'text'},
                    }),
                    ('package', ('str', {'strip': True}), {
                        'doc': 'Storm package which provided the command.'}),
                    ('svciden', ('guid', {'strip': True}), {
                        'doc': 'Storm service iden which provided the package.'}),
                )),
            ),
        }),)
