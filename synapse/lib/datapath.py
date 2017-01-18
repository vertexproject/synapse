import collections

import synapse.lib.syntax as s_syntax

class PathDict(collections.defaultdict):
    def __init__(self, onmiss):
        collections.defaultdict.__init__(self)
        self.onmiss = onmiss

    def __missing__(self, key):
        return self.onmiss(key)

class DataPath:

    def __init__(self, item, parent=None):
        self._d_item = item
        self._d_kids = PathDict( self._getItemElem )
        self._d_parent = parent

    def _getItemElem(self, elem):
        try:
            return DataPath(self._d_item[elem],parent=self)
        except (KeyError,TypeError) as e:
            return None

    #def walk(self, *path):
        #'''
        #Return a data path element by walking down they given keys.

        #Example:

            #item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            #data = DataPath(item)
            #bazdata = data.walk('foo', 1)

        #'''
        #data = self
        #for elem in path:
            #data = data.step(elem)
        #return data

    def open(self, path):
        '''
        Parse and open the specified data path.
        Returns a DataPath element for the specified path.

        Example:

            fqdn = data.open('foo/bar/fqdn').valu()

        Additionally, if any /*/ paths are encountered, the
        API assumes you would like to iterate over elements.

        Example:

            for baz in data.open('foo/bar/*/baz'):
                valu = baz.valu()

        '''
        steps = self._parse_path(path)
        if self._is_iter(steps):
            return self._iter_steps(steps)

        return self._open_steps(steps)

    def iter(self, path):
        steps = self._parse_path(path)
        return self._iter_steps(steps)

    def _open_steps(self, steps):

        base = self
        for step in steps:
            base = base._run_step(step)
            if base == None:
                break

        return base

    #def iter(self, path):
        #'''
        #Iterate over DataPath elements by path string.

        #Example:

            #for woot in data.iter('foo/bar/*/woot'):
                #dostuff(woot)

        #'''
        #steps = self._parse_path(path)
        #for data in self._iter_steps(steps,0,self):
            #yield data

    def _parse_path(self, path):
        '''
        Parse a path string into a series of ( <cmd>, <data> ) directives.

        /foo/*/hehe -> ( ('root',None), ('step','foo'), ('step','bar'), ('iter',None) )

        '''
        if not path:
            return ()

        off = 0
        ret = []

        if path.startswith('/'):
            off += 1
            ret.append( ('move','/') )

        plen = len(path)
        while off < plen:

            _,off = s_syntax.nom(path,off,('/',))

            # if it's a literal, there's no chance for
            # control data such as iterator directives
            if s_syntax.is_literal(path,off):
                elem,off = s_syntax.parse_literal(path,off)
                ret.append( ('step',elem) )
                continue

            elem,off = s_syntax.meh(path,off,('/',))

            if elem == '*':
                ret.append( ('iter',None) )
                continue

            if elem == '.':
                continue

            if elem == '..':
                ret.append( ('move','..') )
                continue

            ret.append( ('step',elem) )

        return ret

    def _is_iter(self, steps):
        return any([ 1 for step in steps if step[0] == 'iter' ])

    def _run_step(self, step):
        oper,data = step
        if oper == 'step':
            return self.step(data)

        if oper == 'move':
            if data == '..':
                return self.parent()

            if data == '/':
                return self.root()

    def _iter_steps(self, steps, off=0):

        base = self

        plen = len(steps)
        while off < plen:

            if base == None:
                break

            oper,data = steps[off]

            off += 1

            if oper == 'step':
                base = base.step(data)
                continue

            if oper == 'iter':
                for x in base:
                    for y in x._iter_steps(steps, off=off):
                        yield y
                return

            if oper == 'move':

                if data == '..':
                    base = base.parent()
                    continue

                if data == '/':
                    base = base.root()
                    continue

                raise SynErr(oper='move',data=data)

        if base != None:
            yield base

    def __iter__(self):
        for item in self.valu():
            yield DataPath(item,parent=self)

    def root(self):
        '''
        Return the root element of this DataPath.

        Example:

            root = data.root()

        '''
        retn = self
        while retn._d_parent:
            retn = retn._d_parent
        return retn

    def parent(self):
        '''
        Return the parent data path element.

        Example:

            rent = data.parent()

        '''
        if self._d_parent == None:
            return self

        return self._d_parent

    def step(self, elem):
        '''
        Return a DataPath element for the specified child path element.

        Example:

            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)
            foodata = data.step('foo')

        '''
        return self._d_kids[elem]

    def valu(self, path=None):
        '''
        Return the value of the specified child path element.

        Example:

            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)

            if data.valu('foo/0/bar') == 10:
                print('woot')

        '''
        if path == None:
            return self._d_item

        steps = self._parse_path(path)
        if self._is_iter(steps):
            return self._valu_iter(steps)

        base = self._open_steps(steps)
        if base != None:
            return base.valu()

    def _valu_iter(self, steps):
        for base in self._iter_steps(steps):
            yield base.valu()

    def items(self, *path):
        for item in self.valu(*path).items():
            yield item
