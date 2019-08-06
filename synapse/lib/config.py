import os
import typing

import synapse.exc as s_exc
import synapse.common as s_common

class ConfTypes(object):
    def __init__(self):
        self.types = {}
        self._initTypes()

    def _initTypes(self):
        self.addType('bool', bool)
        self.addType('int', int)
        self.addType('str', str)
        self.addType('list', list)
        self.addType('dict', dict)

    def addType(self, name: str, func: typing.Callable):
        self.types[name] = func

    def norm(self, name: str, valu: typing.Any) -> typing.Any:
        func = self.types.get(name)
        ret = func(valu)
        return ret

class Config2:
    def __init__(self, confdefs):
        self.confdefs = confdefs
        self.conf = {}

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
