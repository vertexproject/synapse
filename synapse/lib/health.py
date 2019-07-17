import json
import logging
import typing

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.base as s_base

logger = logging.getLogger(__name__)

class HealthCheck(object):
    def __init__(self, htyp: str):
        self.type = htyp
        self._healthy = True
        self.data = {}
        self.packsizecheck = True
        self.packsizemax = 4096

    def pack(self) -> tuple:
        ret = (self.healthy,
               {'type': self.type,
                'data': self.data},
               )
        return ret

    def update(self,
               name: str,
               status: bool,
               data: typing.Any =None,
               ) -> None:
        if name in self.data:
            raise s_exc.DataAlreadyExists(mesg='Already updated healthcheck for the component.',
                                          name=name, status=status)
        # Allow the component a shot at reporting a failure state
        self.healthy = status
        if data is not None:
            self.data[name] = data

    @property
    def healthy(self) -> bool:
        return self._healthy

    @healthy.setter
    def healthy(self, valu: bool):
        if not self.healthy:
            # Cannot change a unhealthy healthcheck status
            return
        if not valu:
            # Can only set the _health to unhealthy
            self._healthy = False
