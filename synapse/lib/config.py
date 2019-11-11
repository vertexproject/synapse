import os
import copy
import typing
import logging
import argparse

import yaml

import synapse.exc as s_exc
import synapse.common as s_common

logger = logging.getLogger(__name__)


argparse_map = {
    'int': int,
    'str': str,
    'bool': bool,
    'float': float,
}

def makeArgParser(confdefs, *args, **kwargs) -> (argparse.ArgumentParser, dict):
    parser = argparse.ArgumentParser()
    parser.add_argument('--test')
    parsed_names = {}
    for (name, conf) in confdefs:
        print('Confdef data:', name, conf)
        akwargs = {'help': conf.get('doc'),
                   }
        atyp = argparse_map.get(conf.get('type'), s_common.novalu)
        if atyp is not s_common.novalu:
            akwargs['type'] = atyp
        defval = conf.get('defval', s_common.novalu)
        akwargs['default'] = defval

        parsed_name = name.replace(':', '-')
        replace_name = name.replace(':', '_')
        parsed_names[replace_name] = name
        argname = '--' + parsed_name
        print('add_argument data', argname, akwargs)
        parser.add_argument(argname, **akwargs)

    return parser, parsed_names

class ConfTypes(object):
    def __init__(self):
        self.types = {}
        self._initTypes()

    def _initTypes(self):
        # These are super primitive and offer little safety
        # for example, nearly anything can be cast into str()
        self.addType('int', int)
        self.addType('str', str)
        self.addType('bool', bool)
        self.addType('dict', dict)
        self.addType('list', list)
        self.addType('float', float)

    def addType(self, name: str, func: typing.Callable):
        self.types[name] = func

    def norm(self, name: str, valu: typing.Any) -> typing.Any:
        func = self.types.get(name)
        if func is None:
            raise s_exc.NoSuchName(mesg='no norm func for name', name=name)
        ret = func(valu)
        return ret

class Config2:
    def __init__(self, confdefs, prefix='SYN_'):
        self.normer = ConfTypes()
        self.prefix = prefix
        self.confdefs = confdefs
        self.conf = {}
        self.norms = {}
        self.yaml_loads = ('dict',
                           'list',
                           )

        for key, info in self.confdefs:
            self.norms[key] = info.get('type').lower()
            defval = info.get('defval', s_common.novalu)
            if defval is s_common.novalu:
                continue
            self.conf[key] = copy.deepcopy(defval)

    def get(self, name, default=None):
        return self.conf.get(name, default)

    # Container magic methods
    def __setitem__(self, key, valu):
        self._set(key, valu)

    def __getitem__(self, item):
        return self.conf[item]

    # dict methods
    def copy(self):
        return copy.deepcopy(self)

    def items(self):
        return self.conf.items()

    def values(self):
        return self.conf.values()

    def keys(self):
        return self.conf.keys()

    async def set(self, name, valu):
        self._set(name, valu)

    def _set(self, name, valu):
        norm = self.norms.get(name)
        if norm is None:
            logger.warning(f'Config key: [{name}] has no norm function.')
            self.conf[name] = valu
            return
            # XXX THIS only fails in the test suite because the
            # CompatTest.test_compat_cellauth hsa some archaic config
            # data in it.  However, warning and moving along does allow
            # someone to cheat by shoveling config data in that isn't
            # neccesarily used. Tradeoffs...
            # raise s_exc.NoSuchName(name=name)
        self.conf[name] = self.normer.norm(norm, valu)

    async def loadConfDict(self, conf: typing.Dict):
        # use a copy of the input dict, since the values may be
        # modified at runtime by a object.
        conf = conf.copy()

        for name, valu in conf.items():
            await self.set(name, valu)

    async def loadConfYaml(self, *path):
        fp = s_common.genpath(*path)
        if os.path.isfile(fp):
            logger.debug('Loading file from [%s]', fp)
            conf = s_common.yamlload(fp)
            return await self.loadConfDict(conf)

    async def loadConfEnvs(self, envn: typing.AnyStr):
        '''Certain types may be yaml-decoded'''
        for key, _ in self.confdefs:
            envar = f'{self.prefix}{envn}_{key.replace(":", "_")}'.upper()
            envv = os.getenv(envar)
            if envv is not None:
                logger.debug(f'Loading config valu from: [{envar}]')
                if self.norms[key] in self.yaml_loads:
                    # Do a yaml load pass to decode certain
                    # types prior to loading them.
                    envv = yaml.safe_load(envv)
                await self.set(key, envv)

class Config:

    def __init__(self, confdefs):
        self.conf = {}
        self.norms = {}
        self.confdefs = confdefs

        for name, defval, norm in confdefs:
            self.norms[name] = norm
            self.conf[name] = defval

    def __iter__(self):
        return iter(list(self.conf.items()))

    async def loadConfDict(self, conf):
        for name, valu in conf.items():
            await self.set(name, valu)

    async def loadConfYaml(self, *path):
        conf = s_common.yamlload(*path)
        return await self.loadConfDict(conf)

    async def loadConfEnvs(self, envn):
        for name, defval, norm in self.confdefs:
            envv = os.getenv(f'{envn}_{name}'.upper())
            if envv is not None:
                await self.set(name, envv)

    def get(self, name):
        return self.conf.get(name)

    async def set(self, name, valu):
        norm = self.norms.get(name)
        if norm is None:
            raise s_exc.NoSuchName(name=name)

        self.conf[name] = norm(valu)
