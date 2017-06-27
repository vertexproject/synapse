from synapse.lib.module import CoreModule, modelrev

class LangMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                # ('lang:code',{'subof','enum',...
                ('lang:idiom', {'subof': 'str:txt', 'doc': 'A subcultural idiom'}),
                ('lang:trans', {'subof': 'str:txt', 'doc': 'Raw text with a documented translation'}),
            ),

            'forms': (

                ('lang:idiom', {}, (
                    ('url', {'ptype': 'inet:url', 'doc': 'Authoritative URL for the idiom'}),
                    ('desc:en', {'ptype': 'str:txt', 'doc': 'English description'}),
                    # TODO etc...
                )),

                ('lang:trans', {}, (
                    ('text:en', {'ptype': 'str:txt', 'doc': 'English translation'}),
                    ('desc:en', {'ptype': 'str:txt', 'doc': 'English description'}),
                    # TODO etc...
                )),
            ),

            'tags': (

                ('lang', {'props': {'doc': 'Tags which denote the presense of various language content'}}),
                ('lang.zh', {'props': {'doc': 'Chinese Language Family'}}),

                ('lang.zh.cn', {'props': {'doc': 'Simplified Chinese (Mainland China)'}}),
                ('lang.zh.hk', {'props': {'doc': 'Cantonese Chinese (Hong Kong)'}}),
                ('lang.zh.tw', {'props': {'doc': 'Traditional Chinese (Taiwan)'}}),

                ('lang.en', {'props': {'doc': 'English Language Family'}}),
                ('lang.en.uk', {'props': {'doc': 'Brittish English Language'}}),
                ('lang.en.us', {'props': {'doc': 'US English Language'}}),

                ('lang.ru', {'props': {'doc': 'Russian Language'}}),

                # FIXME etc...
            ),
        }
        name = 'lang'
        return ((name, modl), )
