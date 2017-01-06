#class BackPath: pass
#backpath = BackPath()

import collections

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
        self._d_kids[-1] = parent

    def _getItemElem(self, elem):
        try:
            return DataPath(self._d_item[elem],parent=self)
        except KeyError as e:
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

    def step(self, elem):
        '''
        Return a DataPath element for the specified child path element.

        Example:

            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)
            foodata = data.step('foo')

        '''
        return self._d_kids[elem]

    def valu(self, *path):
        '''
        Return the value of the specified child path element.

        Example:

            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)
            foodata = data.step('foo')

        '''
        data = self.walk(*path)
        if data == None:
            return None
        return data._d_item

    def items(self, *path):
        for item in self.valu(*path).items():
            yield item

    def iter(self, *path):
        '''
        Yield DataPath instances from the given child path element.

        Example:
            item = { 'foo':[ {'bar':10},{'baz':20} ], 'hur':'dur' }

            data = DataPath(item)
            for dat0 in data.iter('foo'):
                dostuff(dat0)

        '''
        for item in self.valu(*path):
            yield DataPath(item,parent=self)
            
