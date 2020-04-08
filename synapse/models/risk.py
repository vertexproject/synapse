import synapse.lib.module as s_module

class RiskModule(s_module.CoreModule):

    def getModelDefs(self):

        modl = {
            'types': (
                ('risk:vuln', ('guid', {}), {
                    'doc': 'A unique vulnerability',
                }),
                ('risk:hasvuln', ('guid', {}), {
                    'doc': 'An instance of a vulnerability present in a target',
                }),
                ('risk:attack', ('guid', {}), {
                    'doc': 'An instance of an actor attacking a target.'
                }),
            ),
            'forms': (
                ('risk:vuln', {}, (
                    ('name', ('str', {}), {
                        'doc': 'A user specified name for the vulnerability',
                    }),

                    ('type', ('str', {}), {
                        'doc': 'A user specified type for the vulnerability',
                    }),
                    ('desc', ('str', {}), {
                        'doc': 'A description of the vulnerability',
                    }),
                    ('cve', ('it:sec:cve', {}), {
                        'doc': 'The CVE ID of the vulnerability.',
                    }),
                )),

                ('risk:hasvuln', {}, (
                    ('vuln', ('risk:vuln', {}), {
                        'doc': 'The vulnerability present in the target.'
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': 'The vulnerable person',
                    }),
                    ('org', ('ou:org', {}), {
                        'doc': 'The vulnerable org',
                    }),
                    ('place', ('geo:place', {}), {
                        'doc': 'The vulnerable place',
                    }),
                    ('software', ('it:prod:softver', {}), {
                        'doc': 'The vulnerable software',
                    }),
                    ('spec', ('mat:spec', {}), {
                        'doc': 'The vulnerable material specification',
                    }),
                    ('item', ('mat:item', {}), {
                        'doc': 'The vulnerable material item',
                    }),
                )),

                ('risk:attack', {}, (
                    ('time', ('time', {}), {
                        'doc': 'Set if the time of the attack is known',
                    }),
                    ('success', ('bool', {}), {
                        'doc': 'Set if the attack was known to have succeeded or not',
                    }),
                    ('targeted', ('bool', {}), {
                        'doc': 'Set if the attack was assessed to be targeted or not',
                    }),
                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'Set if the attack was part of a larger campaign',
                    }),
                    ('prev', ('risk:attack', {}), {
                        'doc': 'The previous/parent attack in a list or hierarchy',
                    }),
                    ('actor:org', ('ou:org', {}), {
                        'doc': 'The org that carried out the attack',
                    }),
                    ('actor:person', ('ps:person', {}), {
                        'doc': 'The person that carried out the attack',
                    }),
                    ('target:org', ('ou:org', {}), {
                        'doc': 'The org was the target of the attack',
                    }),
                    ('target:host', ('it:host', {}), {
                        'doc': 'The host was the target of the attack',
                    }),
                    ('target:person', ('ps:person', {}), {
                        'doc': 'The person was the target of the attack',
                    }),
                    ('via:ipv4', ('inet:ipv4', {}), {
                        'doc': 'The target host was contacted via the IPv4 address',
                    }),
                    ('via:ipv6', ('inet:ipv6', {}), {
                        'doc': 'The target host was contacted via the IPv6 address',
                    }),
                    ('via:email', ('inet:email', {}), {
                        'doc': 'The target person/org was contacted via the email address',
                    }),
                    ('via:phone', ('tel:phone', {}), {
                        'doc': 'The target person/org was contacted via the phone number',
                    }),
                    ('used:vuln', ('risk:vuln', {}), {
                        'doc': 'The actor used the vuln in the attack',
                    }),
                    ('used:url', ('inet:url', {}), {
                        'doc': 'The actor used the url in the attack',
                    }),
                    ('used:host', ('it:host', {}), {
                        'doc': 'The actor used the host in the attack',
                    }),
                    ('used:email', ('inet:email', {}), {
                        'doc': 'The actor used the email in the attack',
                    }),
                    ('used:file', ('file:bytes', {}), {
                        'doc': 'The actor used the file in the attack',
                    }),
                    ('used:server', ('inet:server', {}), {
                        'doc': 'The actor used the server in the attack',
                    }),
                    ('used:software', ('it:prod:softver', {}), {
                        'doc': 'The actor used the software in the attack',
                    }),
                )),
            ),
        }
        name = 'risk'
        return ((name, modl), )
