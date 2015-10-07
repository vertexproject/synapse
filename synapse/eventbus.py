import weakref
import threading
import traceback
import collections

finlock = threading.RLock()

class EventBus:
    '''
    A synapse EventBus provides an easy way manage callbacks.
    '''
    def __init__(self):
        self.isfini = False
        self.finlock = finlock
        self.finievt = threading.Event()

        self._syn_meths = collections.defaultdict(list)
        self._syn_weaks = collections.defaultdict(weakref.WeakSet)

        self._syn_links = []
        self._syn_weak_links = weakref.WeakSet()

        self._fini_meths = []
        self._fini_weaks = weakref.WeakSet()

    def link(self, meth, weak=False):
        '''
        Add a callback method to receive *all* events.

        Example:

            bus1 = EventBus()
            bus2 = EventBus()

            bus1.link( bus2.dist )

            # all events on bus1 are also propigated on bus2

        '''
        if weak:
            return self._syn_weak_links.add(meth)

        self._syn_links.append(meth)

    def on(self, name, meth, weak=False):
        '''
        Add a callback method to the SynCallBacker.

        Example:

            def baz(event):
                x = event[1].get('x')
                y = event[1].get('y')
                return x + y

            d.on('woot',baz)

            d.fire('foo', x=10, y=20)

        Notes:

            * Use weak=True to hold a weak reference to the method.

        '''
        if weak:
            self._syn_weaks[name].add(meth)
            return

        self._syn_meths[name].append(meth)

    def fire(self, evtname, **info):
        '''
        Fire each of the methods registered for an FIXME.
        Returns a list of the return values of each method.

        Example:

            for ret in d.fire('woot',foo='asdf'):
                print('got: %r' % (ret,))

        '''
        event = (evtname,info)
        self.dist(event)
        return event

    def dist(self, event):
        '''
        Distribute an existing event tuple.
        '''
        ret = []
        name = event[0]
        meths = self._syn_meths.get(name)
        if meths != None:
            for meth in meths:
                try:
                    ret.append( meth( event ) )
                except Exception as e:
                    traceback.print_exc()

        weaks = self._syn_weaks.get(name)
        if weaks != None:
            for meth in weaks:
                try:
                    ret.append( meth( event ) )
                except Exception as e:
                    traceback.print_exc()

        for meth in self._syn_links:
            try:
                ret.append( meth(event) )
            except Exception as e:
                traceback.print_exc()

        for meth in self._syn_weak_links:
            try:
                ret.append( meth(event) )
            except Exception as e:
                traceback.print_exc()

        return ret

    def fini(self):
        '''
        Fire the 'fini' handlers and set self.isfini.

        Example:

            d.fini()

        '''
        with finlock:

            if self.isfini:
                return

            self.isfini = True

        for meth in self._fini_meths:
            try:
                meth()
            except Exception as e:
                traceback.print_exc()

        for meth in self._fini_weaks:
            try:
                meth()
            except Exception as e:
                traceback.print_exc()

        self.finievt.set()

    def onfini(self, meth, weak=False):
        '''
        Register a handler to fire when this EventBus shuts down.
        '''
        if weak:
            return self._fini_weaks.add(meth)
        self._fini_meths.append(meth)

    def wait(self, timeout=None):
        '''
        Wait for fini() on the EventBus.

        Example:

            d.wait(timeout=30)

        '''
        return self.finievt.wait(timeout=timeout)
