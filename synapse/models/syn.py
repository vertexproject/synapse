import logging

import synapse.common as s_common
import synapse.lib.tufo as s_tufo
from synapse.lib.module import CoreModule, modelrev

logger = logging.getLogger(__name__)

class SynMod(CoreModule):
    @staticmethod
    def getBaseModels():
        modl = {

            'types': (
                ('syn:splice', {'subof': 'guid'}),
                ('syn:auth:user', {'subof': 'str'}),
                ('syn:auth:role', {'subof': 'str'}),
                ('syn:auth:userrole', {'subof': 'comp', 'fields': 'user=syn:auth:user,role=syn:auth:role'}),
                ('syn:tagform', {'subof': 'comp', 'fields': 'tag,syn:tag|form,syn:prop', 'ex': '(foo.bar,baz:faz)'}),

                ('syn:alias', {'subof': 'str', 'regex': r'^\$[a-z_]+$',
                    'doc': 'A synapse guid alias', 'ex': '$visi'}),

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

                ('syn:auth:user', {'local': 1}, (
                    ('storm:limit:lift',
                     {'ptype': 'int', 'defval': 10000, 'doc': 'The storm query lift limit for the user'}),
                    ('storm:limit:time',
                     {'ptype': 'int', 'defval': 120, 'doc': 'The storm query time limit for the user'}),
                )),

                ('syn:auth:role', {'local': 1}, (
                    ('desc', {'ptype': 'str'}),
                )),

                ('syn:auth:userrole', {'local': 1}, (
                    ('user', {'ptype': 'syn:auth:user'}),
                    ('role', {'ptype': 'syn:auth:role'}),
                )),

                ('syn:fifo', {'ptype': 'guid', 'local': 1}, (
                    ('name', {'ptype': 'str', 'doc': 'The name of this fifo'}),
                    ('desc', {'ptype': 'str', 'doc': 'The fifo description'}),
                )),

                ('syn:trigger', {'ptype': 'guid', 'local': 1}, (
                    ('en', {'ptype': 'bool', 'defval': 0, 'doc': 'Is the trigger currently enabled'}),
                    ('on', {'ptype': 'syn:perm'}),
                    ('run', {'ptype': 'syn:storm'}),
                    ('user', {'ptype': 'syn:auth:user'}),
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
                ))
            )
        }

        name = 'syn'
        return ((name, modl),)

    @modelrev('syn', 201709051630)
    def _delOldModelNodes(self):
        types = self.core.getRowsByProp('syn:type')
        forms = self.core.getRowsByProp('syn:form')
        props = self.core.getRowsByProp('syn:prop')
        syncore = self.core.getRowsByProp('.:modl:vers:syn:core')

        with self.core.getCoreXact():
            [self.core.delRowsById(r[0]) for r in types]
            [self.core.delRowsById(r[0]) for r in forms]
            [self.core.delRowsById(r[0]) for r in props]
            [self.core.delRowsById(r[0]) for r in syncore]

    @modelrev('syn', 201709191412)
    def _revModl201709191412(self):
        '''
        Migrate the XREF types to use the propvalu syntax.
        '''
        tick = s_common.now()
        adds = []
        dels = set()

        nforms = set()

        for form in self.core.getModelDict().get('forms'):
            sforms = self.core.getTypeOfs(form)
            if 'xref' in sforms:
                nforms.add(form)

        for ntyp in nforms:
            nodes = self.core.getTufosByProp(ntyp)
            xtyp = '{}:xtype'.format(ntyp)
            xrefp = '{}:xref'.format(ntyp)
            xrefpint = '{}:xref:intval'.format(ntyp)
            xrefpstr = '{}:xref:strval'.format(ntyp)
            xrefprop = '{}:xref:prop'.format(ntyp)
            for node in nodes:
                iden = node[0]
                srcvtype = node[1].get(xtyp)
                if srcvtype is None:
                    # This is expensive node level introspection :(
                    for prop, valu in s_tufo.props(node).items():
                        if prop.startswith('xref:'):
                            form = prop.split('xref:', 1)[1]
                            if self.core.isTufoForm(form):
                                srcvtype = form
                                break
                    if not srcvtype:
                        raise s_common.NoSuchProp(iden=node[0], type=ntyp,
                                                  mesg='Unable to find a xref prop which is a form for migrating a '
                                                       'XREF node.')
                srcprp = '{}:xref:{}'.format(ntyp, srcvtype)
                srcv = node[1].get(srcprp)
                valu, subs = self.core.getPropNorm(xrefp, [srcvtype, srcv])
                adds.append((iden, xrefp, valu, tick))
                adds.append((iden, xrefprop, srcvtype, tick))
                if 'intval' in subs:
                    adds.append((iden, xrefpint, subs.get('intval'), tick))
                else:
                    adds.append((iden, xrefpstr, subs.get('strval'), tick))
                dels.add(srcprp)
                dels.add(xtyp)
        with self.core.getCoreXact():
            self.core.addRows(adds)
            for prop in dels:
                self.core.delRowsByProp(prop)

    @modelrev('syn', 201710191144)
    def _revModl201710191144(self):
        with self.core.getCoreXact():
            now = s_common.now()
            adds = []
            logger.debug('Lifting tufo:form rows')
            for i, _, v, t in self.core.store.getRowsByProp('tufo:form'):
                adds.append((i, 'node:created', t, now),)
            logger.debug('Deleting existing node:created rows')
            self.core.store.delRowsByProp('node:created')
            if adds:
                tot = len(adds)
                logger.debug('Adding {:,d} node:created rows'.format(tot))
                i = 0
                n = 100000
                for chunk in s_common.chunks(adds, n):
                    self.core.store.addRows(chunk)
                    i = i + len(chunk)
                    logger.debug('Loading {:,d} [{}%] rows into transaction'.format(i, int((i / tot) * 100)))
        logger.debug('Finished adding node:created rows to the Cortex')

    @modelrev('syn', 201711012123)
    def _revModl201711012123(self):
        now = s_common.now()
        forms = sorted(self.core.getTufoForms())
        nforms = len(forms)
        for n, form in enumerate(forms):
            adds = []
            logger.debug('Computing node:ndef rows for [{}]'.format(form))
            for i, p, v, t in self.core.store.getRowsByProp(form):
                # This is quicker than going through the norm process
                nv = s_common.guid((p, v))
                adds.append((i, 'node:ndef', nv, now))

            if adds:
                tot = len(adds)
                logger.debug('Adding {:,d} node:ndef rows for [{}]'.format(tot, form))
                with self.core.getCoreXact() as xact:
                    i = 0
                    nt = 100000
                    for chunk in s_common.chunks(adds, nt):
                        self.core.store.addRows(chunk)
                        i = i + len(chunk)
                        logger.debug('Loading {:,d} [{}%] rows into transaction'.format(i, int((i / tot) * 100)))
            logger.debug('Processed {:,d} [{}%] forms.'.format(n, int((n / nforms) * 100)))
        logger.debug('Finished adding node:ndef rows to the Cortex')
