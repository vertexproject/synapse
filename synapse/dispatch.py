import weakref
import traceback
import collections

class Dispatcher:
    '''
    A synapse Dispatcher provides an easy way manage callbacks.
    '''

    def __init__(self):
        self.isfini = False
        self._syn_meths = collections.defaultdict(list)
        self._syn_weaks = collections.defaultdict(weakref.WeakSet)

    def synOn(self, name, meth, weak=False):
        '''
        Add a callback method to the SynCallBacker.

        Example:

            def baz(x,y):
                return x + y

            def faz(x,y):
                return x / y

            d.synOn('woot',baz)
            d.synOn('woot',faz)

            d.synFire('foo',10,20)

        Notes:

            * Callback convention is decided by synFire caller
            * Use weak=True to hold a weak reference to the method.

        '''
        if weak:
            self._syn_weaks[name].add(meth)
            return

        self._syn_meths[name].append(meth)

    def synFire(self, name, *args, **kwargs):
        '''
        Fire each of the methods registered for an FIXME.
        Returns a list of the return values of each method.

        Example:

            for ret in d.synFire('woot',10,foo='asdf'):
                print('got: %r' % (ret,))

        '''
        ret = []
        meths = self._syn_meths.get(name)
        if meths != None:
            for meth in meths:
                try:
                    ret.append( meth(*args,**kwargs) )
                except Exception as e:
                    traceback.print_exc()

        weaks = self._syn_weaks.get(name)
        if weaks != None:
            for meth in weaks:
                try:
                    ret.append( meth(*args,**kwargs) )
                except Exception as e:
                    traceback.print_exc()

        return ret

    def synFireFini(self):
        '''
        Fire the 'fini' dispatch handlers and set self.isfini.

        Example:

            d.synFireFini()

        '''
        self.isfini = True
        self.synFire('fini')

