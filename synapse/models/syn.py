import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

class SynUser(s_types.Guid):

    async def _normPyStr(self, text, view=None):

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
            return await s_types.Guid._normPyStr(self, text)
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

    async def _normPyStr(self, text, view=None):

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
            return await s_types.Guid._normPyStr(self, text)
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

async def _liftRuntSynCmd(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = view.core.stormcmds.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in view.core.getStormCmds():
        yield item[1].getRuntPode()

async def _liftRuntSynForm(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.form(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.forms.values()):
        yield item.getRuntPode()

async def _liftRuntSynProp(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.prop(cmprvalu[1])
        if item is not None:
            if item.isform:
                yield item.getRuntPropPode()
            else:
                yield item.getRuntPode()
        return

    for item in prop.modl.getProps():
        if item.isform:
            yield item.getRuntPropPode()
        else:
            yield item.getRuntPode()

async def _liftRuntSynType(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.type(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.types.values()):
        yield item.getRuntPode()

async def _liftRuntSynTagProp(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.tagprops.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.tagprops.values()):
        yield item.getRuntPode()


modeldefs = (
    ('syn', {

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
            ('syn:deleted', ('ndef', {}), {
                'doc': 'A node present below the write layer which has been deleted.'
            }),
        ),

        'forms': (

            ('syn:tag', {}, (

                ('up', ('syn:tag', {}), {
                    'readonly': True,
                    'doc': 'The parent tag for the tag.'}),

                ('isnow', ('syn:tag', {}), {
                    'doc': 'Set to an updated tag if the tag has been renamed.'}),

                ('doc', ('text', {}), {
                    'doc': 'A short definition for the tag.'}),

                ('doc:url', ('inet:url', {}), {
                    'doc': 'A URL link to additional documentation about the tag.'}),

                ('depth', ('int', {}), {
                    'readonly': True,
                    'doc': 'How deep the tag is in the hierarchy.'}),

                ('title', ('str', {}), {'doc': 'A display title for the tag.'}),

                ('base', ('str', {}), {
                    'readonly': True,
                    'doc': 'The tag base name. Eg baz for foo.bar.baz .'}),
            )),
            ('syn:type', {'runt': True, 'liftfunc': 'synapse.models.syn._liftRuntSynType'}, (

                ('doc', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'The docstring for the type.'}),

                ('ctor', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'The python ctor path for the type object.'}),

                ('subof', ('syn:type', {}), {
                    'readonly': True,
                    'doc': 'Type which this inherits from.'}),

                ('opts', ('data', {}), {
                    'readonly': True,
                    'doc': 'Arbitrary type options.'}),
            )),
            ('syn:form', {'runt': True, 'liftfunc': 'synapse.models.syn._liftRuntSynForm'}, (

                ('doc', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'The docstring for the form.'}),

                ('type', ('syn:type', {}), {
                    'readonly': True,
                    'doc': 'Synapse type for this form.'}),

                ('runt', ('bool', {}), {
                    'readonly': True,
                    'doc': 'Whether or not the form is runtime only.'}),
            )),
            ('syn:prop', {'runt': True, 'liftfunc': 'synapse.models.syn._liftRuntSynProp'}, (

                ('doc', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'Description of the property definition.'}),

                ('form', ('syn:form', {}), {
                    'readonly': True,
                    'doc': 'The form of the property.'}),

                ('type', ('syn:type', {}), {
                    'readonly': True,
                    'doc': 'The synapse type for this property.'}),

                ('relname', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'Relative property name.'}),

                ('univ', ('bool', {}), {
                    'readonly': True,
                    'doc': 'Specifies if a prop is universal.'}),

                ('base', ('str', {'strip': True}), {
                    'readonly': True,
                    'doc': 'Base name of the property.'}),

                ('readonly', ('bool', {}), {
                    'readonly': True,
                    'doc': 'If the property is read-only after being set.'}),

                ('extmodel', ('bool', {}), {
                    'readonly': True,
                    'doc': 'If the property is an extended model property or not.'}),
            )),
            ('syn:tagprop', {'runt': True, 'liftfunc': 'synapse.models.syn._liftRuntSynTagProp'}, (
                ('doc', ('str', {'strip': True}), {
                    'doc': 'Description of the tagprop definition.'}),
                ('type', ('syn:type', {}), {
                    'doc': 'The synapse type for this tagprop.', 'readonly': True}),
            )),
            ('syn:cmd', {'runt': True, 'liftfunc': 'synapse.models.syn._liftRuntSynCmd'}, (

                ('doc', ('text', {'strip': True}), {
                    'doc': 'Description of the command.'}),

                ('package', ('str', {'strip': True}), {
                    'doc': 'Storm package which provided the command.'}),

                ('svciden', ('guid', {'strip': True}), {
                    'doc': 'Storm service iden which provided the package.'}),

                ('deprecated', ('bool', {}), {
                    'doc': 'Set to true if this command is scheduled to be removed.'}),

                ('deprecated:version', ('it:semver', {}), {
                    'doc': 'The Synapse version when this command will be removed.'}),

                ('deprecated:date', ('time', {}), {
                    'doc': 'The date when this command will be removed.'}),

                ('deprecated:mesg', ('str', {}), {
                    'doc': 'Optional description of this deprecation.'}),
            )),
            ('syn:deleted', {'runt': True}, (

                ('nid', ('int', {}), {
                    'readonly': True,
                    'doc': 'The nid for the node that was deleted.'}),

                ('sodes', ('data', {}), {
                    'readonly': True,
                    'doc': 'The layer storage nodes for the node that was deleted.'}),
            )),
        ),
    }),
)
