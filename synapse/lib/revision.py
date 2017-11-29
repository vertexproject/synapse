import logging

import synapse.common as s_common
import synapse.eventbus as s_eventbus

logger = logging.getLogger(__name__)

def step(v1, v2):
    def wrap(f):
        f._rev_step = (v1, v2)
        return f
    return wrap

class Revisioner(s_eventbus.EventBus):
    '''
    Assist with incremental revision updates.

    Example:

        class MyRev(Revisioner):

            @revstep('0.0.0', '0.0.1')
            def _runFooThing(self, item):
                dostuff(item)

            @revstep('0.0.1', '0.0.2')
            def _runBarThing(self, item):
                otherstuff(item)

        revr = MyRev()

        vers = getWootVers() # (0, 0, 0)
        for vers in revr.runRevPath(vers, woot):
            saveWootVers(vers)

    '''
    def __init__(self):
        s_eventbus.EventBus.__init__(self)

        self.steps = {}
        self.vers = set()

        for name in dir(self):

            valu = getattr(self, name, None)
            step = getattr(valu, '_rev_step', None)
            if step is None:
                continue

            v0 = self.chop(step[0])
            v1 = self.chop(step[1])

            self.vers.add(v0)
            self.vers.add(v1)

            self.addRevStep(v0, v1, valu)

        self.maxver = max(self.vers)

    def chop(self, text):
        '''
        Simple chop routine for text guarenteed to be in x.y.z format.

        Args:
            text (str): A "1.2.3" style semver string.

        Returns:
            (int,int,int): The semver tuple.
        '''
        return tuple([int(x) for x in text.split('.')])

    def repr(self, sver):
        '''
        Simple repr routine for a (x,y,z) semver tuple.

        Args:
            sver ((int,int,int)): A semver tuple.

        Returns:
            str: The "x.y.z" string
        '''
        return '.'.join([str(v) for v in sver])

    def addRevStep(self, v0, v1, func):
        self.steps[v0] = (v0, v1, func)

    def getRevPath(self, vers):
        '''
        Construct and return a revision path of (v0,v1,func) tuples.

        Args:
            vers ((int, int, int): A simple semver tuple

        Returns:
            [ (v0, v1, func) ]: A list of steps.

        Raises:
            NoRevPath: When no path is found from vers to maxver.
        '''
        if vers == self.maxver:
            return []

        path = []
        nver = vers

        while True:

            step = self.steps.get(nver)
            if step is None:
                break

            path.append(step)
            nver = step[1]

        if not path or path[-1][1] != self.maxver:
            raise s_common.NoRevPath(vers=vers, maxver=self.maxver, path=path)

        return path

    def runRevPath(self, vers, *args, **kwargs):
        '''
        Run revision callbacks and yield semver tuples as they complete.

        Args:
            vers (int): A version integer (or None for a fresh start).

        Yields:
            int: For each completed version update.
        '''
        path = list(self.getRevPath(vers))
        for v1, v2, func in path:
            mesg = 'Updating module [%s] from [%s] => [%s] - do *not* interrupt'
            logger.warning(mesg, self, v1, v2)

            # fire a pre-revision event so that tests can hook into
            self.fire('syn:revisioner:rev', name=str(self.__class__.__name__), v1=v1, v2=v2)

            func(*args, **kwargs)

            mesg = 'Finished updating module [%s] to [%s].'
            logger.warning(mesg, self, v2)

            yield v2
