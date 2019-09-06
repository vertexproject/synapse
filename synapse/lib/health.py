NOMINAL = 'nominal'
DEGRADED = 'degraded'
FAILED = 'failed'
HEALTH_PRIORITY = {FAILED: 1, DEGRADED: 2, NOMINAL: 3}

class HealthCheck(object):
    def __init__(self, iden):
        self.iden = iden
        self._status = NOMINAL
        self.components = []

    def pack(self):
        return {'iden': self.iden,
                'components': self.components,
                'status': self._status,
                }

    def update(self, name, status, mesg='', data=None):
        '''
        Append a new component to the Healcheck object.

        Args:
            name (str): Name of the reported component.
            status (str): nomdinal/degraded/failed status code.
            mesg (str): Optional message about the component status.
            data (dict): Optional arbitrary dictionary of additional metadata about the component.

        Returns:
            None
        '''
        # Allow the component a shot at reporting a failure state
        status = status.lower()
        self.setStatus(status)
        if data is None:
            data = {}
        self.components.append({'status': status,
                                'name': name,
                                'mesg': mesg,
                                'data': data,
                                })

    def getStatus(self):
        return self._status

    def setStatus(self, valu):
        valu = valu.lower()
        new_priority = HEALTH_PRIORITY.get(valu)
        if new_priority is None:
            raise ValueError(f'Value {valu} must be in {list(HEALTH_PRIORITY)}')
        # Can only degrade status, not improve it.
        if new_priority >= HEALTH_PRIORITY.get(self._status):
            return
        self._status = valu
