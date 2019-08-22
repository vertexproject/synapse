import logging

logger = logging.getLogger(__name__)


class HealthCheck(object):
    def __init__(self, iden: str):
        self.iden = iden
        self._healthy = True
        self.components = []

    def pack(self) -> tuple:
        if self.healthy:
            health = 'green'
        else:
            health = 'red'
        comps = []
        for component in self.components:
            comp = component.copy()
            if comp.get('status'):
                comp['status'] = 'green'
            else:
                comp['status'] = 'red'
            comps.append(comp)
        ret = {'iden': self.iden,
               'components': comps,
               'status': health,
               }
        return ret

    def update(self,
               name: str,
               status: bool,
               mesg: str = '',
               data: dict = None,
               ) -> None:
        # Allow the component a shot at reporting a failure state
        self.healthy = status
        if data is None:
            data = {}
        # record which component failed, any additional message they may have,
        # as well as any additional data they want to report on.
        self.components.append({'status': status,
                                'name': name,
                                'mesg': mesg,
                                'data': data,
                                })

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
