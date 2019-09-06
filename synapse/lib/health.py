RED = 'red'
GREEN = 'green'
YELLOW = 'yellow'
HEALTH_PRIORITY = {RED: 1, YELLOW: 2, GREEN: 3}


class HealthCheck(object):
    def __init__(self, iden):
        self.iden = iden
        self._status = GREEN
        self.components = []

    def pack(self):
        return {'iden': self.iden,
                'components': self.components,
                'status': self.status,
                }

    def update(self, name, status, mesg='', data=None):
        '''
        Append a new component to the Healcheck object.

        Args:
            name (str): Name of the reported component.
            status (str): green/yellow/red status code.
            mesg (str): Optional message about the component status.
            data (dict): Optional arbitrary dictionary of additional metadata about the component.

        Returns:
            None
        '''
        # Allow the component a shot at reporting a failure state
        status = status.lower()
        self.status = status
        if data is None:
            data = {}
        self.components.append({'status': status,
                                'name': name,
                                'mesg': mesg,
                                'data': data,
                                })

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, valu):
        valu = valu.lower()
        new_priority = HEALTH_PRIORITY.get(valu)
        if new_priority is None:
            raise ValueError(f'Value {valu} must be in {list(HEALTH_PRIORITY)}')
        # Can only degrade status, not improve it.
        if new_priority >= HEALTH_PRIORITY.get(self._status):
            return
        self._status = valu
