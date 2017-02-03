class Scope:
    '''
    The Scope object assists in creating nested varible scopes.

    Example:

        with Scope() as scope:

            scope.set('foo',10)

            with scope:
                scope.set('foo',20)
                dostuff(scope) # 'foo' is 20...

            dostuff(scope) # 'foo' is 10 again...

    '''
    def __init__(self, **vals):
        self.frames = [vals]

    def __enter__(self):
        self.enter()

    def __exit__(self, exc, cls, tb):
        self.leave()

    def enter(self):
        '''
        Add an additional scope frame.
        '''
        return self.frames.append({})

    def leave(self):
        '''
        Pop the current scope frame.
        '''
        self.frames.pop()

    def set(self, name, valu):
        '''
        Set a value in the current scope frame.
        '''
        self.frames[-1][name] = valu

    def get(self, name, defval=None):
        '''
        Retrieve a value from the closest scope frame.
        '''
        for frame in reversed(self.frames):
            valu = frame.get(name)
            if valu != None:
                return valu
        return defval

    def add(self, name, *vals):
        '''
        Add values as iter() compatible items in the current scope frame.
        '''
        item = self.frames[-1].get(name)
        if item == None:
            self.frames[-1][name] = item = []
        item.extend(vals)

    def iter(self, name):
        '''
        Iterate through values added with add() from each scope frame.
        '''
        for frame in self.frames:
            vals = frame.get(name)
            if vals == None:
                continue
            for valu in vals:
                yield valu
