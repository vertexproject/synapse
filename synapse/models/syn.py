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

    model = view.core.model

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = view.core.stormcmds.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode(model)
        return

    for item in view.core.getStormCmds():
        yield item[1].getRuntPode(model)

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
        # Auto-registered prop types (flagged 'auto') are an internal storage detail.
        if item is not None and not item.info.get('auto'):
            yield item.getRuntPode()
        return

    for item in list(prop.modl.types.values()):
        if item.info.get('auto'):
            continue
        yield item.getRuntPode()

async def _liftRuntSynTagProp(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.tagprops.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.tagprops.values()):
        yield item.getRuntPode()

def _getSynIfacePode(form, name, info):

    props = {'doc': info.get('doc', '')}

    ifaces = info.get('interfaces')
    if ifaces:
        props['interfaces'] = tuple(ifname for (ifname, ifinfo) in ifaces)

    return (('syn:interface', name), {'props': form.wrapRuntProps(props)})

async def _liftRuntSynIface(view, prop, cmprvalu=None):

    form = prop.modl.form('syn:interface')

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        info = prop.modl.ifaces.get(cmprvalu[1])
        if info is not None:
            yield _getSynIfacePode(form, cmprvalu[1], info)
        return

    for name, info in list(prop.modl.ifaces.items()):
        yield _getSynIfacePode(form, name, info)


modeldefs = (
    {

        'types': (
            ('syn:user', (None, {'ctor': 'synapse.models.syn.SynUser'}), {
                'interfaces': (
                    ('entity:actor', {}),
                ),
                'props': (),
                'doc': 'A Synapse user.'}),

            ('syn:role', (None, {'ctor': 'synapse.models.syn.SynRole'}), {
                'doc': 'A Synapse role.'}),
            ('syn:type', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynType',
                'props': (
                    ('doc', ('str', {}), {
                        'doc': 'The docstring for the type.', 'computed': True}),
                    ('ctor', ('str', {}), {
                        'doc': 'The python ctor path for the type object.', 'computed': True}),
                    ('parent', ('syn:type', {}), {
                        'doc': 'Type which this inherits from.', 'computed': True}),
                    ('opts', ('data', {}), {
                        'doc': 'Arbitrary type options.', 'computed': True})
                ),
                'doc': 'A Synapse type used for normalizing nodes and properties.',
            }),
            ('syn:form', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynForm',
                'props': (
                    ('doc', ('str', {}), {
                        'doc': 'The docstring for the form.', 'computed': True}),
                    ('type', ('syn:type', {}), {
                        'doc': 'Synapse type for this form.', 'computed': True}),
                    ('parent', ('syn:form', {}), {
                        'doc': 'Form which this form extends.', 'computed': True}),
                    ('runt', ('bool', {}), {
                        'doc': 'Specifies if the form is runtime only.', 'computed': True}),
                    ('interfaces', ('array', {'type': 'syn:interface'}), {
                        'doc': 'The fully resolved set of interfaces which this form implements.', 'computed': True})
                ),
                'doc': 'A Synapse form used for representing nodes in the graph.',
            }),
            ('syn:interface', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynIface',
                'props': (
                    ('doc', ('str', {}), {
                        'doc': 'The docstring for the interface.', 'computed': True}),
                    ('interfaces', ('array', {'type': 'syn:interface'}), {
                        'doc': 'The interfaces which this interface inherits from.', 'computed': True}),
                ),
                'doc': 'A Synapse interface which forms may implement to share common properties.',
            }),
            ('syn:prop', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynProp',
                'props': (
                    ('doc', ('str', {}), {
                        'doc': 'Description of the property definition.'}),
                    ('form', ('syn:form', {}), {
                        'doc': 'The form of the property.', 'computed': True}),
                    ('type', ('array', {'type': 'syn:type'}), {
                        'doc': 'The synapse types allowed for this property.', 'computed': True}),
                    ('array', ('bool', {}), {
                        'doc': 'If the property is an array of values.', 'computed': True}),
                    ('relname', ('str', {}), {
                        'doc': 'Relative property name.', 'computed': True}),
                    ('univ', ('bool', {}), {
                        'doc': 'Specifies if a prop is universal.', 'computed': True}),
                    ('base', ('str', {}), {
                        'doc': 'Base name of the property.', 'computed': True}),
                    ('computed', ('bool', {}), {
                        'doc': 'Specifies if the property is dynamically computed from other property values.', 'computed': True}),
                    ('extmodel', ('bool', {}), {
                        'doc': 'Specifies if the property is an extended model property.', 'computed': True}),
                    ('typedocs', ('data', {}), {
                        'doc': 'A mapping of member type names to their documentation strings for this property.', 'computed': True}),
                ),
                'doc': 'A Synapse property.'
            }),
            ('syn:tagprop', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynTagProp',
                'props': (
                    ('doc', ('str', {}), {
                        'doc': 'Description of the tagprop definition.'}),
                    ('type', ('syn:type', {}), {
                        'doc': 'The synapse type for this tagprop.', 'computed': True}),
                ),
                'doc': 'A user defined tag property.'
            }),
            ('syn:cmd', ('str', {}), {
                'runt': True,
                'liftfunc': 'synapse.models.syn._liftRuntSynCmd',
                'props': (

                    ('doc', ('text', {}), {
                        'doc': 'Description of the command.'}),

                    ('package', ('str', {}), {
                        'doc': 'Storm package which provided the command.'}),

                    ('svciden', ('guid', {}), {
                        'doc': 'Storm service iden which provided the package.'}),

                    ('deprecated', ('bool', {}), {
                        'doc': 'Set to true if this command is scheduled to be removed.'}),

                    ('deprecated:version', ('it:version', {}), {
                        'doc': 'The Synapse version when this command will be removed.'}),

                    ('deprecated:date', ('time', {}), {
                        'doc': 'The date when this command will be removed.'}),

                    ('deprecated:mesg', ('str', {}), {
                        'doc': 'Optional description of this deprecation.'}),
                ),
                'doc': 'A Synapse storm command.'
            }),
            ('syn:deleted', ('data', {}), {
                'runt': True,
                'props': (
                    ('nid', ('int', {}), {
                        'doc': 'The nid for the node that was deleted.', 'computed': True}),
                    ('form', ('str', {}), {
                        'doc': 'The form for the node that was deleted.', 'computed': True}),
                    ('value', ('data', {}), {
                        'doc': 'The primary property value for the node that was deleted.', 'computed': True}),
                    ('sodes', ('data', {}), {
                        'doc': 'The layer storage nodes for the node that was deleted.', 'computed': True}),
                ),
                'doc': 'A node present below the write layer which has been deleted.'
            }),
        ),
    },
)
