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

    def walk(self, *path):
        '''
        Return a data path element by walking down they given keys.

        Example:

            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)
            bazdata = data.walk('foo', 1)

        '''
        data = self
        for elem in path:
            data = data.step(elem)
        return data

    def open(self, path):
        '''
        Parse and open the specified data path.
        Returns a DataPath element for the specified path.

        Example:

            fqdn = data.open('foo/bar/fqdn').valu()

        '''
        off = 0
        base = self

        if path.startswith('/'):
            off += 1
            base = self.root()

        plen = len(path)
        while off < plen:

            _,off = s_syntax.nom(path,off,('/',))

            # if it's a literal, there's no chance for
            # control data such as iterator directives
            if s_syntax.is_literal(path,off):
                elem,off = s_syntax.parse_literal(path,off)

            else:
                elem,off = s_syntax.meh(path,off,('/',))

                if elem == '.':
                    continue

                if elem == '..':
                    base = base.parent()
                    continue

            base = base.step(elem)
            if base == None:
                return None

        return base

    def iter(self, path):
        '''
        Iterate over DataPath elements by path string.

        Example:

            for woot in data.iter('foo/bar/*/woot'):
                dostuff(woot)

        '''
        off = 0
        base = self

        if path.startswith('/'):
            off += 1
            base = self.root()

        for data in self._iter_recurse(path,off,base):
            yield data

    def _iter_recurse(self, path, off, base):

        plen = len(path)
        while off < plen:

            _,off = s_syntax.nom(path,off,('/',))

            # if it's a literal, there's no chance for
            # control data such as iterator directives
            if s_syntax.is_literal(path,off):
                elem,off = s_syntax.parse_literal(path,off)
                base = base.step(elem)
                if base == None:
                    return

                continue

            elem,off = s_syntax.meh(path,off,('/',))

            if elem == '*':

                for x in base:
                    for y in self._iter_recurse(path, off, x):
                        yield y

                return

            if elem == '.':
                continue

            if elem == '..':
                base = base.parent()
                continue

            base = base.step(elem)
            if base == None:
                return

        yield base

    def __iter__(self):
        for item in self.valu():
            yield DataPath(item,parent=self)

    #def iter(self, path):

    #def parse(self, path):
        #'''
        #Parse the given path and return a tuple of ( parts, info ).
        #'''

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
        data = self
        if path != None:
            data = self.open(path)

        if data == None:
            return None

        return data._d_item

    def items(self, *path):
        for item in self.valu(*path).items():
            yield item
