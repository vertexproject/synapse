import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack


easyPermSchema = {
    'type': 'object',
    'properties': {
        'users': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
        },
        'roles': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
        },
    },
    'required': ['users', 'roles'],
}

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

reqValidVault = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'pattern': '^.{1,128}$'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'type': {'type': 'string', 'pattern': '^.{1,128}$'},
        'scope': {'type': ['string', 'null'], 'enum': [None, 'user', 'role', 'global']},
        'owner': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'permissions': s_msgpack.deepcopy(easyPermSchema),
        'secrets': {'type': 'object'},
        'configs': {'type': 'object'},
    },
    'additionalProperties': False,
    'required': [
        'iden',
        'name',
        'type',
        'scope',
        'owner',
        'permissions',
        'secrets',
        'configs',
    ],
})

# 7776000000  -> 90 days
# 31536000000 -> 365 days
_cellUserAccesTokenSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'modified': {'type': 'integer', 'minimum': 0},
        'expref': {'type': 'integer', 'minimum': 0},
        'duration': {'type': 'integer', 'minimum': 1, 'maximum': 31536000000, 'default': 7776000000},
        'shadow': {
            'type': 'object',
        },
    },
    'additionalProperties': False,
    'required': [
        'iden',
        'name',
        'user',
        'created',
        'modified',
        'expref',
        'shadow',
    ],
}
reqValidUserAccessTokenDef = s_config.getJsValidator(_cellUserAccesTokenSchema)
