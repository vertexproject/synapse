import logging

import synapse.exc as s_exc

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class SynModule(s_module.CoreModule):

    def initCoreModule(self):

        self.core.addRuntLift('syn:cmd', self._liftRuntSynCmd)
        self.core.addRuntLift('syn:cron', self._liftRuntSynCron)
        self.core.addRuntLift('syn:form', self._liftRuntSynForm)
        self.core.addRuntLift('syn:prop', self._liftRuntSynProp)
        self.core.addRuntLift('syn:type', self._liftRuntSynType)
        self.core.addRuntLift('syn:tagprop', self._liftRuntSynTagProp)
        self.core.addRuntLift('syn:trigger', self._liftRuntSynTrigger)

    async def _liftRuntSynCmd(self, view, prop, cmprvalu=None):
        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.core.stormcmds.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for scmd in self.core.stormcmds.values():
            yield scmd.getRuntPode()

    async def _liftRuntSynCron(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.core.agenda.appts.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.core.agenda.appts.values():
            yield item.getRuntPode()

    async def _liftRuntSynForm(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.form(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.model.forms.values():
            yield item.getRuntPode()

    async def _liftRuntSynProp(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.prop(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.model.getProps():
            yield item.getRuntPode()

    async def _liftRuntSynType(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.type(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.model.types.values():
            yield item.getRuntPode()

    async def _liftRuntSynTagProp(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = self.model.tagprops.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in self.model.tagprops.values():
            yield item.getRuntPode()

    async def _liftRuntSynTrigger(self, view, prop, cmprvalu=None):

        if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
            item = view.triggers.triggers.get(cmprvalu[1])
            if item is not None:
                yield item.getRuntPode()
            return

        for item in view.triggers.triggers.values():
            yield item.getRuntPode()

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
                ('syn:splice', ('guid', {'strip': True}), {
                    'doc': 'A splice from a layer.'
                }),
                ('syn:nodedata', ('comp', {'fields': (('key', 'str'), ('form', 'syn:form'))}), {
                    'doc': 'A nodedata key and the form it may be present on.',
                }),
                ('syn:user', ('guid', {'strip': True}), {
                    'doc': 'A Synapse user GUID.'
                }),
                ('syn:role', ('guid', {'strip': True}), {
                    'doc': 'A Synapse role GUID.'
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
                        'doc': 'The list of forms accepted by the command as input.', 'uniq': True, 'sorted': True, 'ro': True}),
                    ('output', ('array', {'type': 'syn:form'}), {
                        'doc': 'The list of forms produced by the command as output.', 'uniq': True, 'sorted': True, 'ro': True}),
                    ('nodedata', ('array', {'type': 'syn:nodedata'}), {
                        'doc': 'The list of nodedata that may be added by the command.', 'uniq': True, 'sorted': True, 'ro': True}),
                )),
                ('syn:splice', {'runt': True}, (
                    ('type', ('str', {'strip': True}), {
                        'doc': 'Type of splice.', 'ro': True
                    }),
                    ('iden', ('str', {}), {
                        'doc': 'The iden of the node involved in the splice.', 'ro': True,
                    }),
                    ('form', ('syn:form', {'strip': True}), {
                        'doc': 'The form involved in the splice.', 'ro': True
                    }),
                    ('prop', ('syn:prop', {'strip': True}), {
                        'doc': 'Property modified in the splice.', 'ro': True
                    }),
                    ('tag', ('syn:tag', {'strip': True}), {
                        'doc': 'Tag modified in the splice.', 'ro': True
                    }),
                    ('valu', ('data', {}), {
                        'doc': 'The value being set in the splice.', 'ro': True
                    }),
                    ('oldv', ('data', {}), {
                        'doc': 'The value before the splice.', 'ro': True
                    }),
                    ('user', ('guid', {}), {
                        'doc': 'The user who caused the splice.', 'ro': True,
                    }),
                    ('prov', ('guid', {}), {
                        'doc': 'The provenance stack of the splice.', 'ro': True,
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time the splice occurred.', 'ro': True,
                    }),
                    ('splice', ('data', {}), {
                        'doc': 'The splice.', 'ro': True
                    }),
                )),
            ),
        }),)
