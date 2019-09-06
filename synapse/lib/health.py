import logging

logger = logging.getLogger(__name__)


RED = 'red'
GREEN = 'green'
YELLOW = 'yellow'
HEALTH_PRIORITY = {RED: 1, YELLOW: 2, GREEN: 3}


class HealthCheck(object):
    def __init__(self, iden: str):
        self.iden = iden
        self._status = GREEN
        self.components = []

    def pack(self) -> tuple:
        ret = {'iden': self.iden,
               'components': self.components,
               'status': self.status,
               }
        return ret

    def update(self,
               name: str,
               status: bool,
               mesg: str = '',
               data: dict = None,
               ) -> None:
        # Allow the component a shot at reporting a failure state
        status = status.lower()
        self.status = status
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
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, valu: str):
        valu = valu.lower()
        # if valu not in HEALTH_PRIORITY:
        #     raise ValueError(f'Value {valu} must be in {list(HEALTH_PRIORITY)}')
        new_priority = HEALTH_PRIORITY.get(valu)
        if new_priority is None:
            raise ValueError(f'Value {valu} must be in {list(HEALTH_PRIORITY)}')
        # Can only degrade status, not improve it.
        if new_priority >= HEALTH_PRIORITY.get(self._status):
            return
        self._status = valu
