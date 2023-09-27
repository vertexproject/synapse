import synapse.lib.config as s_config


_HttpExtAPIConfSchema = {
    'type': 'object',
    'properties': {
        'iden': {
            'type': 'string'
        },
    }
}

HttpExaAPIConfSchema = s_config.getJsValidator(_HttpExtAPIConfSchema)
