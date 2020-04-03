import synapse.lib.module as s_module

class AuthModule(s_module.CoreModule):

    def getModelDefs(self):

        modl = {
            'types': (
                ('auth:creds', ('guid', {}), {
                    'doc': 'A unique set of credentials used to access a resource.',
                }),
                ('auth:access', ('guid', {}), {
                    'doc': 'An instance of using creds to access a resource.',
                }),
            ),
            'forms': (
                ('auth:creds', {}, (
                    ('email', ('inet:email', {}), {
                        'doc': 'The email address used to identify the user.',
                    }),
                    ('user', ('inet:user', {}), {
                        'doc': 'The user name used to identify the user.',
                    }),
                    ('phone', ('tel:phone', {}), {
                        'doc': 'The phone number used to identify the user.',
                    }),
                    ('passwd', ('inet:passwd', {}), {
                        'doc': 'The password used to authenticate.',
                    }),
                    ('passwdhash', ('it:auth:passwdhash', {}), {
                        'doc': 'The password hash used to authenticate.',
                    }),
                    ('website', ('inet:url', {}), {
                        'doc': 'The base URL of the website that the credentials allow access to.',
                    }),
                    ('host', ('it:host', {}), {
                        'doc': 'The host that the credentials allow access to.',
                    }),
                    ('wifi:ssid', ('inet:wifi:ssid', {}), {
                        'doc': 'The WiFi SSID that the credentials allow access to.',
                    }),
                    # TODO x509, rfid, mat:item locks/keys
                )),

                ('auth:access', {}, (
                    ('creds', ('auth:creds', {}), {
                        'doc': 'The credentials used to attempt access.',
                    }),
                    ('time', ('time', {}), {
                        'doc': 'The time of the access attempt.',
                    }),
                    ('success', ('bool', {}), {
                        'doc': 'Set to true if the access was successful.',
                    }),
                    ('person', ('ps:person', {}), {
                        'doc': 'The person who attempted access.',
                    }),
                )),
            ),
        }
        name = 'auth'
        return ((name, modl), )
