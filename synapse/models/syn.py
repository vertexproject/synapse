import logging

import synapse.common as s_common
import synapse.lib.tufo as s_tufo
import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class SynModule(s_module.CoreModule):

    def getModelDefs(self):

        return (('syn', {

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

            ),
        }),)

class SynMod(s_module.CoreModule):
    @staticmethod
    def getBaseModels():
        modl = {

            'types': (
                ('syn:splice', {'subof': 'guid'}),
                ('syn:tagform', {'subof': 'comp', 'fields': 'tag,syn:tag|form,syn:prop', 'ex': '(foo.bar,baz:faz)'}),

                ('syn:alias', {'subof': 'str', 'regex': r'^\$[a-z_]+$',
                    'doc': 'A synapse guid alias', 'ex': '$visi'}),
                ('syn:ingest', {'subof': 'str:lwr'}),
                ('syn:log', {'subof': 'guid'}),

            ),

            'forms': (

                ('syn:splice', {'local': 1}, (
                    ('act', {'ptype': 'str:lwr'}),
                    ('time', {'ptype': 'time'}),
                    ('node', {'ptype': 'guid'}),
                    ('user', {'ptype': 'str:lwr'}),

                    ('tag', {'ptype': 'str:lwr'}),
                    ('form', {'ptype': 'str:lwr'}),
                    ('valu', {'ptype': 'str:lwr'}),
                )),

                ('syn:alias', {'local': 1}, (
                    ('iden', {'ptype': 'guid', 'defval': '*',
                        'doc': 'The GUID for the given alias name'}),
                )),

                ('syn:trigger', {'ptype': 'guid', 'local': 1}, (
                    ('en', {'ptype': 'bool', 'defval': 0, 'doc': 'Is the trigger currently enabled'}),
                    ('on', {'ptype': 'syn:perm'}),
                    ('run', {'ptype': 'syn:storm'}),
                    ('user', {'ptype': 'str'}),
                )),

                ('syn:core', {'doc': 'A node representing a unique Cortex'}, ()),
                ('syn:form', {'doc': 'The base form type.'}, (
                    ('doc', {'ptype': 'str', 'doc': 'basic form definition'}),
                    ('ver', {'ptype': 'int', 'doc': 'form version within the model'}),
                    ('model', {'ptype': 'str', 'doc': 'which model defines a given form'}),
                    ('ptype', {'ptype': 'syn:type', 'doc': 'Synapse type for this form'}),
                    ('local', {'ptype': 'bool', 'defval': 0,
                               'doc': 'Flag used to determine if a form should not be included in splices'}),
                )),
                ('syn:prop', {'doc': 'The base property type.'}, (
                    ('doc', {'ptype': 'str', 'doc': 'Description of the property definition.'}),
                    ('title', {'ptype': 'str', 'doc': 'A short description of the property definition.'}),
                    ('form', {'ptype': 'syn:prop', 'doc': 'The form of the property.'}),
                    ('ptype', {'ptype': 'syn:type', 'doc': 'Synapse type for this field'}),
                    ('req', {'ptype': 'bool', 'doc': 'Set to 1 if this property is required to form teh node.'}),
                    ('relname', {'ptype': 'str', 'doc': 'Relative name of the property'}),
                    ('base', {'ptype': 'str', 'doc': 'Base name of the property'}),
                    ('glob', {'ptype': 'bool', 'defval': 0, 'doc': 'Set to 1 if this property defines a glob'}),
                    ('defval', {'doc': 'Set to the default value for this property', 'glob': 1}),
                    ('univ', {'ptype': 'bool',
                              'doc': 'Specifies if a prop is universal and has no form associated with it.'}),
                )),
                ('syn:type', {'doc': 'The base type type.'}, (
                    ('ctor', {'ptype': 'str', 'doc': 'Python path to the class used to instantiate the type.'}),
                    ('subof', {'ptype': 'syn:type', 'doc': 'Type which this inherits from.'}),
                    ('*', {'glob': 1})
                )),
                ('syn:tag', {'doc': 'The base form for a synapse tag.'}, (
                    ('up', {'ptype': 'syn:tag', 'doc': ''}),
                    ('doc', {'ptype': 'str', 'defval': '', }),
                    ('depth', {'ptype': 'int', 'doc': 'How deep the tag is in the hierarchy', 'defval': 0}),
                    ('title', {'ptype': 'str', 'doc': '', 'defval': ''}),
                    ('base', {'ptype': 'str', 'doc': '', 'ro': 1}),

                )),
                ('syn:tagform', {'doc': 'A node describing the meaning of a tag on a specific form'}, (
                    ('tag', {'ptype': 'syn:tag', 'doc': 'The tag being documented', 'ro': 1}),
                    ('form', {'ptype': 'syn:prop', 'doc': 'The form that the tag applies too', 'ro': 1}),
                    ('doc', {'ptype': 'str:txt', 'defval': '??',
                             'doc': 'The long form description for what the tag means on the given node form'}),
                    ('title', {'ptype': 'str:txt', 'defval': '??',
                               'doc': 'The short name for what the tag means the given node form'}),
                )),
                ('syn:model', {'ptype': 'str', 'doc': 'prefix for all forms with in the model'}, (
                    ('hash', {'ptype': 'guid', 'doc': 'version hash for the current model'}),
                    ('prefix', {'ptype': 'syn:prop', 'doc': 'Prefix used by teh types/forms in the model'}),
                )),
                ('syn:seq', {'ptype': 'str:lwr', 'doc': 'A sequential id generation tracker'}, (
                    ('width', {'ptype': 'int', 'defval': 0, 'doc': 'How many digits to use to represent the number'}),
                    ('nextvalu', {'ptype': 'int', 'defval': 0, 'doc': 'The next sequential value'}),
                )),
                ('syn:ingest', {'ptype': 'syn:ingest', 'local': 1}, (
                    ('time', {'ptype': 'time'}),
                    ('text', {'ptype': 'json'})
                )),
                ('syn:log', {'ptype': 'guid', 'local': 1}, (
                    ('subsys', {'ptype': 'str', 'defval': '??',
                                'doc': 'Named subsystem which originaed teh log event'}),
                    ('level', {'ptype': 'int', 'defval': logging.WARNING, }),
                    ('time', {'ptype': 'time', 'doc': 'When the log event occured'}),
                    ('exc', {'ptype': 'str', 'doc': 'Exception class name if caused by an exception'}),
                    ('info:*', {'glob': 1})
                )),
            )
        }

        name = 'syn'
        return ((name, modl),)
