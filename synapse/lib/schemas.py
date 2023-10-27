import synapse.lib.config as s_config


_HttpExtAPIConfSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'methods': {
            'type': 'object',
            'default': {},
            'properties': {
                'get': {'type': 'string', 'minLen': 1},
                'head': {'type': 'string', 'minLen': 1},
                'post': {'type': 'string', 'minLen': 1},
                'put': {'type': 'string', 'minLen': 1},
                'delete': {'type': 'string', 'minLen': 1},
                'patch': {'type': 'string', 'minLen': 1},
                'options': {'type': 'string', 'minLen': 1},
            },
            'additionalProperties': False,
        },
        'authenticated': {'type': 'boolean', 'default': True},
        'name': {'type': 'string', 'default': ''},
        'desc': {'type': 'string', 'default': ''},
        'path': {'type': 'string', 'minlen': 1},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'runas': {'type': 'string', 'pattern': '^(owner|user)$'},
        'owner': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'updated': {'type': 'integer', 'minimum': 0},
        'readonly': {'type': 'boolean', 'default': False},
        'perms': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'perm': {'type': 'array', 'items': {'type': 'string', 'minlen': 1}},
                    'default': {'type': 'boolean', 'default': False},
                }
            },
            'default': [],
        },
        'vars': {'type': 'object', 'default': {}}

    },
    'additionalProperties': False
}


reqValidHttpExtAPIConf = s_config.getJsValidator(_HttpExtAPIConfSchema)
